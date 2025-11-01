"""
Health Bot - Main entry point
Uses python-telegram-bot v20.x API
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_TOKEN, load_env
from handlers.add_record import get_add_record_conversation_handler
from handlers.view import get_view_records_conversation_handler
from handlers.export import get_export_conversation_handler


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /start command.
    Provides a friendly welcome message.
    """
    user = update.effective_user
    welcome_message = (
        f"Hello {user.first_name}! 👋\n\n"
        f"Welcome to the Health Bot!\n\n"
        f"I can help you record and track health measurements.\n"
        f"Use /help to see available commands."
    )
    
    await update.message.reply_text(welcome_message)
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    # TODO: Add initial onboarding flow here


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /cancel command.
    Cancels any ongoing operation and returns to main menu.
    """
    # Clear any stored conversation data
    context.user_data.clear()
    
    cancel_message = (
        "Operation cancelled.\n\n"
        "You're back to the main menu. What would you like to do?"
    )
    
    await update.message.reply_text(cancel_message)
    logger.info(f"User {update.effective_user.id} cancelled operation")


def main() -> None:
    """
    Main function to start the bot.
    Loads configuration and starts polling.
    """
    # Try to load token from environment variable
    load_env()
    
    if not TELEGRAM_TOKEN:
        logger.error(
            "TELEGRAM_TOKEN not set! "
            "Please set it in config.py or as TELEGRAM_TOKEN environment variable."
        )
        return
    
    # Create Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register conversation handlers (must be registered before command handlers)
    # This ensures they can intercept commands during conversation flow
    application.add_handler(get_add_record_conversation_handler())
    application.add_handler(get_view_records_conversation_handler())
    application.add_handler(get_export_conversation_handler())
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("cancel", cancel_handler))
    
    # Start polling
    logger.info("Starting bot...")
    logger.info("Bot is polling for updates...")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Error while running bot: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()
