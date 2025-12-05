"""
Pytest configuration and shared fixtures for backend tests.

This module provides test fixtures for database sessions, test clients,
authentication, and commonly used test data.
"""

import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import models
from database import Base, get_db
from main import app


# Configure pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh test database for each test function.

    Uses PostgreSQL test database that is created and destroyed for each test.
    Requires TEST_DATABASE_URL or DATABASE_URL environment variable.
    """
    import os

    # Get test database URL from environment
    test_db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not test_db_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL not set - skipping database tests")

    # Create test engine
    test_engine = create_async_engine(test_db_url, echo=False)

    try:
        # Create tables
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create session
        TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        async with TestingSessionLocal() as session:
            yield session

        # Drop tables after test
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception as e:
        pytest.skip(f"PostgreSQL connection failed: {e}")
    finally:
        await test_engine.dispose()


@pytest.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test client with authentication bypassed.

    This fixture overrides the database dependency to use the test database
    and removes authentication middleware for easier testing.
    """
    from unittest.mock import AsyncMock, Mock

    # Override the get_db dependency to use test database
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    # Mock agent_manager and chat_orchestrator on app state
    mock_agent_manager = Mock()
    # Configure client_pool mock to return empty lists/dicts and async methods
    mock_agent_manager.client_pool.get_keys_for_agent.return_value = []
    mock_agent_manager.client_pool.cleanup = AsyncMock()
    mock_agent_manager.cleanup_agent.return_value = None
    app.state.agent_manager = mock_agent_manager

    mock_chat_orchestrator = Mock()
    mock_chat_orchestrator.generate_agent_response.return_value = None
    app.state.chat_orchestrator = mock_chat_orchestrator

    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up
    app.dependency_overrides.clear()
    if hasattr(app.state, "agent_manager"):
        delattr(app.state, "agent_manager")
    if hasattr(app.state, "chat_orchestrator"):
        delattr(app.state, "chat_orchestrator")


@pytest.fixture(scope="function")
async def authenticated_client(test_db: AsyncSession, mock_env_vars) -> AsyncGenerator[tuple[AsyncClient, str], None]:
    """
    Create a test client with a valid JWT token.

    Returns:
        tuple: (AsyncClient, token) - The test client and the JWT token
    """
    from unittest.mock import AsyncMock, Mock

    from auth import generate_jwt_token

    # Override the get_db dependency to use test database
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    # Mock agent_manager and chat_orchestrator on app state
    mock_agent_manager = Mock()
    # Configure client_pool mock to return empty lists/dicts and async methods
    mock_agent_manager.client_pool.get_keys_for_agent.return_value = []
    mock_agent_manager.client_pool.cleanup = AsyncMock()
    mock_agent_manager.cleanup_agent.return_value = None
    app.state.agent_manager = mock_agent_manager

    mock_chat_orchestrator = Mock()
    mock_chat_orchestrator.generate_agent_response.return_value = None
    app.state.chat_orchestrator = mock_chat_orchestrator

    # Generate a valid JWT token
    token = generate_jwt_token(role="admin", user_id="admin")

    # Create test client with auth header
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers={"X-API-Key": token}) as ac:
        yield ac, token

    # Clean up
    app.dependency_overrides.clear()
    if hasattr(app.state, "agent_manager"):
        delattr(app.state, "agent_manager")
    if hasattr(app.state, "chat_orchestrator"):
        delattr(app.state, "chat_orchestrator")


@pytest.fixture(scope="function")
async def guest_client(test_db: AsyncSession, mock_env_vars) -> AsyncGenerator[tuple[AsyncClient, str], None]:
    """
    Create a test client with a valid guest JWT token.

    Returns:
        tuple: (AsyncClient, token) - The test client and the JWT token
    """
    from unittest.mock import AsyncMock, Mock

    from auth import generate_jwt_token

    # Override the get_db dependency to use test database
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    # Mock agent_manager and chat_orchestrator on app state
    mock_agent_manager = Mock()
    # Configure client_pool mock to return empty lists/dicts and async methods
    mock_agent_manager.client_pool.get_keys_for_agent.return_value = []
    mock_agent_manager.client_pool.cleanup = AsyncMock()
    mock_agent_manager.cleanup_agent.return_value = None
    app.state.agent_manager = mock_agent_manager

    mock_chat_orchestrator = Mock()
    mock_chat_orchestrator.generate_agent_response.return_value = None
    app.state.chat_orchestrator = mock_chat_orchestrator

    # Generate a valid JWT token with guest role
    token = generate_jwt_token(role="guest", user_id="guest-test")

    # Create test client with auth header
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers={"X-API-Key": token}) as ac:
        yield ac, token

    # Clean up
    app.dependency_overrides.clear()
    if hasattr(app.state, "agent_manager"):
        delattr(app.state, "agent_manager")
    if hasattr(app.state, "chat_orchestrator"):
        delattr(app.state, "chat_orchestrator")


@pytest.fixture
async def sample_agent(test_db: AsyncSession) -> models.Agent:
    """Create a sample agent for testing."""
    agent = models.Agent(
        name="test_agent",
        group="test_group",
        config_file="agents/test_agent.md",
        in_a_nutshell="A test agent for testing purposes",
        characteristics="Friendly and helpful",
        recent_events="Just created",
        system_prompt="You are a test agent.",
        is_critic=False,
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)
    return agent


@pytest.fixture
async def sample_room(test_db: AsyncSession) -> models.Room:
    """Create a sample room for testing."""
    room = models.Room(name="test_room", max_interactions=None, is_paused=False, owner_id="admin")
    test_db.add(room)
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def sample_guest_room(test_db: AsyncSession) -> models.Room:
    """Create a sample room owned by the guest for testing."""
    room = models.Room(name="guest_test_room", max_interactions=None, is_paused=False, owner_id="guest-test")
    test_db.add(room)
    await test_db.commit()
    await test_db.refresh(room)
    return room


@pytest.fixture
async def sample_room_with_agents(
    test_db: AsyncSession, sample_room: models.Room, sample_agent: models.Agent
) -> models.Room:
    """Create a sample room with agents."""
    # Refresh to ensure we have the agents relationship loaded
    await test_db.refresh(sample_room, ["agents"])
    sample_room.agents.append(sample_agent)
    await test_db.commit()
    await test_db.refresh(sample_room, ["agents"])
    return sample_room


@pytest.fixture
async def sample_message(test_db: AsyncSession, sample_room: models.Room, sample_agent: models.Agent) -> models.Message:
    """Create a sample message for testing."""
    message = models.Message(
        room_id=sample_room.id,
        agent_id=sample_agent.id,
        content="This is a test message",
        role="assistant",
        thinking="Test thinking process",
    )
    test_db.add(message)
    await test_db.commit()
    await test_db.refresh(message)
    return message


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    from core import reset_settings

    # Mock API key hash (bcrypt hash of "test_password")
    test_hash = "$2b$12$H0fCIM9buSuQsCFErTRi0Omz//QVZxCKJW5Dapi2u3ealuUFzvF9O"
    monkeypatch.setenv("API_KEY_HASH", test_hash)

    # Mock JWT secret
    monkeypatch.setenv("JWT_SECRET", "test_secret_key_for_testing_only")

    # Disable guest login for most tests
    monkeypatch.setenv("ENABLE_GUEST_LOGIN", "false")

    # Reset settings cache so new env vars are picked up
    reset_settings()

    return {
        "api_key_hash": test_hash,
        "jwt_secret": "test_secret_key_for_testing_only",
        "test_password": "test_password",
    }


@pytest.fixture
def temp_agent_config(tmp_path):
    """Create a temporary agent configuration directory."""
    agent_dir = tmp_path / "agents" / "test_agent"
    agent_dir.mkdir(parents=True)

    # Create config files
    (agent_dir / "in_a_nutshell.md").write_text("Test agent nutshell")
    (agent_dir / "characteristics.md").write_text("Test characteristics")
    (agent_dir / "recent_events.md").write_text("Test recent events")

    return agent_dir
