from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, field_serializer, model_validator
from utils.serializers import serialize_sqlite_bool as _serialize_sqlite_bool
from utils.serializers import serialize_utc_datetime as _serialize_utc_datetime


class AgentBase(BaseModel):
    name: str
    group: Optional[str] = None
    config_file: Optional[str] = None
    profile_pic: Optional[str] = None
    in_a_nutshell: Optional[str] = None
    characteristics: Optional[str] = None
    recent_events: Optional[str] = None
    is_critic: bool = False


class AgentCreate(AgentBase):
    """
    Create an agent with either:
    1. config_file: Load in_a_nutshell/characteristics/recent_events from file
    2. in_a_nutshell/characteristics/recent_events: Provide directly
    The system_prompt will be built automatically.
    """

    pass


class AgentUpdate(BaseModel):
    """Update agent's runtime fields: nutshell, characteristics, or recent events."""

    profile_pic: Optional[str] = None
    in_a_nutshell: Optional[str] = None
    characteristics: Optional[str] = None
    recent_events: Optional[str] = None


class Agent(AgentBase):
    id: int
    system_prompt: str  # The built system prompt
    session_id: Optional[str] = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info):
        return _serialize_utc_datetime(dt)

    @field_serializer("is_critic")
    def serialize_is_critic(self, value: int, _info):
        return _serialize_sqlite_bool(value)

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    content: str
    role: str
    participant_type: Optional[str] = None  # 'user', 'situation_builder', 'character', or None for agents
    participant_name: Optional[str] = None  # Custom name for 'character' mode


class MessageCreate(MessageBase):
    agent_id: Optional[int] = None
    thinking: Optional[str] = None


class Message(MessageBase):
    id: int
    room_id: int
    agent_id: Optional[int]
    thinking: Optional[str] = None
    timestamp: datetime
    agent_name: Optional[str] = None
    agent_profile_pic: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_agent_fields(cls, data: Any) -> Any:
        """Populate agent_name and agent_profile_pic from the agent relationship."""
        # If data is a model instance (has __dict__), extract agent info
        if hasattr(data, "__dict__"):
            # Get the agent relationship if it exists
            agent = getattr(data, "agent", None)
            if agent:
                # Create a dict from the model and add agent fields
                data_dict = {
                    "id": data.id,
                    "room_id": data.room_id,
                    "agent_id": data.agent_id,
                    "content": data.content,
                    "role": data.role,
                    "participant_type": data.participant_type,
                    "participant_name": data.participant_name,
                    "thinking": data.thinking,
                    "timestamp": data.timestamp,
                    "agent_name": agent.name,
                    "agent_profile_pic": agent.profile_pic,
                }
                return data_dict
        return data

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime, _info):
        return _serialize_utc_datetime(dt)

    class Config:
        from_attributes = True


class RoomBase(BaseModel):
    name: str


class RoomCreate(RoomBase):
    max_interactions: Optional[int] = None


class RoomUpdate(BaseModel):
    max_interactions: Optional[int] = None
    is_paused: Optional[bool] = None


class Room(RoomBase):
    id: int
    owner_id: Optional[str] = None
    max_interactions: Optional[int] = None
    is_paused: bool = False
    created_at: datetime
    last_activity_at: Optional[datetime] = None
    last_read_at: Optional[datetime] = None
    agents: List[Agent] = []
    messages: List[Message] = []

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info):
        return _serialize_utc_datetime(dt)

    @field_serializer("last_activity_at")
    def serialize_last_activity_at(self, dt: Optional[datetime], _info):
        return _serialize_utc_datetime(dt) if dt else None

    @field_serializer("last_read_at")
    def serialize_last_read_at(self, dt: Optional[datetime], _info):
        return _serialize_utc_datetime(dt) if dt else None

    @field_serializer("is_paused")
    def serialize_is_paused(self, value: int, _info):
        return _serialize_sqlite_bool(value)

    class Config:
        from_attributes = True


class RoomSummary(RoomBase):
    id: int
    owner_id: Optional[str] = None
    max_interactions: Optional[int] = None
    is_paused: bool = False
    created_at: datetime
    last_activity_at: Optional[datetime] = None
    last_read_at: Optional[datetime] = None
    has_unread: bool = False

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info):
        return _serialize_utc_datetime(dt)

    @field_serializer("last_activity_at")
    def serialize_last_activity_at(self, dt: Optional[datetime], _info):
        return _serialize_utc_datetime(dt) if dt else None

    @field_serializer("last_read_at")
    def serialize_last_read_at(self, dt: Optional[datetime], _info):
        return _serialize_utc_datetime(dt) if dt else None

    @field_serializer("is_paused")
    def serialize_is_paused(self, value: int, _info):
        return _serialize_sqlite_bool(value)

    class Config:
        from_attributes = True
