"""
Upload record conversation handler.
Multi-step flow for uploading medical lab report images.
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from clients.health_api_client import get_health_api_client

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_PATIENT, WAITING_FOR_IMAGE = range(2)

# Supported image formats
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes


async def upload_record_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for /upload_record command.
    Step 1: Present patient list as inline buttons.
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
        
        # Build success message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success_message = (
            "✅ **Lab Report Uploaded Successfully!**\n\n"
            f"👤 Patient: {patient_name}\n"
            f"📁 Filename: {result.get('filename', filename)}\n"
            f"📅 Uploaded at: {timestamp}"
        )
        
        # Add task ID if present
        if result.get('task_id'):
            success_message += f"\n🆔 Task ID: {result['task_id']}"
        
        await update.message.reply_text(
            success_message,
            parse_mode="Markdown"
        )
        
        logger.info(
            f"User {update.effective_user.id} uploaded record: "
            f"patient={patient_name}, filename={result.get('filename', filename)}"
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

