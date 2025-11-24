"""
Unit tests for orchestration message handlers.

Tests broadcasting and message saving functionality.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from domain.contexts import AgentMessageData, MessageContext
from orchestration.handlers import (
    broadcast_stream_delta,
    broadcast_stream_end,
    broadcast_stream_start,
    broadcast_typing_indicator,
    save_and_broadcast_agent_message,
)


class TestBroadcastTypingIndicator:
    """Tests for broadcast_typing_indicator function."""

    @pytest.mark.asyncio
    async def test_broadcast_typing_with_manager(self):
        """Test broadcasting typing indicator (no-op for polling architecture)."""
        mock_agent = Mock(id=1, name="Alice", profile_pic="pic.jpg")

        context = MessageContext(
            db=Mock(),
            room_id=1,
            agent=mock_agent,
        )

        # Should complete without error (no-op)
        await broadcast_typing_indicator(context)

    @pytest.mark.asyncio
    async def test_broadcast_typing_without_manager(self):
        """Test that broadcasting is skipped when no manager."""
        mock_agent = Mock(id=1, name="Alice")

        context = MessageContext(
            db=Mock(),
            room_id=1,
            agent=mock_agent,
        )

        # Should not raise error
        await broadcast_typing_indicator(context)


class TestSaveAndBroadcastAgentMessage:
    """Tests for save_and_broadcast_agent_message function."""

    @pytest.mark.asyncio
    async def test_save_and_broadcast_message(self):
        """Test saving agent message (polling architecture - no broadcast)."""
        mock_db = AsyncMock()
        mock_agent = Mock(id=1, name="Alice", profile_pic="pic.jpg")

        # Mock saved message
        saved_message = Mock(id=123, content="Hello world", role="assistant", timestamp=datetime.utcnow())

        with patch("orchestration.handlers.crud.create_message", return_value=saved_message) as mock_create:
            context = MessageContext(
                db=mock_db,
                room_id=1,
                agent=mock_agent,
            )

            message_data = AgentMessageData(content="Hello world", thinking="Thinking process")

            await save_and_broadcast_agent_message(context, message_data)

            # Should save message to database
            mock_create.assert_awaited_once()
            create_call_args = mock_create.call_args[0]
            assert create_call_args[1] == 1  # room_id

            # Verify message content
            message_arg = mock_create.call_args[0][2]
            assert message_arg.content == "Hello world"
            assert message_arg.thinking == "Thinking process"

    @pytest.mark.asyncio
    async def test_save_message_without_broadcast(self):
        """Test saving message without broadcasting (for critics)."""
        mock_db = AsyncMock()
        mock_agent = Mock(id=1, name="Alice")

        saved_message = Mock(id=123, content="Hello", timestamp=datetime.utcnow())

        with patch("orchestration.handlers.crud.create_message", return_value=saved_message):
            context = MessageContext(
                db=mock_db,
                room_id=1,
                agent=mock_agent,
            )

            message_data = AgentMessageData(content="Hello")

            await save_and_broadcast_agent_message(context, message_data, broadcast=False)

            # Message should be saved but not broadcast (since no manager)
            # This should not raise any errors


class TestBroadcastStreamStart:
    """Tests for broadcast_stream_start function."""

    @pytest.mark.asyncio
    async def test_broadcast_stream_start_with_manager(self):
        """Test broadcasting stream start event (no-op for polling architecture)."""
        mock_agent = Mock(id=1, name="Alice", profile_pic="pic.jpg")

        context = MessageContext(
            db=Mock(),
            room_id=1,
            agent=mock_agent,
        )

        # Should complete without error (no-op)
        await broadcast_stream_start(context, "temp_123")

    @pytest.mark.asyncio
    async def test_broadcast_stream_start_without_manager(self):
        """Test stream start without manager."""
        mock_agent = Mock(id=1, name="Alice")

        context = MessageContext(
            db=Mock(),
            room_id=1,
            agent=mock_agent,
        )

        # Should not raise error
        await broadcast_stream_start(context, "temp_123")


class TestBroadcastStreamDelta:
    """Tests for broadcast_stream_delta function."""

    @pytest.mark.asyncio
    async def test_broadcast_content_delta(self):
        """Test broadcasting content delta (no-op for polling architecture)."""
        mock_agent = Mock(id=1)

        context = MessageContext(
            db=Mock(),
            room_id=1,
            agent=mock_agent,
        )

        # Should complete without error (no-op)
        await broadcast_stream_delta(context, "temp_123", content_delta="Hello ")

    @pytest.mark.asyncio
    async def test_broadcast_thinking_delta(self):
        """Test broadcasting thinking delta (no-op for polling architecture)."""
        mock_agent = Mock(id=1)

        context = MessageContext(
            db=Mock(),
            room_id=1,
            agent=mock_agent,
        )

        # Should complete without error (no-op)
        await broadcast_stream_delta(context, "temp_123", thinking_delta="Thinking...")

    @pytest.mark.asyncio
    async def test_broadcast_both_deltas(self):
        """Test broadcasting both content and thinking deltas (no-op for polling architecture)."""
        mock_agent = Mock(id=1)

        context = MessageContext(
            db=Mock(),
            room_id=1,
            agent=mock_agent,
        )

        # Should complete without error (no-op)
        await broadcast_stream_delta(context, "temp_123", content_delta="Hello", thinking_delta="Processing")


class TestBroadcastStreamEnd:
    """Tests for broadcast_stream_end function."""

    @pytest.mark.asyncio
    async def test_broadcast_stream_end_with_broadcast(self):
        """Test saving stream end message (polling architecture - no broadcast)."""
        mock_db = AsyncMock()
        mock_agent = Mock(id=1, name="Alice", profile_pic="pic.jpg")

        saved_message = Mock(id=123, content="Complete message", timestamp=datetime.utcnow())

        with patch("orchestration.handlers.crud.create_message", return_value=saved_message) as mock_create:
            context = MessageContext(
                db=mock_db,
                room_id=1,
                agent=mock_agent,
            )

            message_data = AgentMessageData(content="Complete message", thinking="Final thoughts")

            msg_id = await broadcast_stream_end(context, "temp_123", message_data, broadcast=True)

            # Should save message
            mock_create.assert_awaited_once()

            # Verify message content
            message_arg = mock_create.call_args[0][2]
            assert message_arg.content == "Complete message"
            assert message_arg.thinking == "Final thoughts"

            # Should return message ID
            assert msg_id == 123

    @pytest.mark.asyncio
    async def test_broadcast_stream_end_without_broadcast(self):
        """Test saving stream end without broadcasting (for critics)."""
        mock_db = AsyncMock()
        mock_agent = Mock(id=1, name="Alice")

        saved_message = Mock(id=123, timestamp=datetime.utcnow())

        with patch("orchestration.handlers.crud.create_message", return_value=saved_message):
            context = MessageContext(
                db=mock_db,
                room_id=1,
                agent=mock_agent,
            )

            message_data = AgentMessageData(content="Complete message")

            msg_id = await broadcast_stream_end(context, "temp_123", message_data, broadcast=False)

            # Should save message but not broadcast
            assert msg_id == 123

    @pytest.mark.asyncio
    async def test_broadcast_stream_end_with_no_thinking(self):
        """Test stream end with no thinking text (polling architecture)."""
        mock_db = AsyncMock()
        mock_agent = Mock(id=1, name="Alice", profile_pic="pic.jpg")

        saved_message = Mock(id=123, content="Message", timestamp=datetime.utcnow())

        with patch("orchestration.handlers.crud.create_message", return_value=saved_message) as mock_create:
            context = MessageContext(
                db=mock_db,
                room_id=1,
                agent=mock_agent,
            )

            message_data = AgentMessageData(content="Message")  # No thinking

            await broadcast_stream_end(context, "temp_123", message_data)

            # Thinking should be None in saved message
            message_arg = mock_create.call_args[0][2]
            assert message_arg.thinking is None
