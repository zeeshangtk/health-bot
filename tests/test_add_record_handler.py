"""
Unit tests for add_record handler flow.
Tests that the handler correctly saves records to the database.
"""
import os
import tempfile
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

from handlers.add_record import value_received, ENTERING_VALUE
from storage.database import Database, get_database


# Sample test data
TEST_PATIENT = "Nazra Mastoor"
TEST_RECORD_TYPE = "BP"
TEST_VALUE = "120/80"


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db = Database(db_path=db_path)
    
    # Create test patient (required for foreign key relationship)
    db.add_patient(TEST_PATIENT)
    
    # Patch get_database to return our test database
    with patch('handlers.add_record.get_database', return_value=db):
        yield db
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update object."""
    user = Mock(spec=User)
    user.id = 12345
    user.username = "test_user"
    user.first_name = "Test"
    
    chat = Mock(spec=Chat)
    chat.id = 12345
    
    message = Mock(spec=Message)
    message.text = TEST_VALUE
    message.reply_text = AsyncMock()
    message.chat = chat
    
    update = Mock(spec=Update)
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    
    return update


@pytest.fixture
def mock_context():
    """Create a mock Telegram Context object."""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_value_received_saves_record(temp_db, mock_update, mock_context):
    """Test that value_received saves a record to the database."""
    # Set up context with patient and record type
    mock_context.user_data["selected_patient"] = TEST_PATIENT
    mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    with patch('handlers.add_record.get_database', return_value=temp_db):
        from telegram.ext import ConversationHandler
        result = await value_received(mock_update, mock_context)
    
    # Verify record was saved
    records = temp_db.get_records()
    assert len(records) == 1, "Should have one record saved"
    
    record = records[0]
    assert record.patient == TEST_PATIENT, "Patient should match"
    assert record.record_type == TEST_RECORD_TYPE, "Record type should match"
    assert record.value == TEST_VALUE, "Value should match"
    assert record.data_type == "text", "Data type should be 'text'"
    
    # Verify conversation ended
    assert result == ConversationHandler.END, "Conversation should end"
    
    # Verify confirmation message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "✅" in call_args[0][0] or "Record Saved" in call_args[0][0], \
        "Should send success message"


@pytest.mark.asyncio
async def test_value_received_with_missing_context(temp_db, mock_update, mock_context):
    """Test that value_received handles missing patient/record_type gracefully."""
    # Don't set patient or record_type in context
    mock_context.user_data.clear()
    
    with patch('handlers.add_record.get_database', return_value=temp_db):
        from telegram.ext import ConversationHandler
        result = await value_received(mock_update, mock_context)
    
    # Verify no record was saved
    records = temp_db.get_records()
    assert len(records) == 0, "Should not save record when context is missing"
    
    # Verify error message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌" in call_args[0][0] or "Error" in call_args[0][0], \
        "Should send error message"
    
    # Verify conversation ended
    assert result == ConversationHandler.END, "Conversation should end"


@pytest.mark.asyncio
async def test_value_received_with_empty_value(temp_db, mock_update, mock_context):
    """Test that value_received handles empty input."""
    # Set up context
    mock_context.user_data["selected_patient"] = TEST_PATIENT
    mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    # Set empty value
    mock_update.message.text = "   "  # Whitespace only
    
    with patch('handlers.add_record.get_database', return_value=temp_db):
        result = await value_received(mock_update, mock_context)
    
    # Verify no record was saved
    records = temp_db.get_records()
    assert len(records) == 0, "Should not save empty record"
    
    # Verify error message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌" in call_args[0][0] or "Invalid" in call_args[0][0], \
        "Should send error message for invalid input"
    
    # Verify stays in ENTERING_VALUE state
    assert result == ENTERING_VALUE, "Should stay in ENTERING_VALUE state"


@pytest.mark.asyncio
async def test_value_received_saves_multiple_records(temp_db, mock_update, mock_context):
    """Test that handler can save multiple records."""
    # Set up context
    mock_context.user_data["selected_patient"] = TEST_PATIENT
    mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    test_values = ["120/80", "130/85", "115/75"]
    
    with patch('handlers.add_record.get_database', return_value=temp_db):
        for value in test_values:
            mock_update.message.text = value
            mock_update.message.reply_text.reset_mock()
            
            await value_received(mock_update, mock_context)
            
            # Reset context for next iteration
            mock_context.user_data["selected_patient"] = TEST_PATIENT
            mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    # Verify all records were saved
    records = temp_db.get_records()
    assert len(records) == len(test_values), f"Should have {len(test_values)} records"
    
    # Verify all values match
    saved_values = [r.value for r in records]
    assert set(saved_values) == set(test_values), "All values should be saved"


@pytest.mark.asyncio
async def test_value_received_record_timestamp(temp_db, mock_update, mock_context):
    """Test that saved record has correct timestamp."""
    # Set up context
    mock_context.user_data["selected_patient"] = TEST_PATIENT
    mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    before_save = datetime.now()
    
    with patch('handlers.add_record.get_database', return_value=temp_db):
        await value_received(mock_update, mock_context)
    
    after_save = datetime.now()
    
    # Verify record timestamp is within expected range
    records = temp_db.get_records()
    assert len(records) == 1, "Should have one record"
    
    record_timestamp = records[0].timestamp
    assert before_save <= record_timestamp <= after_save, \
        "Timestamp should be approximately now"


def test_manual_integration_test_instructions():
    """
    Instructions for manual integration testing.
    
    To manually test the add_record flow:
    
    1. Start the bot:
       python bot.py
    
    2. In Telegram:
       - Send /start to initialize
       - Send /add_record
       - Select a patient from inline buttons
       - Select a record type from inline buttons
       - Enter a value (e.g., "120/80" for BP)
    
    3. Verify in database:
       - Check data/health_bot.db
       - Or use /view_records to see the saved entry
    
    Expected behavior:
       - Record is saved with correct patient, type, and value
       - Confirmation message shows all record details
       - Record appears in /view_records output
    """
    # This is a documentation test - no assertions needed
    pass

