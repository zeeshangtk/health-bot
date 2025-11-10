"""
Unknown command handler (fallback).
Catches any unrecognized commands or text messages and provides a helpful guide.
This handler should be registered LAST so it only runs if no other handler matches.

Integration:
This handler is registered after all other handlers in bot.py to catch:
1. Unknown commands (commands starting with / that aren't registered)
2. Text messages that don't match any conversation flow

When registered last, python-telegram-bot will only trigger this handler if
none of the previous handlers (CommandHandler, ConversationHandler, etc.) matched.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)

# List of all recognized commands in the bot
# Used for logging/reference, actual matching is done by handler registration order
RECOGNIZED_COMMANDS = [
    "/start",
    "/add_record",
    "/upload_record",
    "/view_records",
    "/add_patient",
    "/get_patients",
    "/export",
    "/cancel",
]


async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Fallback handler for unrecognized commands or messages.
    
    This handler catches:
    - Unknown commands (e.g., /unknown_command)
    - Any text message that doesn't match existing conversation flows (only in private chats)
    
    In group chats, this handler only responds to:
    - Unknown commands
    - Messages that mention the bot
    
    Provides a helpful guide message with all available commands and optional
    inline keyboard buttons for easy access.
    
    Note: This handler is registered with low priority (last) so it only
    triggers when no other handler has matched the message.
    """
    # Safety check: ensure we have a message to reply to
    if not update.message:
        logger.warning("Unknown command handler triggered but no message found in update")
        return
    
    # Check if this is a group chat
    chat = update.effective_chat
    is_group = chat.type in ["group", "supergroup"]
    
    # Extract the message text
    message_text = update.message.text if update.message.text else ""
    
    # Check if this is a bot command (unknown command)
    is_command = False
    if update.message.entities:
        # Check if the message has a bot_command entity
        for entity in update.message.entities:
            if entity.type == "bot_command":
                is_command = True
                # Extract the command from the message
                command_text = message_text[entity.offset:entity.offset + entity.length]
                logger.info(
                    f"User {update.effective_user.id} sent unknown command: {command_text}"
                )
                break
    
    # In group chats, only respond to commands or when bot is mentioned at the start
    if is_group:
        # Check if bot is mentioned in the message (only at the start or as part of command)
        bot_mentioned = False
        if update.message.entities:
            bot_username = context.bot.username if context.bot.username else None
            bot_id = context.bot.id
            
            for entity in update.message.entities:
                # Check for @username mentions - only if at start of message (offset 0)
                # or if it's part of a command context
                if entity.type == "mention" and bot_username:
                    mention_text = message_text[entity.offset:entity.offset + entity.length]
                    if mention_text == f"@{bot_username}":
                        # Only respond if mention is at the start of the message
                        # This prevents responding to casual mentions in conversation
                        if entity.offset == 0:
                            bot_mentioned = True
                            break
                # Check for text_mention (when user is mentioned by name)
                elif entity.type == "text_mention" and hasattr(entity, 'user'):
                    if entity.user and entity.user.id == bot_id:
                        # Only respond if mention is at the start
                        if entity.offset == 0:
                            bot_mentioned = True
                            break
        
        # If it's not a command and bot is not mentioned at the start, ignore the message
        if not is_command and not bot_mentioned:
            logger.debug(
                f"Ignoring non-command message in group chat from user {update.effective_user.id}"
            )
            return
    
    # Log the unrecognized input
    user_id = update.effective_user.id
    if not is_command:
        logger.info(
            f"User {user_id} sent unrecognized message: {message_text[:50]}"
        )
    
    # Build the help message
    help_message = (
        "🤔 Sorry, I didn't understand that command.\n\n"
        "Here are the commands I support:\n\n"
        "/add_record — Add a new medical record (text or photo)\n"
        "/upload_record — Upload a medical lab report image\n"
        "/view_records — View recent records\n"
        "/add_patient — Add a new patient\n"
        "/get_patients — List all patients\n"
        "/export — Export records as CSV/JSON\n"
        "/cancel — Cancel current operation\n"
        "/start — Start or restart the bot"
    )
    
    # Create inline keyboard with command buttons for convenience
    # Note: These buttons provide visual prompts; users still need to type commands
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Record", callback_data="/add_record"),
            InlineKeyboardButton("📸 Upload Record", callback_data="/upload_record"),
        ],
        [
            InlineKeyboardButton("👁️ View Records", callback_data="/view_records"),
            InlineKeyboardButton("📥 Export", callback_data="/export"),
        ],
        [
            InlineKeyboardButton("➕ Add Patient", callback_data="/add_patient"),
            InlineKeyboardButton("👥 Get Patients", callback_data="/get_patients"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="/cancel"),
            InlineKeyboardButton("🏠 Start", callback_data="/start"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the help message with inline keyboard
    # Add error handling for network issues (timeouts, connection errors, etc.)
    try:
        await update.message.reply_text(
            help_message,
            reply_markup=reply_markup
        )
    except Exception as e:
        # Log the error but don't crash the bot
        logger.error(
            f"Failed to send help message to user {user_id}: {e}",
            exc_info=True
        )
        # Try to send a simpler message without the keyboard as fallback
        try:
            await update.message.reply_text(
                help_message
            )
        except Exception as fallback_error:
            logger.error(
                f"Failed to send fallback help message to user {user_id}: {fallback_error}",
                exc_info=True
            )


async def help_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries from inline keyboard buttons.
    Executes the command associated with the button press by creating a synthetic
    message update and processing it through the application's handler chain.
    """
    if not update.callback_query:
        logger.warning("Help callback handler triggered but no callback_query found")
        return
    
    query = update.callback_query
    
    # Answer the callback query first to provide user feedback
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Failed to answer callback query: {e}", exc_info=True)
        return
    
    # Extract command from callback data (format: "/command_name")
    callback_data = query.data
    if not callback_data or not callback_data.startswith("/"):
        logger.warning(f"Invalid callback data: {callback_data}")
        return
    
    command = callback_data.strip()
    
    # Validate it's a recognized command
    if command not in RECOGNIZED_COMMANDS:
        logger.warning(f"Unrecognized command in callback: {command}")
        return
    
    logger.info(f"User {query.from_user.id} clicked button for {command}")
    
    # Create a synthetic message to simulate the user sending the command
    # We'll use the callback query's message as a template and modify the text
    try:
        from telegram import Message
        from telegram.constants import MessageEntityType
        
        # Get the original message as a base
        original_msg = query.message
        
        # Create command entity to mark the command in the message
        # This helps CommandHandler recognize it as a command
        from telegram import MessageEntity
        command_entity = MessageEntity(
            type=MessageEntityType.BOT_COMMAND,
            offset=0,
            length=len(command)
        )
        
        # Create a new Message object with the command as text
        # We need to construct it with the bot instance and proper entities
        synthetic_message = Message(
            message_id=original_msg.message_id + 1000000,  # Offset to avoid conflicts
            from_user=query.from_user,
            date=original_msg.date,
            chat=original_msg.chat,
            text=command,
            entities=[command_entity],  # Mark it as a bot command
            bot=context.bot  # Important: need the bot instance
        )
        
        # Create a synthetic Update with the message
        synthetic_update = Update(
            update_id=update.update_id + 1000000,  # Offset to avoid conflicts
            message=synthetic_message
        )
        
        # Process the synthetic update through the application
        # This will trigger the appropriate command handler
        if hasattr(context, 'application') and context.application:
            await context.application.process_update(synthetic_update)
        else:
            # Fallback if application is not available
            await query.message.reply_text(
                f"Please type {command} in the chat to use this feature."
            )
            
    except Exception as e:
        logger.error(
            f"Failed to process command {command} from callback: {e}",
            exc_info=True
        )
        # Fallback: inform user to type the command manually
        try:
            await query.message.reply_text(
                f"Please type {command} in the chat to use this feature."
            )
        except Exception as fallback_error:
            logger.error(
                f"Failed to send fallback message: {fallback_error}",
                exc_info=True
            )


def get_unknown_command_handler() -> MessageHandler:
    """
    Create and return the MessageHandler for unknown commands/messages.
    
    This handler catches any text message (including commands) that doesn't
    match existing handlers. In python-telegram-bot, handlers are checked in
    registration order, and CommandHandler has priority for commands.
    Therefore, this MessageHandler will only catch:
    - Unknown commands (commands not registered with CommandHandler)
    - Text messages that don't match any ConversationHandler state
    
    In group chats, the handler will only respond to:
    - Commands (handled by the handler logic)
    - Messages that mention the bot (handled by the handler logic)
    
    Integration note: This handler must be registered LAST (after all other
    handlers) in bot.py's main() function to ensure it only triggers as a
    fallback when no other handler matches.
    
    Returns:
        MessageHandler: Configured message handler with TEXT filter
    """
    # Filter to match text messages, commands, or messages mentioning the bot
    # The handler logic will further filter to ignore casual group chat messages
    return MessageHandler(
        filters.TEXT | filters.COMMAND,
        unknown_command_handler
    )


def get_help_callback_handler():
    """
    Create and return a CallbackQueryHandler for help button callbacks.
    
    Returns:
        CallbackQueryHandler: Handler for inline keyboard button presses
    """
    from telegram.ext import CallbackQueryHandler
    # Match any callback data that starts with "/" (command format)
    return CallbackQueryHandler(
        help_callback_handler,
        pattern="^/"  # Match callbacks starting with "/" (command format)
    )

