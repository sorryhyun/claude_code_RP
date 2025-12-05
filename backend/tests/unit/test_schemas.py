"""
Unit tests for Pydantic schemas.

Tests schema validation, serialization, and field transformations.
"""

from datetime import datetime, timezone

import pytest
import schemas
from pydantic import ValidationError


class TestAgentSchemas:
    """Tests for Agent-related schemas."""

    @pytest.mark.unit
    def test_agent_base_creation(self):
        """Test creating AgentBase schema."""
        agent_data = {
            "name": "test_agent",
            "group": "test_group",
            "in_a_nutshell": "Test agent",
            "characteristics": "Helpful",
            "is_critic": False,
        }
        agent = schemas.AgentBase(**agent_data)

        assert agent.name == "test_agent"
        assert agent.group == "test_group"
        assert agent.is_critic is False

    @pytest.mark.unit
    def test_agent_base_defaults(self):
        """Test AgentBase default values."""
        agent = schemas.AgentBase(name="minimal_agent")

        assert agent.name == "minimal_agent"
        assert agent.group is None
        assert agent.is_critic is False

    @pytest.mark.unit
    def test_agent_create_schema(self):
        """Test AgentCreate schema."""
        agent_data = {"name": "new_agent", "config_file": "agents/new_agent.md"}
        agent = schemas.AgentCreate(**agent_data)

        assert agent.name == "new_agent"
        assert agent.config_file == "agents/new_agent.md"

    @pytest.mark.unit
    def test_agent_update_schema(self):
        """Test AgentUpdate schema."""
        update_data = {"in_a_nutshell": "Updated nutshell", "recent_events": "New events"}
        agent_update = schemas.AgentUpdate(**update_data)

        assert agent_update.in_a_nutshell == "Updated nutshell"
        assert agent_update.recent_events == "New events"
        assert agent_update.characteristics is None  # Not provided

    @pytest.mark.unit
    async def test_agent_schema_serialization(self, sample_agent):
        """Test Agent schema from database model."""
        agent_schema = schemas.Agent.model_validate(sample_agent)

        assert agent_schema.id == sample_agent.id
        assert agent_schema.name == sample_agent.name
        assert agent_schema.system_prompt == sample_agent.system_prompt
        assert agent_schema.is_critic is False  # Converted from int


class TestRoomSchemas:
    """Tests for Room-related schemas."""

    @pytest.mark.unit
    def test_room_base_creation(self):
        """Test creating RoomBase schema."""
        room = schemas.RoomBase(name="test_room")
        assert room.name == "test_room"

    @pytest.mark.unit
    def test_room_base_validation(self):
        """Test RoomBase validation."""
        with pytest.raises(ValidationError):
            schemas.RoomBase()  # name is required

    @pytest.mark.unit
    def test_room_create_schema(self):
        """Test RoomCreate schema."""
        room_data = {"name": "new_room", "max_interactions": 10}
        room = schemas.RoomCreate(**room_data)

        assert room.name == "new_room"
        assert room.max_interactions == 10

    @pytest.mark.unit
    def test_room_create_defaults(self):
        """Test RoomCreate default values."""
        room = schemas.RoomCreate(name="minimal_room")

        assert room.name == "minimal_room"
        assert room.max_interactions is None

    @pytest.mark.unit
    def test_room_update_schema(self):
        """Test RoomUpdate schema."""
        update_data = {"max_interactions": 20, "is_paused": True}
        room_update = schemas.RoomUpdate(**update_data)

        assert room_update.max_interactions == 20
        assert room_update.is_paused is True

    @pytest.mark.unit
    async def test_room_schema_serialization(self, sample_room, test_db):
        """Test Room schema from database model."""
        # Refresh to load relationships
        await test_db.refresh(sample_room, ["agents", "messages"])

        room_schema = schemas.Room.model_validate(sample_room)

        assert room_schema.id == sample_room.id
        assert room_schema.name == sample_room.name
        assert room_schema.is_paused is False  # Converted from int

    @pytest.mark.unit
    async def test_room_summary_schema(self, sample_room):
        """Test RoomSummary schema."""
        summary = schemas.RoomSummary.model_validate(sample_room)

        assert summary.id == sample_room.id
        assert summary.name == sample_room.name
        # RoomSummary doesn't include agents or messages
        assert not hasattr(summary, "agents")
        assert not hasattr(summary, "messages")


class TestMessageSchemas:
    """Tests for Message-related schemas."""

    @pytest.mark.unit
    def test_message_base_creation(self):
        """Test creating MessageBase schema."""
        message = schemas.MessageBase(content="Test message", role="user", participant_type="user")

        assert message.content == "Test message"
        assert message.role == "user"
        assert message.participant_type == "user"

    @pytest.mark.unit
    def test_message_base_defaults(self):
        """Test MessageBase default values."""
        message = schemas.MessageBase(content="Test", role="assistant")

        assert message.content == "Test"
        assert message.role == "assistant"
        assert message.participant_type is None

    @pytest.mark.unit
    def test_message_create_schema(self):
        """Test MessageCreate schema."""
        message_data = {"content": "Hello!", "role": "assistant", "agent_id": 1, "thinking": "Thinking about response"}
        message = schemas.MessageCreate(**message_data)

        assert message.content == "Hello!"
        assert message.agent_id == 1
        assert message.thinking == "Thinking about response"

    @pytest.mark.unit
    async def test_message_schema_with_agent(self, sample_message, test_db):
        """Test Message schema includes agent info."""
        # Refresh with agent relationship
        await test_db.refresh(sample_message, ["agent"])

        message_schema = schemas.Message.model_validate(sample_message)

        assert message_schema.id == sample_message.id
        assert message_schema.content == sample_message.content
        assert message_schema.agent_name == sample_message.agent.name
        assert message_schema.agent_profile_pic == sample_message.agent.profile_pic

    @pytest.mark.unit
    def test_message_user_types(self):
        """Test different participant types."""
        # User message
        user_msg = schemas.MessageBase(content="User says", role="user", participant_type="user")
        assert user_msg.participant_type == "user"

        # Situation builder message
        situation_msg = schemas.MessageBase(
            content="Situation context", role="user", participant_type="situation_builder"
        )
        assert situation_msg.participant_type == "situation_builder"

        # Character message
        char_msg = schemas.MessageBase(
            content="Character says", role="user", participant_type="character", participant_name="Custom Character"
        )
        assert char_msg.participant_type == "character"
        assert char_msg.participant_name == "Custom Character"


class TestSchemaDatetimeSerialization:
    """Tests for datetime field serialization."""

    @pytest.mark.unit
    async def test_agent_datetime_serialization(self, sample_agent):
        """Test Agent created_at serialization."""
        agent_schema = schemas.Agent.model_validate(sample_agent)

        # Check that created_at exists and is a datetime
        created_at = agent_schema.created_at
        assert created_at is not None
        assert isinstance(created_at, datetime)

    @pytest.mark.unit
    async def test_room_datetime_serialization(self, sample_room, test_db):
        """Test Room created_at serialization."""
        # Refresh to load relationships
        await test_db.refresh(sample_room, ["agents", "messages"])

        room_schema = schemas.Room.model_validate(sample_room)

        # Check that created_at exists and is a datetime
        created_at = room_schema.created_at
        assert created_at is not None
        assert isinstance(created_at, datetime)

    @pytest.mark.unit
    async def test_message_datetime_serialization(self, sample_message, test_db):
        """Test Message timestamp serialization."""
        await test_db.refresh(sample_message, ["agent"])
        message_schema = schemas.Message.model_validate(sample_message)

        # Check that timestamp exists and is a datetime
        timestamp = message_schema.timestamp
        assert timestamp is not None
        assert isinstance(timestamp, datetime)


class TestSchemaBooleanSerialization:
    """Tests for boolean field serialization."""

    @pytest.mark.unit
    async def test_agent_is_critic_serialization(self, test_db):
        """Test Agent is_critic field serialization."""
        # Create critic agent (is_critic=True)
        agent = schemas.Agent.model_validate(
            type(
                "Agent",
                (),
                {
                    "id": 1,
                    "name": "test",
                    "system_prompt": "test",
                    "created_at": datetime.now(timezone.utc),
                    "is_critic": True,  # Native boolean
                    "group": None,
                    "config_file": None,
                    "profile_pic": None,
                    "in_a_nutshell": None,
                    "characteristics": None,
                    "recent_events": None,
                },
            )()
        )

        # Should be boolean
        assert agent.is_critic is True
        assert isinstance(agent.is_critic, bool)

    @pytest.mark.unit
    async def test_room_is_paused_serialization(self, test_db):
        """Test Room is_paused field serialization."""
        # Create paused room (is_paused=True)
        room = schemas.Room.model_validate(
            type(
                "Room",
                (),
                {
                    "id": 1,
                    "name": "test",
                    "max_interactions": None,
                    "is_paused": True,  # Native boolean
                    "created_at": datetime.now(timezone.utc),
                    "agents": [],
                    "messages": [],
                },
            )()
        )

        # Should be boolean
        assert room.is_paused is True
        assert isinstance(room.is_paused, bool)
