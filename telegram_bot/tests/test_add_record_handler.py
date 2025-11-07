"""
Unit tests for add_record handler flow.
Tests that the handler correctly saves records via the Health Service API.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

from handlers.add_record import value_received, ENTERING_VALUE
from clients.health_api_client import HealthAPIClient


# Sample test data
TEST_PATIENT = "Nazra Mastoor"
TEST_RECORD_TYPE = "BP"
TEST_VALUE = "120/80"

TEST_RECORD_RESPONSE = {
    "timestamp": "2025-01-01T10:00:00",
    "patient": TEST_PATIENT,
    "record_type": TEST_RECORD_TYPE,
    "data_type": "text",
    "value": TEST_VALUE
}


@pytest.fixture
def mock_api_client():
    """Create a mock HealthAPIClient for testing."""
    client = Mock(spec=HealthAPIClient)
    return client


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
async def test_value_received_saves_record(mock_api_client, mock_update, mock_context):
    """Test that value_received saves a record via the API."""
    # Set up context with patient and record type
    mock_context.user_data["selected_patient"] = TEST_PATIENT
    mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    # Mock the API client response
    mock_api_client.save_record = AsyncMock(return_value=TEST_RECORD_RESPONSE)
    
    with patch('handlers.add_record.get_health_api_client', return_value=mock_api_client):
        from telegram.ext import ConversationHandler
        result = await value_received(mock_update, mock_context)
    
    # Verify API was called correctly
    mock_api_client.save_record.assert_called_once()
    call_kwargs = mock_api_client.save_record.call_args[1]
    assert call_kwargs["patient"] == TEST_PATIENT
    assert call_kwargs["record_type"] == TEST_RECORD_TYPE
    assert call_kwargs["value"] == TEST_VALUE
    assert call_kwargs["data_type"] == "text"
    assert isinstance(call_kwargs["timestamp"], datetime)
    
    # Verify conversation ended
    assert result == ConversationHandler.END, "Conversation should end"
    
    # Verify confirmation message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "✅" in call_args[0][0] or "Record Saved" in call_args[0][0], \
        "Should send success message"


@pytest.mark.asyncio
async def test_value_received_with_missing_context(mock_api_client, mock_update, mock_context):
    """Test that value_received handles missing patient/record_type gracefully."""
    # Don't set patient or record_type in context
    mock_context.user_data.clear()
    
    mock_api_client.save_record = AsyncMock()
    
    with patch('handlers.add_record.get_health_api_client', return_value=mock_api_client):
        from telegram.ext import ConversationHandler
        result = await value_received(mock_update, mock_context)
    
    # Verify API was not called
    mock_api_client.save_record.assert_not_called()
    
    # Verify error message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌" in call_args[0][0] or "Error" in call_args[0][0], \
        "Should send error message"
    
    # Verify conversation ended
    assert result == ConversationHandler.END, "Conversation should end"


@pytest.mark.asyncio
async def test_value_received_with_empty_value(mock_api_client, mock_update, mock_context):
    """Test that value_received handles empty input."""
    # Set up context
    mock_context.user_data["selected_patient"] = TEST_PATIENT
    mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    # Set empty value
    mock_update.message.text = "   "  # Whitespace only
    
    mock_api_client.save_record = AsyncMock()
    
    with patch('handlers.add_record.get_health_api_client', return_value=mock_api_client):
        result = await value_received(mock_update, mock_context)
    
    # Verify API was not called
    mock_api_client.save_record.assert_not_called()
    
    # Verify error message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌" in call_args[0][0] or "Invalid" in call_args[0][0], \
        "Should send error message for invalid input"
    
    # Verify stays in ENTERING_VALUE state
    assert result == ENTERING_VALUE, "Should stay in ENTERING_VALUE state"


@pytest.mark.asyncio
async def test_value_received_saves_multiple_records(mock_api_client, mock_update, mock_context):
    """Test that handler can save multiple records."""
    # Set up context
    mock_context.user_data["selected_patient"] = TEST_PATIENT
    mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    test_values = ["120/80", "130/85", "115/75"]
    mock_api_client.save_record = AsyncMock(side_effect=[
        {**TEST_RECORD_RESPONSE, "value": value} for value in test_values
    ])
    
    with patch('handlers.add_record.get_health_api_client', return_value=mock_api_client):
        for value in test_values:
            mock_update.message.text = value
            mock_update.message.reply_text.reset_mock()
            
            await value_received(mock_update, mock_context)
            
            # Reset context for next iteration
            mock_context.user_data["selected_patient"] = TEST_PATIENT
            mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    # Verify API was called for each value
    assert mock_api_client.save_record.call_count == len(test_values)
    
    # Verify all values were passed correctly
    call_values = [call[1]["value"] for call in mock_api_client.save_record.call_args_list]
    assert set(call_values) == set(test_values), "All values should be saved"


@pytest.mark.asyncio
async def test_value_received_record_timestamp(mock_api_client, mock_update, mock_context):
    """Test that saved record has correct timestamp."""
    # Set up context
    mock_context.user_data["selected_patient"] = TEST_PATIENT
    mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    before_save = datetime.now()
    
    # Mock API response with current timestamp
    mock_response = {**TEST_RECORD_RESPONSE}
    mock_api_client.save_record = AsyncMock(return_value=mock_response)
    
    with patch('handlers.add_record.get_health_api_client', return_value=mock_api_client):
        await value_received(mock_update, mock_context)
    
    after_save = datetime.now()
    
    # Verify timestamp was passed correctly to API
    call_kwargs = mock_api_client.save_record.call_args[1]
    timestamp = call_kwargs["timestamp"]
    assert isinstance(timestamp, datetime)
    assert before_save <= timestamp <= after_save, \
        "Timestamp should be approximately now"


@pytest.mark.asyncio
async def test_value_received_api_connection_error(mock_api_client, mock_update, mock_context):
    """Test that value_received handles API connection errors gracefully."""
    # Set up context
    mock_context.user_data["selected_patient"] = TEST_PATIENT
    mock_context.user_data["selected_record_type"] = TEST_RECORD_TYPE
    
    # Mock connection error
    mock_api_client.save_record = AsyncMock(side_effect=ConnectionError("Connection failed"))
    
    with patch('handlers.add_record.get_health_api_client', return_value=mock_api_client):
        result = await value_received(mock_update, mock_context)
    
    # Verify error message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "❌" in call_args[0][0] or "Error" in call_args[0][0].lower(), \
        "Should send error message for connection error"
    
    # Verify stays in ENTERING_VALUE state (allows retry)
    assert result == ENTERING_VALUE, "Should stay in ENTERING_VALUE to allow retry"


def test_manual_integration_test_instructions():
    """
    Instructions for manual integration testing.
    
    To manually test the add_record flow:
    
    1. Start the Health Service API:
       cd health_svc
       python main.py
    
    2. Start the bot:
       cd telegram_bot
       python bot.py
    
    3. In Telegram:
       - Send /start to initialize
       - Send /add_record
       - Select a patient from inline buttons
       - Select a record type from inline buttons
       - Enter a value (e.g., "120/80" for BP)
    
    4. Verify via API:
       - curl http://localhost:8000/api/v1/records
       - Or use /view_records to see the saved entry
    
    Expected behavior:
       - Record is saved via API with correct patient, type, and value
       - Confirmation message shows all record details
       - Record appears in /view_records output
    """
    # This is a documentation test - no assertions needed
    pass

