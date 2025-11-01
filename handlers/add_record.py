"""
Add record conversation handler.
Multi-step flow for recording health measurements.
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

from config import SUPPORTED_RECORD_TYPES
from storage.database import get_database

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_PATIENT, SELECTING_RECORD_TYPE, ENTERING_VALUE = range(3)


async def add_record_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for /add_record command.
    Step A: Present patient list as inline buttons.
    """
    # Get patients from database instead of static config
    db = get_database()
    patients = db.get_patients()
    
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
        "👤 **Step 1 of 3: Select Patient**\n\n"
        "Please select a patient:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SELECTING_PATIENT


async def patient_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Step B: Handle patient selection and present record-type options.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")
        return ConversationHandler.END
    
    # Extract patient name from callback data
    if query.data.startswith("patient_"):
        patient_name = query.data.replace("patient_", "")
        
        # Validate patient name exists in database
        db = get_database()
        patients = db.get_patients()
        patient_names = [p["name"] for p in patients]
        if patient_name not in patient_names:
            await query.edit_message_text(
                "❌ Invalid patient selection. Please try again with /add_record."
            )
            return ConversationHandler.END
        
        # Store patient in context
        context.user_data["selected_patient"] = patient_name
        
        # Create inline keyboard with record type options
        keyboard = []
        for record_type in SUPPORTED_RECORD_TYPES:
            keyboard.append([InlineKeyboardButton(record_type, callback_data=f"type_{record_type}")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📋 **Step 2 of 3: Select Record Type**\n\n"
            f"Patient: *{patient_name}*\n\n"
            f"Please select the type of record:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SELECTING_RECORD_TYPE
    
    await query.edit_message_text("❌ Invalid selection. Please try again with /add_record.")
    return ConversationHandler.END


async def record_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Step C: Handle record type selection and prompt for value input.
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
        
        # Validate record type
        if record_type not in SUPPORTED_RECORD_TYPES:
            await query.edit_message_text(
                "❌ Invalid record type selection. Please try again with /add_record."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        # Store record type in context
        context.user_data["selected_record_type"] = record_type
        
        patient_name = context.user_data.get("selected_patient", "Unknown")
        
        # Prompt for value input
        await query.edit_message_text(
            f"✍️ **Step 3 of 3: Enter Record Value**\n\n"
            f"Patient: *{patient_name}*\n"
            f"Record Type: *{record_type}*\n\n"
            f"Please send the measurement value as text.\n\n"
            f"Examples:\n"
            f"• For BP: \"120/80\" or \"120 over 80\"\n"
            f"• For Sugar: \"95\" or \"95 mg/dL\"\n"
            f"• For Weight: \"70\" or \"70 kg\"\n"
            f"• For Creatinine: \"1.2\" or \"1.2 mg/dL\"\n\n"
            f"You can type any text description.\n"
            f"Use /cancel to cancel.",
            parse_mode="Markdown"
        )
        
        return ENTERING_VALUE
    
    await query.edit_message_text("❌ Invalid selection. Please try again with /add_record.")
    context.user_data.clear()
    return ConversationHandler.END


async def value_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Step D: Handle text input, save record, and send confirmation.
    """
    value_text = update.message.text.strip()
    
    if not value_text:
        await update.message.reply_text(
            "❌ Invalid input. Please send a non-empty text value.\n"
            "Use /cancel to cancel."
        )
        return ENTERING_VALUE
    
    # Retrieve stored data from context
    patient_name = context.user_data.get("selected_patient")
    record_type = context.user_data.get("selected_record_type")
    
    if not patient_name or not record_type:
        await update.message.reply_text(
            "❌ Error: Missing patient or record type. Please start over with /add_record."
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    try:
        # Save record to database
        timestamp = datetime.now()
        db = get_database()
        
        record_id = db.save_record(
            timestamp=timestamp,
            patient=patient_name,
            record_type=record_type,
            data_type="text",  # As per requirements: data_type is "text"
            value=value_text
        )
        
        # Format timestamp for display
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Send confirmation message
        confirmation_message = (
            "✅ **Record Saved Successfully!**\n\n"
            f"📅 Timestamp: {timestamp_str}\n"
            f"👤 Patient: {patient_name}\n"
            f"📋 Record Type: {record_type}\n"
            f"📝 Data Type: text\n"
            f"💾 Value: {value_text}\n"
            f"🆔 Record ID: {record_id}"
        )
        
        await update.message.reply_text(
            confirmation_message,
            parse_mode="Markdown"
        )
        
        logger.info(
            f"User {update.effective_user.id} saved record: "
            f"patient={patient_name}, type={record_type}, value={value_text}"
        )
        
        # Clear context data
        context.user_data.clear()
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error saving record: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Error saving record. Please try again or contact support.\n"
            "Use /cancel to exit."
        )
        return ENTERING_VALUE


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
    Handle unexpected inputs during conversation.
    """
    current_state = context.user_data.get("_conversation_state")
    
    if update.message:
        await update.message.reply_text(
            "❌ I didn't understand that input.\n\n"
            "Please send a text message with the record value, "
            "or use /cancel to exit."
        )
    
    # Stay in current state
    return ENTERING_VALUE


def get_add_record_conversation_handler() -> ConversationHandler:
    """
    Create and return the ConversationHandler for /add_record flow.
    
    Returns:
        ConversationHandler: Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[CommandHandler("add_record", add_record_command)],
        states={
            SELECTING_PATIENT: [
                CallbackQueryHandler(patient_selected, pattern="^(patient_|cancel)"),
            ],
            SELECTING_RECORD_TYPE: [
                CallbackQueryHandler(record_type_selected, pattern="^(type_|cancel)"),
            ],
            ENTERING_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, value_received),
                CommandHandler("cancel", cancel_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_handler),
            MessageHandler(filters.ALL, unexpected_input),
        ],
        name="add_record_conversation",
        persistent=False,
    )

