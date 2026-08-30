"""
View records handler.
Displays the latest 5 health records based on patient and record type filters.
Rate limited to prevent API abuse.
"""
import html
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import SUPPORTED_RECORD_TYPES
from clients.health_api_client import get_health_api_client
from utils.formatting import render_table
from utils.rate_limiter import rate_limit_api_calls

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_PATIENT, SELECTING_RECORD_TYPE = range(2)


@rate_limit_api_calls
async def view_records_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for /view_records command.
    Step 1: Present patient list (including "All" option) as inline buttons.
    Rate limited to prevent API abuse.
    """
    client = get_health_api_client()
    
    try:
        patients = await client.get_patients()
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        await update.message.reply_text(
            "❌ Error connecting to health service. Please try again later."
        )
        return ConversationHandler.END
    
    if not patients:
        await update.message.reply_text(
            "❌ No patients configured. Please add patients to the configuration."
        )
        return ConversationHandler.END
    
    # Create inline keyboard with patient options
    keyboard = []
    keyboard.append([InlineKeyboardButton("📋 All Patients", callback_data="patient_ALL")])
    for patient in patients:
        keyboard.append([InlineKeyboardButton(patient["name"], callback_data=f"patient_{patient['name']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👤 **Step 1 of 2: Select Patient**\n\n"
        "Please select a patient (or All):",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SELECTING_PATIENT


async def patient_selected_for_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Step 2: Handle patient selection and present record-type options.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")
        return ConversationHandler.END
    
    # Extract patient name from callback data
    if query.data.startswith("patient_"):
        patient_name = query.data.replace("patient_", "")
        
        # Validate patient name or "ALL"
        if patient_name != "ALL":
            client = get_health_api_client()
            try:
                patients = await client.get_patients()
                patient_names = [p["name"] for p in patients]
                if patient_name not in patient_names:
                    await query.edit_message_text(
                        "❌ Invalid patient selection. Please try again with /view_records."
                    )
                    return ConversationHandler.END
            except ConnectionError as e:
                logger.error(f"Connection error: {e}")
                await query.edit_message_text(
                    "❌ Error connecting to health service. Please try again later."
                )
                return ConversationHandler.END
        
        # Store patient in context
        context.user_data["selected_patient"] = patient_name
        
        # Create inline keyboard with record type options
        keyboard = []
        keyboard.append([InlineKeyboardButton("📋 All Types", callback_data="type_ALL")])
        for record_type in SUPPORTED_RECORD_TYPES:
            keyboard.append([InlineKeyboardButton(record_type, callback_data=f"type_{record_type}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        patient_display = "All Patients" if patient_name == "ALL" else patient_name
        
        await query.edit_message_text(
            f"📋 **Step 2 of 2: Select Record Type**\n\n"
            f"Patient: *{patient_display}*\n\n"
            f"Please select the type of record (or All):",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SELECTING_RECORD_TYPE
    
    await query.edit_message_text("❌ Invalid selection. Please try again with /view_records.")
    return ConversationHandler.END


async def record_type_selected_for_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Step 3: Handle record type selection, fetch records, and display them.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Extract record type from callback data
    if query.data.startswith("type_"):
        record_type = query.data.replace("type_", "")
        
        # Validate record type or "ALL"
        if record_type != "ALL" and record_type not in SUPPORTED_RECORD_TYPES:
            await query.edit_message_text(
                "❌ Invalid record type selection. Please try again with /view_records."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        # Retrieve stored patient from context
        patient_name = context.user_data.get("selected_patient")
        
        if not patient_name:
            await query.edit_message_text(
                "❌ Error: Missing patient selection. Please start over with /view_records."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        try:
            # Fetch records from API
            client = get_health_api_client()
            
            # Convert "ALL" to None for API query
            patient_filter = None if patient_name == "ALL" else patient_name
            type_filter = None if record_type == "ALL" else record_type
            
            records = await client.get_records(
                patient=patient_filter,
                record_type=type_filter,
                limit=5
            )
            
            # Format records for display
            patient_display = "All Patients" if patient_name == "ALL" else patient_name
            type_display = "All Types" if record_type == "ALL" else record_type

            if not records:
                await query.edit_message_text(
                    f"📋 <b>No Records Found</b>\n\n"
                    f"Patient: <b>{html.escape(patient_display)}</b>\n"
                    f"Record Type: <b>{html.escape(type_display)}</b>\n\n"
                    f"No records match your criteria.",
                    parse_mode=ParseMode.HTML
                )
            else:
                header = (
                    f"📋 <b>Latest {len(records)} Record(s)</b>\n"
                    f"Patient: <b>{html.escape(patient_display)}</b>\n"
                    f"Record Type: <b>{html.escape(type_display)}</b>\n"
                )

                rows = [
                    [
                        datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M"),
                        record["patient"],
                        record["record_type"],
                        record["value"],
                    ]
                    for record in records
                ]
                table = render_table(["Time", "Patient", "Type", "Value"], rows)

                await query.edit_message_text(
                    f"{header}\n{table}",
                    parse_mode=ParseMode.HTML
                )
            
            logger.info(
                f"User {update.effective_user.id} viewed records: "
                f"patient={patient_name}, type={record_type}, count={len(records)}"
            )
            
            # Clear context data
            context.user_data.clear()
            
            return ConversationHandler.END
            
        except ConnectionError as e:
            logger.error(f"Connection error fetching records: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Error connecting to health service. Please try again later."
            )
            context.user_data.clear()
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error fetching records: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Error fetching records. Please try again or contact support."
            )
            context.user_data.clear()
            return ConversationHandler.END
    
    await query.edit_message_text("❌ Invalid selection. Please try again with /view_records.")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_view_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /cancel command during conversation.
    """
    context.user_data.clear()
    
    if update.message:
        await update.message.reply_text("❌ Operation cancelled.")
    elif update.callback_query:
        await update.callback_query.answer("Operation cancelled.")
        await update.callback_query.edit_message_text("❌ Operation cancelled.")
    
    return ConversationHandler.END


def get_view_records_conversation_handler() -> ConversationHandler:
    """
    Create and return the ConversationHandler for /view_records flow.
    
    Returns:
        ConversationHandler: Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[CommandHandler("view_records", view_records_command)],
        states={
            SELECTING_PATIENT: [
                CallbackQueryHandler(patient_selected_for_view, pattern="^(patient_|cancel)"),
            ],
            SELECTING_RECORD_TYPE: [
                CallbackQueryHandler(record_type_selected_for_view, pattern="^(type_|cancel)"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_view_handler),
        ],
        name="view_records_conversation",
        persistent=False,
    )
