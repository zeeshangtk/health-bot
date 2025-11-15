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
from handlers.view_records_graph import get_view_records_graph_conversation_handler
from handlers.export import get_export_conversation_handler
from handlers.upload_record import get_upload_record_conversation_handler
from handlers.unknown_command import get_unknown_command_handler, get_help_callback_handler


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


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle errors in the telegram bot.
    Logs errors and attempts to notify the user if possible.
    """
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    # Try to notify the user if we have an update
    if isinstance(update, Update) and update.effective_message:
        try:
            # Check if it's a network/connection error
            error_str = str(context.error).lower()
            if any(keyword in error_str for keyword in ['connection', 'network', 'timeout', 'ssl', 'tls']):
                error_msg = (
                    "⚠️ Network error occurred. "
                    "Please check your internet connection and try again in a moment."
                )
            else:
                error_msg = (
                    "❌ An error occurred while processing your request. "
                    "Please try again or contact support if the issue persists."
                )
            
            await update.effective_message.reply_text(error_msg)
        except Exception as e:
            logger.error(f"Error sending error message to user: {e}")


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
    application.add_handler(get_view_records_graph_conversation_handler())
    application.add_handler(get_export_conversation_handler())
    application.add_handler(get_upload_record_conversation_handler())
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(get_get_patients_handler())  # NEW: Register get_patients handler
    application.add_handler(CommandHandler("cancel", cancel_handler))
    
    # Register callback handler for help buttons (from unknown command handler)
    # This should be registered before the unknown command handler
    application.add_handler(get_help_callback_handler())
    
    # Register fallback handler for unknown commands/messages
    # IMPORTANT: This must be registered LAST so it only triggers when no other
    # handler matches. Handlers are checked in registration order, so any
    # unrecognized text/command will fall through to this handler.
    application.add_handler(get_unknown_command_handler())
    
    # Register error handler
    application.add_error_handler(error_handler)
    
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
