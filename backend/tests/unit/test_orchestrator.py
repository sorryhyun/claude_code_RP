"""
Unit tests for ChatOrchestrator.

Tests multi-agent conversation orchestration logic.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from domain.task_identifier import TaskIdentifier
from orchestration.orchestrator import MAX_FOLLOW_UP_ROUNDS, MAX_TOTAL_MESSAGES, ChatOrchestrator


class TestChatOrchestratorInit:
    """Tests for ChatOrchestrator initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        orchestrator = ChatOrchestrator()

        assert orchestrator.max_follow_up_rounds == MAX_FOLLOW_UP_ROUNDS
        assert orchestrator.max_total_messages == MAX_TOTAL_MESSAGES
        assert orchestrator.active_room_tasks == {}
        assert orchestrator.last_user_message_time == {}
        assert orchestrator.response_generator is not None

    def test_init_with_custom_limits(self):
        """Test initialization with custom limits."""
        orchestrator = ChatOrchestrator(max_follow_up_rounds=3, max_total_messages=20)

        assert orchestrator.max_follow_up_rounds == 3
        assert orchestrator.max_total_messages == 20


class TestGetChattingAgents:
    """Tests for get_chatting_agents method."""

    def test_get_chatting_agents_with_active_clients(self):
        """Test retrieving list of chatting agents."""
        orchestrator = ChatOrchestrator()
        mock_manager = Mock()
        mock_manager.active_clients = {
            TaskIdentifier(room_id=1, agent_id=10): Mock(),
            TaskIdentifier(room_id=1, agent_id=20): Mock(),
            TaskIdentifier(room_id=2, agent_id=30): Mock(),
        }

        chatting_agents = orchestrator.get_chatting_agents(1, mock_manager)

        # Should return agents for room 1 only
        assert sorted(chatting_agents) == [10, 20]

    def test_get_chatting_agents_with_no_active_clients(self):
        """Test with no active clients."""
        orchestrator = ChatOrchestrator()
        mock_manager = Mock()
        mock_manager.active_clients = {}

        chatting_agents = orchestrator.get_chatting_agents(1, mock_manager)

        assert chatting_agents == []

    def test_get_chatting_agents_filters_by_room(self):
        """Test that only agents from the specified room are returned."""
        orchestrator = ChatOrchestrator()
        mock_manager = Mock()
        mock_manager.active_clients = {
            TaskIdentifier(room_id=1, agent_id=10): Mock(),
            TaskIdentifier(room_id=2, agent_id=20): Mock(),
            TaskIdentifier(room_id=3, agent_id=30): Mock(),
        }

        chatting_agents = orchestrator.get_chatting_agents(1, mock_manager)

        # Should only include agents from room 1
        assert chatting_agents == [10]


class TestInterruptRoomProcessing:
    """Tests for interrupt_room_processing method."""

    @pytest.mark.asyncio
    async def test_interrupt_room_with_active_task(self):
        """Test interrupting a room with an active task."""
        orchestrator = ChatOrchestrator()
        mock_manager = AsyncMock()

        # Create a real asyncio.Task that we can cancel
        async def long_running_task():
            # Simulate a long-running task that waits indefinitely
            await asyncio.sleep(100)

        mock_task = asyncio.create_task(long_running_task())
        orchestrator.active_room_tasks[1] = mock_task

        await orchestrator.interrupt_room_processing(1, mock_manager)

        # Task should be cancelled
        assert mock_task.cancelled()

        # Should interrupt agents via manager
        mock_manager.interrupt_room.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_interrupt_room_with_no_active_task(self):
        """Test interrupting a room with no active task."""
        orchestrator = ChatOrchestrator()
        mock_manager = AsyncMock()

        await orchestrator.interrupt_room_processing(1, mock_manager)

        # Should still call interrupt_room on manager
        mock_manager.interrupt_room.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_interrupt_room_with_completed_task(self):
        """Test interrupting a room where task is already done."""
        orchestrator = ChatOrchestrator()
        mock_manager = AsyncMock()

        # Create a completed task
        mock_task = AsyncMock()
        mock_task.done.return_value = True
        orchestrator.active_room_tasks[1] = mock_task

        await orchestrator.interrupt_room_processing(1, mock_manager)

        # Should not try to cancel completed task
        mock_task.cancel.assert_not_called()


class TestCleanupRoomState:
    """Tests for cleanup_room_state method."""

    @pytest.mark.asyncio
    async def test_cleanup_room_state_complete(self):
        """Test complete room state cleanup."""
        orchestrator = ChatOrchestrator()
        mock_manager = AsyncMock()

        # Setup room state
        orchestrator.active_room_tasks[1] = AsyncMock()
        orchestrator.last_user_message_time[1] = 123.456

        with patch.object(orchestrator, "interrupt_room_processing", new=AsyncMock()) as mock_interrupt:
            await orchestrator.cleanup_room_state(1, mock_manager)

            # Should interrupt processing
            mock_interrupt.assert_awaited_once_with(1, mock_manager)

        # Should remove from tracking dicts
        assert 1 not in orchestrator.active_room_tasks
        assert 1 not in orchestrator.last_user_message_time

    @pytest.mark.asyncio
    async def test_cleanup_room_state_partial(self):
        """Test cleanup when only some state exists."""
        orchestrator = ChatOrchestrator()
        mock_manager = AsyncMock()

        # Only last_user_message_time exists
        orchestrator.last_user_message_time[1] = 123.456

        with patch.object(orchestrator, "interrupt_room_processing", new=AsyncMock()):
            await orchestrator.cleanup_room_state(1, mock_manager)

        # Should not raise errors
        assert 1 not in orchestrator.last_user_message_time


class TestCountAgentMessages:
    """Tests for _count_agent_messages method."""

    @pytest.mark.asyncio
    async def test_count_agent_messages(self):
        """Test counting agent messages in a room."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()

        # Mock database response
        mock_result = Mock()
        mock_result.scalar.return_value = 15
        mock_db.execute.return_value = mock_result

        count = await orchestrator._count_agent_messages(mock_db, 1)

        assert count == 15

    @pytest.mark.asyncio
    async def test_count_agent_messages_returns_zero_when_none(self):
        """Test that None result returns 0."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        count = await orchestrator._count_agent_messages(mock_db, 1)

        assert count == 0


class TestHandleUserMessage:
    """Tests for handle_user_message method."""

    @pytest.mark.asyncio
    async def test_handle_user_message_saves_message(self):
        """Test that user message is saved to database."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_manager = None  # No broadcasting
        mock_agent_manager = AsyncMock()

        message_data = {"content": "Hello agents!", "participant_type": "user", "participant_name": None}

        # Mock saved message
        saved_message = Mock(id=1, content="Hello agents!", role="user", timestamp=Mock())

        with (
            patch("orchestration.orchestrator.crud.create_message", return_value=saved_message) as mock_create,
            patch("orchestration.orchestrator.crud.get_agents", return_value=[]) as mock_get_agents,
            patch.object(orchestrator, "interrupt_room_processing", new=AsyncMock()),
        ):
            await orchestrator.handle_user_message(
                db=mock_db,
                room_id=1,
                message_data=message_data,
                _manager=mock_manager,
                agent_manager=mock_agent_manager,
            )

            # Should save message
            mock_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_user_message_uses_saved_message_id(self):
        """Test using pre-saved message ID."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_manager = None
        mock_agent_manager = AsyncMock()

        # Mock database get
        saved_message = Mock(id=123, content="Hello", role="user")
        mock_db.get.return_value = saved_message

        message_data = {"content": "Hello"}

        with (
            patch("orchestration.orchestrator.crud.create_message") as mock_create,
            patch("orchestration.orchestrator.crud.get_agents", return_value=[]),
            patch.object(orchestrator, "interrupt_room_processing", new=AsyncMock()),
        ):
            await orchestrator.handle_user_message(
                db=mock_db,
                room_id=1,
                message_data=message_data,
                _manager=mock_manager,
                agent_manager=mock_agent_manager,
                saved_user_message_id=123,
            )

            # Should NOT create new message
            mock_create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_user_message_interrupts_previous_processing(self):
        """Test that previous processing is interrupted."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_manager = None
        mock_agent_manager = AsyncMock()

        message_data = {"content": "New message"}
        saved_message = Mock(id=1, content="New message", role="user", timestamp=Mock())

        with (
            patch("orchestration.orchestrator.crud.create_message", return_value=saved_message),
            patch("orchestration.orchestrator.crud.get_agents", return_value=[]),
            patch.object(orchestrator, "interrupt_room_processing", new=AsyncMock()) as mock_interrupt,
        ):
            await orchestrator.handle_user_message(
                db=mock_db,
                room_id=1,
                message_data=message_data,
                _manager=mock_manager,
                agent_manager=mock_agent_manager,
            )

            # Should interrupt existing processing
            mock_interrupt.assert_awaited_once_with(1, mock_agent_manager)

    @pytest.mark.asyncio
    async def test_handle_user_message_records_timestamp(self):
        """Test that user message timestamp is recorded."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_manager = None
        mock_agent_manager = AsyncMock()

        message_data = {"content": "Hello"}
        saved_message = Mock(id=1, content="Hello", role="user", timestamp=Mock())

        with (
            patch("orchestration.orchestrator.crud.create_message", return_value=saved_message),
            patch("orchestration.orchestrator.crud.get_agents", return_value=[]),
            patch.object(orchestrator, "interrupt_room_processing", new=AsyncMock()),
        ):
            await orchestrator.handle_user_message(
                db=mock_db,
                room_id=1,
                message_data=message_data,
                _manager=mock_manager,
                agent_manager=mock_agent_manager,
            )

            # Should record timestamp
            assert 1 in orchestrator.last_user_message_time
            assert isinstance(orchestrator.last_user_message_time[1], float)


class TestProcessAgentResponses:
    """Tests for _process_agent_responses method."""

    @pytest.mark.asyncio
    async def test_process_agent_responses_skips_paused_room(self):
        """Test that paused rooms are skipped."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_orch_context = Mock(db=mock_db, room_id=1)

        # Mock paused room
        paused_room = Mock(is_paused=True)

        with patch("orchestration.orchestrator.crud.get_room_cached", return_value=paused_room):
            await orchestrator._process_agent_responses(
                orch_context=mock_orch_context,
                agents=[],
                interrupt_agents=[],
                critic_agents=[],
                user_message_content="Hello",
            )

            # Should exit early without processing
            # (no other mocks should be called)

    @pytest.mark.asyncio
    async def test_process_agent_responses_calls_initial_responses(self):
        """Test that initial agent responses are called."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_agent_manager = AsyncMock()
        mock_orch_context = Mock(db=mock_db, room_id=1, agent_manager=mock_agent_manager)

        # Mock active room with one agent
        active_room = Mock(is_paused=False, max_interactions=None)
        mock_agent = Mock(id=1, name="Alice", is_critic=False)

        with (
            patch("orchestration.orchestrator.crud.get_room_cached", return_value=active_room),
            patch.object(orchestrator, "_initial_agent_responses", return_value=1) as mock_initial,
            patch.object(orchestrator, "_follow_up_rounds", new=AsyncMock()) as mock_follow_up,
        ):
            await orchestrator._process_agent_responses(
                orch_context=mock_orch_context,
                agents=[mock_agent],
                interrupt_agents=[],
                critic_agents=[],
                user_message_content="Hello",
            )

            # Should call initial responses
            mock_initial.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_agent_responses_skips_follow_up_with_one_agent(self):
        """Test that follow-up rounds are skipped with only one agent."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_agent_manager = AsyncMock()
        mock_orch_context = Mock(db=mock_db, room_id=1, agent_manager=mock_agent_manager)

        active_room = Mock(is_paused=False, max_interactions=None)
        mock_agent = Mock(id=1, name="Alice")

        with (
            patch("orchestration.orchestrator.crud.get_room_cached", return_value=active_room),
            patch.object(orchestrator, "_initial_agent_responses", return_value=1),
            patch.object(orchestrator, "_follow_up_rounds", new=AsyncMock()) as mock_follow_up,
        ):
            await orchestrator._process_agent_responses(
                orch_context=mock_orch_context,
                agents=[mock_agent],  # Only one agent
                interrupt_agents=[],
                critic_agents=[],
                user_message_content="Hello",
            )

            # Should NOT call follow-up rounds with single agent
            mock_follow_up.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_agent_responses_processes_critics(self):
        """Test that critic agents are processed."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_agent_manager = AsyncMock()
        mock_orch_context = Mock(db=mock_db, room_id=1, agent_manager=mock_agent_manager)

        active_room = Mock(is_paused=False, max_interactions=None)
        mock_agent = Mock(id=1, name="Alice")
        mock_critic = Mock(id=2, name="Critic", is_critic=True)

        with (
            patch("orchestration.orchestrator.crud.get_room_cached", return_value=active_room),
            patch.object(orchestrator, "_initial_agent_responses", return_value=1),
            patch.object(orchestrator, "_process_critic_feedback", new=AsyncMock()) as mock_critics,
        ):
            await orchestrator._process_agent_responses(
                orch_context=mock_orch_context,
                agents=[mock_agent],
                interrupt_agents=[],
                critic_agents=[mock_critic],
                user_message_content="Hello",
            )

            # Should process critics
            mock_critics.assert_awaited_once()


class TestInitialAgentResponses:
    """Tests for _initial_agent_responses method."""

    @pytest.mark.asyncio
    async def test_initial_agent_responses_concurrent_execution(self):
        """Test that agents respond concurrently."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_orch_context = Mock(db=mock_db, room_id=1)

        # Mock active room
        active_room = Mock(is_paused=False)

        # Create multiple mock agents (without priority)
        agents = [Mock(id=i, name=f"Agent{i}", priority=0, transparent=False) for i in range(3)]

        with (
            patch("orchestration.orchestrator.crud.get_room_cached", return_value=active_room),
            patch.object(
                orchestrator.response_generator, "generate_response", new=AsyncMock(return_value=True)
            ) as mock_generate,
        ):
            total = await orchestrator._initial_agent_responses(
                orch_context=mock_orch_context,
                agents=agents,
                interrupt_agents=[],
                user_message_content="Hello",
                total_messages=0,
            )

            # Should have called generate_response for each agent
            assert mock_generate.await_count == 3

            # Should return count of responses
            assert total == 3

    @pytest.mark.asyncio
    async def test_initial_agent_responses_counts_only_real_responses(self):
        """Test that skipped responses are not counted."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_orch_context = Mock(db=mock_db, room_id=1)

        active_room = Mock(is_paused=False)
        agents = [Mock(id=1, priority=0, transparent=False), Mock(id=2, priority=0, transparent=False), Mock(id=3, priority=0, transparent=False)]

        # Mock some agents skipping
        async def mock_generate(orch_context, agent, user_message_content):
            # Agent 2 skips
            return agent.id != 2

        with (
            patch("orchestration.orchestrator.crud.get_room_cached", return_value=active_room),
            patch.object(orchestrator.response_generator, "generate_response", side_effect=mock_generate),
        ):
            total = await orchestrator._initial_agent_responses(
                orch_context=mock_orch_context,
                agents=agents,
                interrupt_agents=[],
                user_message_content="Hello",
                total_messages=0,
            )

            # Should count only 2 responses (agent 2 skipped)
            assert total == 2


class TestFollowUpRounds:
    """Tests for _follow_up_rounds method."""

    @pytest.mark.asyncio
    async def test_follow_up_rounds_respects_max_rounds(self):
        """Test that follow-up rounds respect max limit."""
        orchestrator = ChatOrchestrator(max_follow_up_rounds=2)
        mock_db = AsyncMock()
        mock_orch_context = Mock(db=mock_db, room_id=1)

        active_room = Mock(is_paused=False, max_interactions=None)
        agents = [Mock(id=1, priority=0, transparent=False), Mock(id=2, priority=0, transparent=False)]

        call_count = 0

        async def mock_generate(orch_context, agent, user_message_content):
            nonlocal call_count
            call_count += 1
            # Always respond to create multiple rounds
            return True

        with (
            patch("orchestration.orchestrator.crud.get_room_cached", return_value=active_room),
            patch.object(orchestrator, "_count_agent_messages", return_value=0),
            patch.object(orchestrator.response_generator, "generate_response", side_effect=mock_generate),
        ):
            await orchestrator._follow_up_rounds(
                orch_context=mock_orch_context, agents=agents, interrupt_agents=[], total_messages=0
            )

            # Should have run 2 rounds with 2 agents each = 4 calls
            assert call_count == 4

    @pytest.mark.asyncio
    async def test_follow_up_rounds_stops_when_no_responses(self):
        """Test that follow-up rounds stop when no agent responds."""
        orchestrator = ChatOrchestrator(max_follow_up_rounds=10)
        mock_db = AsyncMock()
        mock_orch_context = Mock(db=mock_db, room_id=1)

        active_room = Mock(is_paused=False, max_interactions=None)
        agents = [Mock(id=1, priority=0, transparent=False), Mock(id=2, priority=0, transparent=False)]

        with (
            patch("orchestration.orchestrator.crud.get_room_cached", return_value=active_room),
            patch.object(orchestrator, "_count_agent_messages", return_value=0),
            patch.object(orchestrator.response_generator, "generate_response", return_value=False),
        ):  # All skip
            await orchestrator._follow_up_rounds(
                orch_context=mock_orch_context, agents=agents, interrupt_agents=[], total_messages=0
            )

            # Should stop after first round where all agents skipped
            # No assertion needed - test passes if it completes without hanging

    @pytest.mark.asyncio
    async def test_follow_up_rounds_respects_max_interactions(self):
        """Test that follow-up rounds respect room max_interactions limit."""
        orchestrator = ChatOrchestrator()
        mock_db = AsyncMock()
        mock_orch_context = Mock(db=mock_db, room_id=1)

        # Room has max 5 interactions, and already has 4
        active_room = Mock(is_paused=False, max_interactions=5)
        agents = [Mock(id=1, priority=0, transparent=False), Mock(id=2, priority=0, transparent=False)]

        call_count = 0
        message_count = 4  # Start with 4 messages

        # Mock that dynamically updates count as messages are added
        async def mock_count_messages(db, room_id):
            return message_count

        async def mock_generate(orch_context, agent, user_message_content):
            nonlocal call_count, message_count
            call_count += 1
            message_count += 1  # Simulate database update
            return True

        with (
            patch("orchestration.orchestrator.crud.get_room_cached", return_value=active_room),
            patch.object(orchestrator, "_count_agent_messages", side_effect=mock_count_messages),
            patch.object(orchestrator.response_generator, "generate_response", side_effect=mock_generate),
        ):
            await orchestrator._follow_up_rounds(
                orch_context=mock_orch_context, agents=agents, interrupt_agents=[], total_messages=0
            )

            # Should only allow 1 more message (to reach limit of 5)
            assert call_count == 1


class TestProcessCriticFeedback:
    """Tests for _process_critic_feedback method."""

    @pytest.mark.asyncio
    async def test_process_critic_feedback_concurrent(self):
        """Test that critics process concurrently."""
        orchestrator = ChatOrchestrator()
        mock_orch_context = Mock()

        critics = [Mock(id=i, name=f"Critic{i}") for i in range(3)]

        with patch.object(
            orchestrator.response_generator, "generate_response", new=AsyncMock(return_value=True)
        ) as mock_generate:
            await orchestrator._process_critic_feedback(
                orch_context=mock_orch_context, critic_agents=critics, user_message_content="Hello"
            )

            # Should call generate_response for each critic with is_critic=True
            assert mock_generate.await_count == 3

            # Verify is_critic flag was set
            for call in mock_generate.await_args_list:
                assert call[1]["is_critic"] is True

    @pytest.mark.asyncio
    async def test_process_critic_feedback_handles_errors(self):
        """Test that critic errors don't stop other critics."""
        orchestrator = ChatOrchestrator()
        mock_orch_context = Mock()

        critics = [Mock(id=1, name="Critic1"), Mock(id=2, name="Critic2")]

        # First critic raises error, second succeeds
        mock_generate = AsyncMock(side_effect=[Exception("Critic error"), True])

        with patch.object(orchestrator.response_generator, "generate_response", mock_generate):
            # Should not raise exception
            await orchestrator._process_critic_feedback(
                orch_context=mock_orch_context, critic_agents=critics, user_message_content="Hello"
            )

            # Both critics should have been processed
            assert mock_generate.await_count == 2
