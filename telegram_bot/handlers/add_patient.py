"""
Add patient handler.
Handles /add_patient command to dynamically add new patients.
Rate limited to prevent abuse.
"""
import logging
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

from clients.health_api_client import get_health_api_client
from utils.rate_limiter import rate_limit_commands

logger = logging.getLogger(__name__)

# Conversation state
WAITING_FOR_NAME = 1


@rate_limit_commands
async def add_patient_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for /add_patient command.
    Asks user for patient's full name.
    Rate limited to prevent abuse.
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
        client = get_health_api_client()
        result = await client.add_patient(patient_name)
        
        # If we get here, patient was added successfully
        await update.message.reply_text(
            f"✅ Patient *{patient_name}* added successfully!",
            parse_mode="Markdown"
        )
        logger.info(
            f"User {update.effective_user.id} added patient: {patient_name}"
        )
        
        return ConversationHandler.END
        
    except ValueError as e:
        # Patient already exists or API error
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "409" in error_msg:
            await update.message.reply_text(
                f"⚠️ Patient *{patient_name}* already exists.",
                parse_mode="Markdown"
            )
        else:
            logger.error(f"API error adding patient: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Error: {error_msg}\n"
                "Please try again or use /cancel to exit."
            )
        return WAITING_FOR_NAME
    except ConnectionError as e:
        logger.error(f"Connection error adding patient: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Error connecting to health service. Please try again later."
        )
        return WAITING_FOR_NAME
    except Exception as e:
        # Other errors
        logger.error(f"Unexpected error adding patient: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Error adding patient. Please try again or contact support.\n"
            "Use /cancel to exit."
        )
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

