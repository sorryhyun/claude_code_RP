"""
Unit tests for orchestration context builder.

Tests conversation context building from room messages.
"""

import os
from unittest.mock import Mock, patch

from orchestration.context import build_conversation_context


class TestBuildConversationContext:
    """Tests for build_conversation_context function."""

    @patch("orchestration.context.get_conversation_context_config")
    def test_build_context_with_no_messages(self, mock_get_config):
        """Test building context with no messages."""
        mock_get_config.return_value = {
            "conversation_context": {
                "header": "Conversation:",
                "footer": "",
                "response_instruction_default": "Respond naturally.",
            }
        }

        context = build_conversation_context([])

        assert context == ""

    @patch("orchestration.context.get_conversation_context_config")
    def test_build_context_with_user_messages(self, mock_get_config):
        """Test building context with user messages."""
        mock_get_config.return_value = {
            "conversation_context": {
                "header": "Conversation:",
                "footer": "",
                "response_instruction_default": "Respond naturally.",
            }
        }

        # Create mock messages
        msg1 = Mock(role="user", content="Hello!", participant_type="user", participant_name=None, agent_id=None)

        msg2 = Mock(role="user", content="How are you?", participant_type="user", participant_name=None, agent_id=None)

        with patch.dict(os.environ, {"USER_NAME": "TestUser"}):
            from core import reset_settings

            reset_settings()
            context = build_conversation_context([msg1, msg2])

        assert "Conversation:" in context
        assert "TestUser: Hello!" in context
        assert "TestUser: How are you?" in context
        assert "Respond naturally." in context

    @patch("orchestration.context.get_conversation_context_config")
    def test_build_context_with_agent_messages(self, mock_get_config):
        """Test building context with agent messages."""
        mock_get_config.return_value = {
            "conversation_context": {"header": "Conversation:", "footer": "", "response_instruction_default": ""}
        }

        # Create mock agent with name attribute properly set
        mock_agent = Mock()
        mock_agent.name = "Alice"

        msg = Mock(role="assistant", content="Hi there!", agent_id=1, agent=mock_agent)

        context = build_conversation_context([msg])

        assert "Alice: Hi there!" in context

    @patch("orchestration.context.get_conversation_context_config")
    def test_build_context_skips_skip_messages(self, mock_get_config):
        """Test that skip messages are excluded from context."""
        mock_get_config.return_value = {
            "conversation_context": {"header": "Conversation:", "footer": "", "response_instruction_default": ""}
        }

        # Import SKIP_MESSAGE_TEXT
        from config.constants import SKIP_MESSAGE_TEXT

        msg1 = Mock(role="assistant", content=SKIP_MESSAGE_TEXT, agent_id=1, agent=Mock(name="Alice"))

        msg2 = Mock(role="assistant", content="Real message", agent_id=2, agent=Mock(name="Bob"))

        context = build_conversation_context([msg1, msg2])

        # Should not include skip message
        assert SKIP_MESSAGE_TEXT not in context
        assert "Real message" in context

    @patch("orchestration.context.get_conversation_context_config")
    def test_build_context_with_agent_id_filter(self, mock_get_config):
        """Test building context with agent_id filter (only new messages)."""
        mock_get_config.return_value = {
            "conversation_context": {"header": "Conversation:", "footer": "", "response_instruction_default": ""}
        }

        # Create messages before and after agent's last response
        messages = [
            Mock(role="user", content="Message 1", agent_id=None, participant_type="user"),
            Mock(role="assistant", content="Agent response", agent_id=1, agent=Mock(name="Alice")),
            Mock(role="user", content="Message 2", agent_id=None, participant_type="user"),
            Mock(role="user", content="Message 3", agent_id=None, participant_type="user"),
        ]

        with patch.dict(os.environ, {"USER_NAME": "User"}):
            context = build_conversation_context(messages, agent_id=1)

        # Should only include messages after agent's last response
        assert "Message 1" not in context
        assert "Agent response" not in context
        assert "Message 2" in context
        assert "Message 3" in context

    @patch("orchestration.context.get_conversation_context_config")
    def test_build_context_with_limit(self, mock_get_config):
        """Test building context respects message limit."""
        mock_get_config.return_value = {
            "conversation_context": {"header": "", "footer": "", "response_instruction_default": ""}
        }

        # Create many messages
        messages = [
            Mock(role="user", content=f"Message {i}", agent_id=None, participant_type="user") for i in range(100)
        ]

        context = build_conversation_context(messages, limit=5)

        # Should only include last 5 messages (+ header/footer)
        assert "Message 95" in context
        assert "Message 99" in context
        assert "Message 0" not in context
        assert "Message 90" not in context

    @patch("orchestration.context.get_conversation_context_config")
    def test_build_context_with_character_participant(self, mock_get_config):
        """Test building context with character participant type."""
        mock_get_config.return_value = {
            "conversation_context": {"header": "", "footer": "", "response_instruction_default": ""}
        }

        msg = Mock(
            role="user",
            content="Hello from character!",
            participant_type="character",
            participant_name="Charlie",
            agent_id=None,
        )

        context = build_conversation_context([msg])

        # Should use participant_name as speaker
        assert "Charlie: Hello from character!" in context

    @patch("orchestration.context.get_conversation_context_config")
    def test_build_context_with_situation_builder(self, mock_get_config):
        """Test building context with situation_builder participant."""
        mock_get_config.return_value = {
            "conversation_context": {"header": "", "footer": "", "response_instruction_default": ""}
        }

        msg = Mock(
            role="user",
            content="Scenario description",
            participant_type="situation_builder",
            participant_name=None,
            agent_id=None,
        )

        context = build_conversation_context([msg])

        # Should use "Situation Builder" as speaker
        assert "Situation Builder: Scenario description" in context

    @patch("orchestration.context.get_conversation_context_config")
    @patch("orchestration.context.format_with_particles")
    def test_build_context_one_on_one_with_user_instruction(self, mock_format_particles, mock_get_config):
        """Test 1-on-1 conversation instruction with user."""
        mock_get_config.return_value = {
            "conversation_context": {
                "header": "",
                "footer": "",
                "response_instruction_with_user": "Respond to {user_name}.",
            }
        }
        mock_format_particles.return_value = "Respond to TestUser."

        msg = Mock(role="user", content="Hello", participant_type="user", participant_name=None, agent_id=None)

        context = build_conversation_context([msg], agent_name="Alice", agent_count=1, user_name="TestUser")

        # Should use 1-on-1 instruction template
        mock_format_particles.assert_called_once()
        assert "Respond to TestUser." in context

    @patch("orchestration.context.get_conversation_context_config")
    @patch("orchestration.context.format_with_particles")
    def test_build_context_multi_agent_instruction(self, mock_format_particles, mock_get_config):
        """Test multi-agent conversation instruction."""
        mock_get_config.return_value = {
            "conversation_context": {
                "header": "",
                "footer": "",
                "response_instruction_with_agent": "Respond as {agent_name}.",
            }
        }
        mock_format_particles.return_value = "Respond as Alice."

        msg = Mock(role="user", content="Hello everyone", participant_type="user", participant_name=None, agent_id=None)

        context = build_conversation_context(
            [msg],
            agent_name="Alice",
            agent_count=3,  # Multiple agents
        )

        # Should use multi-agent instruction template
        mock_format_particles.assert_called_once()
        assert "Respond as Alice." in context

    @patch("orchestration.context.get_conversation_context_config")
    def test_build_context_deduplicates_messages(self, mock_get_config):
        """Test that duplicate messages are filtered out."""
        mock_get_config.return_value = {
            "conversation_context": {"header": "", "footer": "", "response_instruction_default": ""}
        }

        # Create duplicate messages
        messages = [
            Mock(role="user", content="Same message", agent_id=None, participant_type="user"),
            Mock(role="user", content="Same message", agent_id=None, participant_type="user"),
            Mock(role="user", content="Different message", agent_id=None, participant_type="user"),
        ]

        with patch.dict(os.environ, {"USER_NAME": "User"}):
            context = build_conversation_context(messages)

        # Should only include "Same message" once
        assert context.count("Same message") == 1
        assert "Different message" in context
