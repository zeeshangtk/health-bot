"""
Unit tests for the post-upload review checklist in upload_record.py:
building the keyboard, toggling rows, and the edit/delete flows.
"""
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch

os.environ.setdefault("TELEGRAM_TOKEN", "test-telegram-token")
os.environ.setdefault("HEALTH_SVC_API_KEY", "test-api-key-for-testing-purposes-12345678")

from telegram import Update, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes

from handlers.upload_record import (
    _build_review_keyboard,
    _build_review_text,
    review_toggle_callback,
    review_edit_start_callback,
    review_edit_cancel_callback,
    review_edit_value_received,
    review_delete_start_callback,
    review_delete_confirm_callback,
    review_delete_cancel_callback,
    REVIEW_STATE_KEY,
)
from clients.health_api_client import HealthAPIClient


def make_review():
    """A 2-row review, matching what _finalize_upload_success would build."""
    return {
        "rows": [["Creatinine", "1.1", "mg/dL"], ["BP", "120/80", "mmHg"]],
        "checked": [False, False],
        "record_ids": [101, 102],
        "deleted": [False, False],
        "pending_delete": None,
        "header_lines": ["✅ <b>Lab Report Processed</b>"],
    }


@pytest.fixture
def mock_api_client():
    return Mock(spec=HealthAPIClient)


@pytest.fixture
def mock_context():
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.chat_data = {}
    context.bot = Mock()
    context.bot.edit_message_text = AsyncMock()
    return context


def make_callback_update(callback_data, message_id=555, chat_id=999):
    chat = Mock(spec=Chat)
    chat.id = chat_id

    message = Mock(spec=Message)
    message.message_id = message_id
    message.reply_text = AsyncMock()

    query = Mock(spec=CallbackQuery)
    query.data = callback_data
    query.message = message
    query.answer = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = Mock(spec=Update)
    update.callback_query = query
    update.effective_chat = chat
    return update


class TestBuildReviewKeyboard:
    def test_active_row_has_toggle_edit_delete_buttons(self):
        review = make_review()
        keyboard = _build_review_keyboard(review)

        row_buttons = keyboard.inline_keyboard[0]
        assert len(row_buttons) == 3
        assert row_buttons[0].callback_data == "rvw_toggle:0"
        assert row_buttons[1].callback_data == "rvw_edit:0"
        assert row_buttons[2].callback_data == "rvw_del:0"

    def test_row_without_record_id_has_no_edit_delete_buttons(self):
        review = make_review()
        review["record_ids"][0] = None
        keyboard = _build_review_keyboard(review)

        row_buttons = keyboard.inline_keyboard[0]
        assert len(row_buttons) == 1
        assert row_buttons[0].callback_data == "rvw_toggle:0"

    def test_deleted_row_shows_disabled_marker(self):
        review = make_review()
        review["deleted"][0] = True
        keyboard = _build_review_keyboard(review)

        row_buttons = keyboard.inline_keyboard[0]
        assert len(row_buttons) == 1
        assert row_buttons[0].callback_data == "rvw_noop"
        assert "deleted" in row_buttons[0].text.lower()

    def test_pending_delete_shows_confirm_sub_row(self):
        review = make_review()
        review["pending_delete"] = 1
        keyboard = _build_review_keyboard(review)

        # Row 0 unaffected, row 1 replaced by a prompt + yes/no row
        assert keyboard.inline_keyboard[0][0].callback_data == "rvw_toggle:0"
        assert keyboard.inline_keyboard[1][0].callback_data == "rvw_noop"
        confirm_row = keyboard.inline_keyboard[2]
        assert confirm_row[0].callback_data == "rvw_del_confirm:1"
        assert confirm_row[1].callback_data == "rvw_del_cancel:1"


def test_build_review_text_shows_deleted_placeholder():
    review = make_review()
    review["deleted"][0] = True
    text = _build_review_text(review)
    assert "(deleted)" in text
    assert "1.1" not in text  # original value no longer shown for the deleted row


@pytest.mark.asyncio
class TestReviewToggle:
    async def test_toggle_flips_checked_state(self, mock_context):
        review = make_review()
        update = make_callback_update("rvw_toggle:0")
        mock_context.chat_data[REVIEW_STATE_KEY] = {555: review}

        await review_toggle_callback(update, mock_context)

        assert review["checked"][0] is True
        update.callback_query.edit_message_reply_markup.assert_called_once()

    async def test_toggle_on_expired_review_shows_alert(self, mock_context):
        update = make_callback_update("rvw_toggle:0")

        await review_toggle_callback(update, mock_context)

        update.callback_query.answer.assert_called_once()
        assert update.callback_query.answer.call_args[1].get("show_alert") is True


@pytest.mark.asyncio
class TestReviewEditFlow:
    async def test_edit_start_sets_pending_edit_and_prompts(self, mock_context):
        review = make_review()
        update = make_callback_update("rvw_edit:0")
        mock_context.chat_data[REVIEW_STATE_KEY] = {555: review}

        await review_edit_start_callback(update, mock_context)

        assert mock_context.chat_data["pending_edit"] == {
            "message_id": 555, "idx": 0, "record_id": 101
        }
        update.callback_query.message.reply_text.assert_called_once()

    async def test_edit_start_without_record_id_shows_alert(self, mock_context):
        review = make_review()
        review["record_ids"][0] = None
        update = make_callback_update("rvw_edit:0")
        mock_context.chat_data[REVIEW_STATE_KEY] = {555: review}

        await review_edit_start_callback(update, mock_context)

        assert "pending_edit" not in mock_context.chat_data
        update.callback_query.answer.assert_called_once()
        assert update.callback_query.answer.call_args[1].get("show_alert") is True

    async def test_value_received_updates_record_and_row(self, mock_context, mock_api_client):
        review = make_review()
        mock_context.chat_data[REVIEW_STATE_KEY] = {555: review}
        mock_context.chat_data["pending_edit"] = {"message_id": 555, "idx": 0, "record_id": 101}
        mock_api_client.update_record = AsyncMock(return_value={})

        chat = Mock(spec=Chat)
        chat.id = 999
        message = Mock(spec=Message)
        message.text = "1.2"
        message.reply_text = AsyncMock()

        update = Mock(spec=Update)
        update.message = message
        update.effective_chat = chat

        with patch("handlers.upload_record.get_health_api_client", return_value=mock_api_client):
            await review_edit_value_received(update, mock_context)

        mock_api_client.update_record.assert_called_once_with(101, value="1.2")
        assert review["rows"][0][1] == "1.2"
        assert "pending_edit" not in mock_context.chat_data
        mock_context.bot.edit_message_text.assert_called_once()
        message.reply_text.assert_called_once()

    async def test_value_received_ignores_when_no_pending_edit(self, mock_context, mock_api_client):
        message = Mock(spec=Message)
        message.text = "1.2"
        message.reply_text = AsyncMock()
        update = Mock(spec=Update)
        update.message = message

        with patch("handlers.upload_record.get_health_api_client", return_value=mock_api_client):
            await review_edit_value_received(update, mock_context)

        mock_api_client.update_record.assert_not_called()
        message.reply_text.assert_not_called()

    async def test_value_received_handles_record_not_found(self, mock_context, mock_api_client):
        review = make_review()
        mock_context.chat_data[REVIEW_STATE_KEY] = {555: review}
        mock_context.chat_data["pending_edit"] = {"message_id": 555, "idx": 0, "record_id": 101}
        mock_api_client.update_record = AsyncMock(side_effect=ValueError("API error 404: not found"))

        message = Mock(spec=Message)
        message.text = "1.2"
        message.reply_text = AsyncMock()
        update = Mock(spec=Update)
        update.message = message

        with patch("handlers.upload_record.get_health_api_client", return_value=mock_api_client):
            await review_edit_value_received(update, mock_context)

        assert "pending_edit" not in mock_context.chat_data
        assert review["rows"][0][1] == "1.1"  # unchanged
        message.reply_text.assert_called_once()
        assert "❌" in message.reply_text.call_args[0][0]

    async def test_edit_cancel_clears_pending_edit(self, mock_context):
        mock_context.chat_data["pending_edit"] = {"message_id": 555, "idx": 0, "record_id": 101}
        update = make_callback_update("rvw_edit_cancel")

        await review_edit_cancel_callback(update, mock_context)

        assert "pending_edit" not in mock_context.chat_data
        update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
class TestReviewDeleteFlow:
    async def test_delete_start_sets_pending_delete(self, mock_context):
        review = make_review()
        update = make_callback_update("rvw_del:0")
        mock_context.chat_data[REVIEW_STATE_KEY] = {555: review}

        await review_delete_start_callback(update, mock_context)

        assert review["pending_delete"] == 0
        update.callback_query.edit_message_reply_markup.assert_called_once()

    async def test_delete_confirm_calls_delete_and_marks_row_deleted(self, mock_context, mock_api_client):
        review = make_review()
        review["pending_delete"] = 0
        update = make_callback_update("rvw_del_confirm:0")
        mock_context.chat_data[REVIEW_STATE_KEY] = {555: review}
        mock_api_client.delete_record = AsyncMock(return_value=None)

        with patch("handlers.upload_record.get_health_api_client", return_value=mock_api_client):
            await review_delete_confirm_callback(update, mock_context)

        mock_api_client.delete_record.assert_called_once_with(101)
        assert review["deleted"][0] is True
        assert review["pending_delete"] is None
        mock_context.bot.edit_message_text.assert_called_once()

    async def test_delete_confirm_handles_record_not_found(self, mock_context, mock_api_client):
        review = make_review()
        review["pending_delete"] = 0
        update = make_callback_update("rvw_del_confirm:0")
        mock_context.chat_data[REVIEW_STATE_KEY] = {555: review}
        mock_api_client.delete_record = AsyncMock(side_effect=ValueError("API error 404: not found"))

        with patch("handlers.upload_record.get_health_api_client", return_value=mock_api_client):
            await review_delete_confirm_callback(update, mock_context)

        assert review["deleted"][0] is False
        assert review["pending_delete"] is None
        update.callback_query.answer.assert_called_once()
        assert update.callback_query.answer.call_args[1].get("show_alert") is True

    async def test_delete_cancel_clears_pending_delete(self, mock_context):
        review = make_review()
        review["pending_delete"] = 0
        update = make_callback_update("rvw_del_cancel:0")
        mock_context.chat_data[REVIEW_STATE_KEY] = {555: review}

        await review_delete_cancel_callback(update, mock_context)

        assert review["pending_delete"] is None
        update.callback_query.edit_message_reply_markup.assert_called_once()
