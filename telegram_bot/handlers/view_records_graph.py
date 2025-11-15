"""
View records graph handler.
Displays an HTML graph visualization of a patient's health records.
"""
import logging
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from clients.health_api_client import get_health_api_client

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_PATIENT = range(1)


async def view_records_graph_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for /view_records_graph command.
    Step 1: Present patient list as inline buttons.
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
    for patient in patients:
        keyboard.append([InlineKeyboardButton(patient["name"], callback_data=f"patient_{patient['name']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👤 **Select Patient**\n\n"
        "Please select a patient to view their health records graph:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SELECTING_PATIENT


async def patient_selected_for_graph(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle patient selection, fetch HTML graph, and send it to the user.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")
        return ConversationHandler.END
    
    # Extract patient name from callback data
    if query.data.startswith("patient_"):
        patient_name = query.data.replace("patient_", "")
        
        # Validate patient name
        client = get_health_api_client()
        try:
            patients = await client.get_patients()
            patient_names = [p["name"] for p in patients]
            if patient_name not in patient_names:
                await query.edit_message_text(
                    "❌ Invalid patient selection. Please try again with /view_records_graph."
                )
                return ConversationHandler.END
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            await query.edit_message_text(
                "❌ Error connecting to health service. Please try again later."
            )
            return ConversationHandler.END
        
        try:
            # Fetch HTML graph from API
            html_content = await client.get_html_view(patient_name)
            
            # Send HTML as a document
            # Telegram doesn't support sending HTML directly as a message,
            # so we'll send it as a document
            html_bytes = html_content.encode('utf-8')
            html_file = BytesIO(html_bytes)
            html_file.seek(0)  # Ensure file pointer is at the beginning
            
            await query.edit_message_text(
                f"📊 **Generating graph for {patient_name}...**",
                parse_mode="Markdown"
            )
            
            await query.message.reply_document(
                document=html_file,
                filename=f"{patient_name}_health_records.html",
                caption=f"📊 Health Records Graph for *{patient_name}*\n\nOpen this HTML file in your browser to view the interactive graph.",
                parse_mode="Markdown"
            )
            
            logger.info(
                f"User {update.effective_user.id} viewed graph for patient: {patient_name}"
            )
            
            # Clear context data
            context.user_data.clear()
            
            return ConversationHandler.END
            
        except ConnectionError as e:
            logger.error(f"Connection error fetching HTML graph: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Error connecting to health service. Please try again later."
            )
            context.user_data.clear()
            return ConversationHandler.END
        except ValueError as e:
            logger.error(f"Error fetching HTML graph: {e}", exc_info=True)
            await query.edit_message_text(
                f"❌ Error generating graph: {str(e)}\n\nPlease try again or contact support."
            )
            context.user_data.clear()
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Unexpected error fetching HTML graph: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ An unexpected error occurred. Please try again or contact support."
            )
            context.user_data.clear()
            return ConversationHandler.END
    
    await query.edit_message_text("❌ Invalid selection. Please try again with /view_records_graph.")
    return ConversationHandler.END


async def cancel_graph_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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


def get_view_records_graph_conversation_handler() -> ConversationHandler:
    """
    Create and return the ConversationHandler for /view_records_graph flow.
    
    Returns:
        ConversationHandler: Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[CommandHandler("view_records_graph", view_records_graph_command)],
        states={
            SELECTING_PATIENT: [
                CallbackQueryHandler(patient_selected_for_graph, pattern="^(patient_|cancel)"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_graph_handler),
        ],
        name="view_records_graph_conversation",
        persistent=False,
    )

