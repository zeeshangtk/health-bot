"""
Add patient handler.
Handles /add_patient command to dynamically add new patients.
"""
import logging
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

from storage.database import get_database

logger = logging.getLogger(__name__)

# Conversation state
WAITING_FOR_NAME = 1


async def add_patient_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for /add_patient command.
    Asks user for patient's full name.
    """
    await update.message.reply_text(
        "👤 **Add New Patient**\n\n"
        "Please send the patient's full name:\n\n"
        "Use /cancel to cancel.",
        parse_mode="Markdown"
    )
    
    return WAITING_FOR_NAME


async def process_patient_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the patient name input and save to database.
    """
    patient_name = update.message.text.strip()
    
    if not patient_name:
        await update.message.reply_text(
            "❌ Invalid input. Please send a non-empty patient name.\n"
            "Use /cancel to cancel."
        )
        return WAITING_FOR_NAME
    
    try:
        db = get_database()
        success = db.add_patient(patient_name)
        
        if success:
            try:
                await update.message.reply_text(
                    f"✅ Patient *{patient_name}* added successfully!",
                    parse_mode="Markdown"
                )
                logger.info(
                    f"User {update.effective_user.id} added patient: {patient_name}"
                )
            except Exception as send_error:
                # Database save succeeded but failed to send reply
                logger.error(f"Patient saved but failed to send confirmation: {send_error}")
                # Don't fail the operation - patient was saved successfully
        else:
            try:
                await update.message.reply_text(
                    f"⚠️ Patient *{patient_name}* already exists in the database.",
                    parse_mode="Markdown"
                )
            except Exception as send_error:
                logger.error(f"Failed to send duplicate warning: {send_error}")
        
        return ConversationHandler.END
        
    except ValueError as e:
        # Database constraint error
        logger.error(f"Database error adding patient: {e}", exc_info=True)
        try:
            await update.message.reply_text(
                f"❌ Database error: {str(e)}\n"
                "Please try again or use /cancel to exit."
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")
        return WAITING_FOR_NAME
    except Exception as e:
        # Other errors
        logger.error(f"Error adding patient: {e}", exc_info=True)
        try:
            await update.message.reply_text(
                "❌ Error adding patient. Please try again or contact support.\n"
                "Use /cancel to exit."
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")
        return WAITING_FOR_NAME


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /cancel command during add_patient conversation.
    """
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Operation cancelled.\n\n"
        "You're back to the main menu."
    )
    
    return ConversationHandler.END


def get_add_patient_handler() -> ConversationHandler:
    """
    Create and return the ConversationHandler for /add_patient flow.
    
    Returns:
        ConversationHandler: Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[CommandHandler("add_patient", add_patient_command)],
        states={
            WAITING_FOR_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_patient_name),
                CommandHandler("cancel", cancel_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_handler),
        ],
        name="add_patient_conversation",
        persistent=False,
    )

