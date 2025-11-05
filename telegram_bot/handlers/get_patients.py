"""
Get patients handler.
Handles /get_patients command to view all registered patients.
"""
import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from storage.database import get_database

logger = logging.getLogger(__name__)


async def get_patients_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /get_patients command.
    Displays all registered patients from the database.
    """
    db = get_database()
    patients = db.get_patients()
    
    if not patients:
        await update.message.reply_text("⚠️ No patients found.")
        logger.info(f"User {update.effective_user.id} requested patients list (empty)")
        return
    
    # Build formatted message with numbered list
    message_lines = ["🧾 **Registered Patients:**\n"]
    
    for index, patient in enumerate(patients, start=1):
        message_lines.append(f"{index}. {patient['name']}")
    
    message = "\n".join(message_lines)
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )
    
    logger.info(
        f"User {update.effective_user.id} viewed patients list "
        f"({len(patients)} patients)"
    )


def get_get_patients_handler() -> CommandHandler:
    """
    Create and return the CommandHandler for /get_patients command.
    
    Returns:
        CommandHandler: Configured command handler
    """
    return CommandHandler("get_patients", get_patients_command)

