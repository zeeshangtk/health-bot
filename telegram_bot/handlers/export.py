"""
Export handler.
Allows exporting health records as CSV or JSON files.
"""
import csv
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import SUPPORTED_RECORD_TYPES
from storage.database import get_database

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_PATIENT, SELECTING_FORMAT = range(2)


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point for /export command.
    Step 1: Present patient list (including "All" option) as inline buttons.
    """
    db = get_database()
    patients = db.get_patients()
    
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
        "Please select a patient (or All) to export:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SELECTING_PATIENT


async def patient_selected_for_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Step 2: Handle patient selection and present format options (CSV/JSON).
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
            db = get_database()
            patients = db.get_patients()
            patient_names = [p["name"] for p in patients]
            if patient_name not in patient_names:
                await query.edit_message_text(
                    "❌ Invalid patient selection. Please try again with /export."
                )
                return ConversationHandler.END
        
        # Store patient in context
        context.user_data["selected_patient"] = patient_name
        
        # Create inline keyboard with format options
        keyboard = [
            [InlineKeyboardButton("📄 CSV", callback_data="format_CSV")],
            [InlineKeyboardButton("📋 JSON", callback_data="format_JSON")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        patient_display = "All Patients" if patient_name == "ALL" else patient_name
        
        await query.edit_message_text(
            f"📤 **Step 2 of 2: Select Export Format**\n\n"
            f"Patient: *{patient_display}*\n\n"
            f"Please select the export format:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SELECTING_FORMAT
    
    await query.edit_message_text("❌ Invalid selection. Please try again with /export.")
    return ConversationHandler.END


def _create_csv_file(records, file_path: Path) -> None:
    """
    Create a CSV file from records.
    
    Args:
        records: List of HealthRecord objects
        file_path: Path where CSV file should be created
    """
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['timestamp', 'patient', 'record_type', 'data_type', 'value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for record in records:
            writer.writerow({
                'timestamp': record.timestamp.isoformat(),
                'patient': record.patient,
                'record_type': record.record_type,
                'data_type': record.data_type,
                'value': record.value
            })


def _create_json_file(records, file_path: Path) -> None:
    """
    Create a JSON file from records.
    
    Args:
        records: List of HealthRecord objects
        file_path: Path where JSON file should be created
    """
    records_data = []
    for record in records:
        records_data.append({
            'timestamp': record.timestamp.isoformat(),
            'patient': record.patient,
            'record_type': record.record_type,
            'data_type': record.data_type,
            'value': record.value
        })
    
    with open(file_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(records_data, jsonfile, indent=2, ensure_ascii=False)


async def format_selected_for_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Step 3: Handle format selection, create file, send it, and clean up.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Operation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Extract format from callback data
    if query.data.startswith("format_"):
        export_format = query.data.replace("format_", "")
        
        # Validate format
        if export_format not in ["CSV", "JSON"]:
            await query.edit_message_text(
                "❌ Invalid format selection. Please try again with /export."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        # Retrieve stored patient from context
        patient_name = context.user_data.get("selected_patient")
        
        if not patient_name:
            await query.edit_message_text(
                "❌ Error: Missing patient selection. Please start over with /export."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        temp_file = None
        
        try:
            # Fetch records from database
            db = get_database()
            
            # Convert "ALL" to None for database query
            patient_filter = None if patient_name == "ALL" else patient_name
            
            records = db.get_records(patient=patient_filter)
            
            if not records:
                patient_display = "All Patients" if patient_name == "ALL" else patient_name
                await query.edit_message_text(
                    f"📋 **No Records Found**\n\n"
                    f"Patient: *{patient_display}*\n\n"
                    f"No records to export.",
                    parse_mode="Markdown"
                )
                context.user_data.clear()
                return ConversationHandler.END
            
            # Create temporary file
            patient_display = "All_Patients" if patient_name == "ALL" else patient_name.replace(" ", "_")
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = "csv" if export_format == "CSV" else "json"
            filename = f"health_records_{patient_display}_{timestamp_str}.{file_extension}"
            
            # Use tempfile to create a temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=f".{file_extension}", prefix="health_export_")
            temp_file = Path(temp_path)
            
            # Close the file descriptor as we'll open it properly below
            os.close(temp_fd)
            
            # Create the export file
            if export_format == "CSV":
                _create_csv_file(records, temp_file)
            else:  # JSON
                _create_json_file(records, temp_file)
            
            # Send file to user
            patient_display_text = "All Patients" if patient_name == "ALL" else patient_name
            
            await query.edit_message_text(
                f"📤 **Exporting Records...**\n\n"
                f"Patient: *{patient_display_text}*\n"
                f"Format: *{export_format}*\n"
                f"Records: *{len(records)}*\n\n"
                f"Preparing file...",
                parse_mode="Markdown"
            )
            
            # Send the file as a document
            with open(temp_file, 'rb') as file:
                await update.effective_chat.send_document(
                    document=file,
                    filename=filename,
                    caption=(
                        f"📤 **Health Records Export**\n\n"
                        f"Patient: {patient_display_text}\n"
                        f"Format: {export_format}\n"
                        f"Records: {len(records)}"
                    ),
                    parse_mode="Markdown"
                )
            
            logger.info(
                f"User {update.effective_user.id} exported records: "
                f"patient={patient_name}, format={export_format}, count={len(records)}"
            )
            
            # Clear context data
            context.user_data.clear()
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error exporting records: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Error exporting records. Please try again or contact support."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        finally:
            # Clean up temporary file
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")
    
    await query.edit_message_text("❌ Invalid selection. Please try again with /export.")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_export_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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


def get_export_conversation_handler() -> ConversationHandler:
    """
    Create and return the ConversationHandler for /export flow.
    
    Returns:
        ConversationHandler: Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[CommandHandler("export", export_command)],
        states={
            SELECTING_PATIENT: [
                CallbackQueryHandler(patient_selected_for_export, pattern="^(patient_|cancel)"),
            ],
            SELECTING_FORMAT: [
                CallbackQueryHandler(format_selected_for_export, pattern="^(format_|cancel)"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_export_handler),
        ],
        name="export_conversation",
        persistent=False,
    )

