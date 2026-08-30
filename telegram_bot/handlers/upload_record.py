"""
Upload record conversation handler.
Multi-step flow for uploading medical lab report images.
Rate limited with stricter limits for file uploads.
"""
import html
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from clients.health_api_client import get_health_api_client
from utils.formatting import render_table
from utils.rate_limiter import rate_limit_uploads

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_PATIENT, WAITING_FOR_IMAGE = range(2)

# Supported image formats
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Live upload-progress polling
POLL_INTERVAL_SECONDS = 2.0
MAX_POLL_ATTEMPTS = 60  # ~2 minutes at the interval above
STAGE_LABELS = {
    "validating": "📄 Validating uploaded file...",
    "extracting": "🧪 Extracting lab values with AI...",
    "archiving": "🗄️ Archiving document to Paperless...",
    "saving": "💾 Saving extracted values...",
}
REVIEW_STATE_KEY = "upload_reviews"


@rate_limit_uploads
async def upload_record_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for /upload_record command.
    Step 1: Present patient list as inline buttons.
    Rate limited with stricter limits for file uploads.
    """
    # Get patients from API
    client = get_health_api_client()
    
    try:
        patients = await client.get_patients()
    except (ValueError, ConnectionError) as e:
        logger.error(f"Error fetching patients: {e}")
        await update.message.reply_text(
            "❌ Error connecting to health service. Please try again later."
        )
        return ConversationHandler.END
    
    if not patients:
        await update.message.reply_text(
            "❌ No patients found. Please add a patient first using /add_patient."
        )
        return ConversationHandler.END
    
    # Extract patient names from dicts
    patient_names = [patient["name"] for patient in patients]
    
    # Create inline keyboard with patient options
    keyboard = []
    for patient_name in patient_names:
        keyboard.append([InlineKeyboardButton(patient_name, callback_data=f"patient_{patient_name}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👤 **Step 1 of 2: Select Patient**\n\n"
        "Please select a patient for the lab report:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    logger.info(f"User {update.effective_user.id} started upload_record flow")
    
    return SELECTING_PATIENT


async def patient_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Step 2: Handle patient selection and prompt for image upload.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Extract patient name from callback data
    if query.data.startswith("patient_"):
        patient_name = query.data.replace("patient_", "")
        
        # Validate patient name exists in API
        client = get_health_api_client()
        try:
            patients = await client.get_patients()
            patient_names = [p["name"] for p in patients]
            if patient_name not in patient_names:
                await query.edit_message_text(
                    "❌ Invalid patient selection. Please try again with /upload_record."
                )
                context.user_data.clear()
                return ConversationHandler.END
        except (ValueError, ConnectionError) as e:
            logger.error(f"Error fetching patients: {e}")
            await query.edit_message_text(
                "❌ Error connecting to health service. Please try again later."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        # Store patient in context
        context.user_data["selected_patient"] = patient_name
        
        logger.info(f"User {update.effective_user.id} selected patient: {patient_name}")
        
        await query.edit_message_text(
            f"📸 **Step 2 of 2: Upload Lab Report Image**\n\n"
            f"Patient: *{patient_name}*\n\n"
            f"Please upload an image of the medical lab report.\n"
            f"Supported formats: JPEG, PNG, GIF, BMP\n"
            f"Maximum size: 10MB\n\n"
            f"You can send the image as a photo or document.\n"
            f"Use /cancel to cancel.",
            parse_mode="Markdown"
        )
        
        return WAITING_FOR_IMAGE
    
    await query.edit_message_text("❌ Invalid selection. Please try again with /upload_record.")
    context.user_data.clear()
    return ConversationHandler.END


async def image_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Step 3: Handle image upload, send to API, and display confirmation.
    """
    file = None
    filename = None
    content_type = None
    
    # Handle photo messages (Telegram sends multiple sizes, get the largest)
    if update.message.photo:
        photo = update.message.photo[-1]  # Largest size
        file = await context.bot.get_file(photo.file_id)
        filename = f"photo_{photo.file_id}.jpg"
        content_type = "image/jpeg"
        logger.info(f"Received photo message: file_id={photo.file_id}")
    
    # Handle document messages (check if it's an image)
    elif update.message.document:
        doc = update.message.document
        if doc.mime_type and doc.mime_type.startswith('image/'):
            file = await context.bot.get_file(doc.file_id)
            filename = doc.file_name or f"document_{doc.file_id}"
            content_type = doc.mime_type
            logger.info(f"Received document message: file_id={doc.file_id}, filename={filename}, mime_type={doc.mime_type}")
        else:
            await update.message.reply_text(
                "❌ The file you sent is not an image.\n\n"
                "Please upload an image file (JPEG, PNG, GIF, or BMP).\n"
                "Use /cancel to cancel."
            )
            return WAITING_FOR_IMAGE
    
    # If no valid image found
    if not file:
        await update.message.reply_text(
            "❌ Please send an image file.\n\n"
            "You can send the image as a photo or as a document.\n"
            "Supported formats: JPEG, PNG, GIF, BMP\n"
            "Use /cancel to cancel."
        )
        return WAITING_FOR_IMAGE
    
    # Validate file extension
    if filename:
        file_ext = None
        for ext in SUPPORTED_IMAGE_EXTENSIONS:
            if filename.lower().endswith(ext):
                file_ext = ext
                break
        
        if not file_ext:
            await update.message.reply_text(
                "❌ Unsupported file format.\n\n"
                "Please upload an image in one of these formats: JPEG, PNG, GIF, BMP\n"
                "Use /cancel to cancel."
            )
            return WAITING_FOR_IMAGE
    
    # Validate content type
    if content_type and not content_type.startswith('image/'):
        await update.message.reply_text(
            "❌ The file you sent is not an image.\n\n"
            "Please upload an image file (JPEG, PNG, GIF, or BMP).\n"
            "Use /cancel to cancel."
        )
        return WAITING_FOR_IMAGE
    
    # Download file content
    try:
        file_content_bytes = await file.download_as_bytearray()
        # Convert bytearray to bytes for httpx compatibility
        file_content = bytes(file_content_bytes)
        file_size = len(file_content)
        
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ File too large ({file_size / (1024 * 1024):.2f}MB).\n\n"
                f"Maximum file size is 10MB.\n"
                f"Please try again with a smaller file.\n"
                f"Use /cancel to cancel."
            )
            return WAITING_FOR_IMAGE
        
        logger.info(f"Downloaded file: filename={filename}, size={file_size} bytes")
    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Error downloading the image file.\n\n"
            "Please try again or use /cancel to exit."
        )
        return WAITING_FOR_IMAGE
    
    # Retrieve patient name from context
    patient_name = context.user_data.get("selected_patient")
    
    if not patient_name:
        await update.message.reply_text(
            "❌ Error: Missing patient information. Please start over with /upload_record."
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Upload to API
    try:
        client = get_health_api_client()
        
        result = await client.upload_record_image(
            file_content=file_content,
            filename=filename,
            content_type=content_type,
            patient=patient_name
        )

        logger.info(
            f"User {update.effective_user.id} uploaded record: "
            f"patient={patient_name}, filename={result.get('filename', filename)}"
        )

        task_id = result.get("task_id")
        if task_id:
            status_message = await update.message.reply_text("⏳ Processing your lab report...")
            context.job_queue.run_repeating(
                _poll_upload_status,
                interval=POLL_INTERVAL_SECONDS,
                first=POLL_INTERVAL_SECONDS,
                chat_id=update.effective_chat.id,
                name=f"upload_status_{task_id}",
                data={
                    "task_id": task_id,
                    "message_id": status_message.message_id,
                    "patient_name": patient_name,
                    "attempts": 0,
                    "last_label": None,
                },
            )
        else:
            # No background task was queued - nothing to poll for.
            await update.message.reply_text(
                f"✅ Lab report saved: {result.get('filename', filename)}\n"
                f"👤 Patient: {patient_name}"
            )

        # Clear context data
        context.user_data.clear()

        return ConversationHandler.END
        
    except ValueError as e:
        logger.error(f"API error uploading record: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Error uploading lab report: {str(e)}\n\n"
            "Please try again or use /cancel to exit."
        )
        return WAITING_FOR_IMAGE
    except ConnectionError as e:
        logger.error(f"Connection error uploading record: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Error connecting to health service.\n\n"
            "Please check your connection and try again.\n"
            "Use /cancel to exit."
        )
        return WAITING_FOR_IMAGE
    except Exception as e:
        logger.error(f"Unexpected error uploading record: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ An unexpected error occurred while uploading the lab report.\n\n"
            "Please try again or use /cancel to exit."
        )
        return WAITING_FOR_IMAGE


async def _poll_upload_status(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    JobQueue callback: poll the backend for background upload-processing
    status and edit the placeholder message in place until the task reaches
    a terminal state (or polling times out).
    """
    job = context.job
    job_data = job.data
    task_id = job_data["task_id"]
    message_id = job_data["message_id"]
    patient_name = job_data["patient_name"]
    job_data["attempts"] += 1

    client = get_health_api_client()
    try:
        status_response = await client.get_upload_status(task_id)
    except (ValueError, ConnectionError) as e:
        logger.warning(f"Error polling upload status for task {task_id}: {e}")
        if job_data["attempts"] >= MAX_POLL_ATTEMPTS:
            job.schedule_removal()
            await context.bot.edit_message_text(
                chat_id=job.chat_id,
                message_id=message_id,
                text="⚠️ Lost track of processing status. Check /view_records shortly to see if it completed."
            )
        return

    state = status_response.get("status")

    if state in ("PENDING", "PROGRESS"):
        label = STAGE_LABELS.get(status_response.get("stage"), "⏳ Processing your lab report...")
        if job_data["last_label"] != label:
            job_data["last_label"] = label
            await context.bot.edit_message_text(chat_id=job.chat_id, message_id=message_id, text=label)
        if job_data["attempts"] >= MAX_POLL_ATTEMPTS:
            job.schedule_removal()
            await context.bot.edit_message_text(
                chat_id=job.chat_id,
                message_id=message_id,
                text="⚠️ Still processing - this is taking longer than usual. Check /view_records shortly."
            )
        return

    job.schedule_removal()

    if state == "SUCCESS":
        await _finalize_upload_success(context, job.chat_id, message_id, patient_name, status_response.get("result") or {})
    else:
        error_detail = status_response.get("error") or "Unknown error"
        await context.bot.edit_message_text(
            chat_id=job.chat_id,
            message_id=message_id,
            text=(
                "❌ <b>Processing failed</b> while reading your lab report.\n\n"
                f"Details: {html.escape(error_detail[:300])}\n\n"
                "Please try uploading the photo again with /upload_record."
            ),
            parse_mode=ParseMode.HTML
        )


async def _finalize_upload_success(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    message_id: int,
    patient_name: str,
    result: dict
) -> None:
    """Render the final extraction summary (table + review keyboard) in place."""
    lab_report = result.get("lab_report") or {}
    test_results = lab_report.get("results") or []
    rows = [
        [t.get("test_name", "?"), str(t.get("results", "")), t.get("unit") or ""]
        for t in test_results
    ]

    lines = [
        "✅ <b>Lab Report Processed</b>",
        f"👤 Patient: {html.escape(patient_name)}",
        f"💾 {result.get('records_saved', 0)} value(s) saved",
    ]
    paperless_status = result.get("paperless_status")
    if paperless_status == "failed":
        lines.append("⚠️ Archiving to Paperless failed (file kept locally; won't retry automatically).")
    elif paperless_status == "ok":
        lines.append("🗄️ Archived to Paperless.")

    text = "\n".join(lines)
    reply_markup = None
    if rows:
        text += "\n" + render_table(["Test", "Value", "Unit"], rows)
        checked = [False] * len(rows)
        context.chat_data.setdefault(REVIEW_STATE_KEY, {})[message_id] = {
            "rows": rows,
            "checked": checked,
        }
        reply_markup = _build_review_keyboard(rows, checked)
    else:
        text += "\n\n(No test values were extracted from this image.)"

    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )


def _build_review_keyboard(rows: list, checked: list) -> InlineKeyboardMarkup:
    """Build the ☑️/⬜ per-row review toggle keyboard (annotate-only, no edit/delete)."""
    keyboard = []
    for idx, row in enumerate(rows):
        label = row[0] if row and row[0] else f"Row {idx + 1}"
        emoji = "☑️" if checked[idx] else "⬜"
        keyboard.append([InlineKeyboardButton(f"{emoji} {label}"[:64], callback_data=f"rvw_toggle:{idx}")])
    keyboard.append([InlineKeyboardButton("⚠️ Something looks wrong", callback_data="rvw_issue")])
    return InlineKeyboardMarkup(keyboard)


async def review_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Flip a single row's reviewed flag and re-render the keyboard in place."""
    query = update.callback_query
    message_id = query.message.message_id
    review = context.chat_data.get(REVIEW_STATE_KEY, {}).get(message_id)

    if not review:
        await query.answer("This review has expired.", show_alert=True)
        return

    idx = int(query.data.split(":", 1)[1])
    review["checked"][idx] = not review["checked"][idx]
    await query.answer()
    await query.edit_message_reply_markup(
        reply_markup=_build_review_keyboard(review["rows"], review["checked"])
    )


async def review_issue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain that editing/deleting extracted values isn't supported yet."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "Editing or deleting extracted values isn't supported yet.\n"
        "To log the correct value yourself, use /add_record for now."
    )


def get_upload_review_handlers() -> list:
    """CallbackQueryHandlers for the post-upload review keyboard (registered globally, not tied to the upload ConversationHandler)."""
    return [
        CallbackQueryHandler(review_toggle_callback, pattern=r"^rvw_toggle:\d+$"),
        CallbackQueryHandler(review_issue_callback, pattern=r"^rvw_issue$"),
    ]


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /cancel command during conversation.
    """
    context.user_data.clear()
    
    if update.message:
        await update.message.reply_text(
            "❌ Operation cancelled.\n\n"
            "You're back to the main menu.",
            reply_markup=ReplyKeyboardRemove()
        )
    elif update.callback_query:
        await update.callback_query.answer("Operation cancelled.")
        await update.callback_query.edit_message_text("❌ Operation cancelled.")
    
    return ConversationHandler.END


async def unexpected_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle unexpected inputs during conversation (non-image messages).
    """
    if update.message:
        await update.message.reply_text(
            "❌ Please upload an image file.\n\n"
            "You can send the image as a photo or as a document.\n"
            "Supported formats: JPEG, PNG, GIF, BMP\n"
            "Maximum size: 10MB\n\n"
            "Use /cancel to cancel."
        )
    
    # Stay in WAITING_FOR_IMAGE state
    return WAITING_FOR_IMAGE


def get_upload_record_conversation_handler() -> ConversationHandler:
    """
    Create and return the ConversationHandler for /upload_record flow.
    
    Returns:
        ConversationHandler: Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[CommandHandler("upload_record", upload_record_command)],
        states={
            SELECTING_PATIENT: [
                CallbackQueryHandler(patient_selected, pattern="^(patient_|cancel)"),
            ],
            WAITING_FOR_IMAGE: [
                MessageHandler(filters.PHOTO, image_received),
                MessageHandler(filters.Document.IMAGE, image_received),
                CommandHandler("cancel", cancel_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_handler),
            MessageHandler(filters.ALL, unexpected_input),
        ],
        name="upload_record_conversation",
        persistent=False,
    )

