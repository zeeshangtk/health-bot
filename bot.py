"""
Health Bot - Main entry point
Uses python-telegram-bot v20.x API
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_TOKEN, load_env
from handlers.add_record import get_add_record_conversation_handler
from handlers.add_patient import get_add_patient_handler
from handlers.get_patients import get_get_patients_handler  # NEW: Get patients handler
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
    
    # Validate token exists and is not empty
    if not TELEGRAM_TOKEN or not TELEGRAM_TOKEN.strip():
        logger.error(
            "TELEGRAM_TOKEN not set! "
            "Please set it in config.py or as TELEGRAM_TOKEN environment variable."
        )
        return
    
    # Create Application with proper token validation
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
    except Exception as e:
        logger.error(f"Failed to create Application: {e}")
        logger.error("Please check that your TELEGRAM_TOKEN is valid.")
        return
    
    # Register conversation handlers (must be registered before command handlers)
    # This ensures they can intercept commands during conversation flow
    application.add_handler(get_add_record_conversation_handler())
    application.add_handler(get_add_patient_handler())  # NEW: Register add_patient handler
    application.add_handler(get_view_records_conversation_handler())
    application.add_handler(get_export_conversation_handler())
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(get_get_patients_handler())  # NEW: Register get_patients handler
    application.add_handler(CommandHandler("cancel", cancel_handler))
    
    # Start polling
    logger.info("Starting bot...")
    logger.info("Bot is polling for updates...")
    
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
    except RuntimeError as e:
        error_msg = str(e).lower()
        if "not properly initialized" in error_msg or "initialize" in error_msg:
            logger.error(
                "Bot initialization failed. This usually means:\n"
                "1. The TELEGRAM_TOKEN is invalid or expired\n"
                "2. There's a network connectivity issue\n"
                "3. The token format is incorrect\n\n"
                "Please verify your token from @BotFather on Telegram."
            )
        else:
            logger.error(f"Runtime error: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error while running bot: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()
