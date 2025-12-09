"""
Chat orchestrator for managing multi-agent conversations.

This module handles the logic for multi-round conversations between agents,
including context building, response generation, and message broadcasting.

Uses a tape-based scheduling system for predictable turn management.
"""

import asyncio
import logging
import time
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("ChatOrchestrator")

import crud
import models
import schemas
from domain.contexts import OrchestrationContext
from sdk import AgentManager

from .agent_ordering import is_transparent, separate_interrupt_agents
from .memory_brain import MemoryBrain
from .response_generator import ResponseGenerator
from .tape import TapeExecutor, TapeGenerator

# Multi-round conversation settings
MAX_FOLLOW_UP_ROUNDS = 5  # Number of follow-up rounds after initial responses
MAX_TOTAL_MESSAGES = 30  # Safety limit to prevent infinite loops


class ChatOrchestrator:
    """
    Orchestrates multi-agent conversations with follow-up rounds.
    Supports priority agent system where specific agents get first chance to respond.
    """

    def __init__(
        self,
        max_follow_up_rounds: int = MAX_FOLLOW_UP_ROUNDS,
        max_total_messages: int = MAX_TOTAL_MESSAGES,
        priority_agent_names: List[str] = None,
    ):
        self.max_follow_up_rounds = max_follow_up_rounds
        self.max_total_messages = max_total_messages
        self.priority_agent_names = priority_agent_names or []
        # Track active processing tasks per room for interruption
        self.active_room_tasks: dict[int, asyncio.Task] = {}
        # Used to skip broadcasting responses that were started before the interruption
        self.last_user_message_time: dict[int, float] = {}
        # Initialize memory brain (shared across all agents)
        self.memory_brain = MemoryBrain()
        # Initialize response generator
        self.response_generator = ResponseGenerator(self.last_user_message_time, self.memory_brain)

    async def shutdown(self, timeout: float = 5.0):
        """
        Gracefully shutdown the orchestrator, cancelling all active room tasks.

        Args:
            timeout: Maximum time to wait for tasks to complete before cancelling
        """
        if not self.active_room_tasks:
            return

        logger.info(f"🛑 Shutting down orchestrator with {len(self.active_room_tasks)} active room tasks")

        # Cancel all active tasks
        for room_id, task in list(self.active_room_tasks.items()):
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete (or be cancelled)
        if self.active_room_tasks:
            tasks = list(self.active_room_tasks.values())
            done, pending = await asyncio.wait(tasks, timeout=timeout)

            if pending:
                logger.warning(f"⚠️ {len(pending)} room tasks did not complete within {timeout}s")

        # Clear tracking dicts
        self.active_room_tasks.clear()
        self.last_user_message_time.clear()
        logger.info("✅ Orchestrator shutdown complete")

    def get_chatting_agents(self, room_id: int, agent_manager: AgentManager) -> list[int]:
        """
        Get list of agent IDs currently chatting (generating responses) in a room.

        Args:
            room_id: Room ID
            agent_manager: AgentManager instance

        Returns:
            List of agent IDs currently processing in this room
        """
        chatting_agent_ids = []

        for task_id in agent_manager.active_clients.keys():
            if task_id.room_id == room_id:
                chatting_agent_ids.append(task_id.agent_id)

        return chatting_agent_ids

    async def interrupt_room_processing(self, room_id: int, agent_manager: AgentManager):
        """
        Interrupt all agents currently processing in a room.
        This is called when a new user message arrives while agents are still responding.
        """
        # Cancel any active processing task for this room
        if room_id in self.active_room_tasks:
            task = self.active_room_tasks[room_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass  # Expected

        # Interrupt all agents in this room via the agent manager
        await agent_manager.interrupt_room(room_id)

    async def cleanup_room_state(self, room_id: int, agent_manager: AgentManager):
        """
        Clean up all state associated with a room.
        This should be called when a room is deleted to prevent memory leaks.

        Args:
            room_id: Room ID to clean up
            agent_manager: AgentManager instance for interrupting any active processing
        """
        logger.info(f"🧹 Cleaning up room state | Room: {room_id}")

        # First, interrupt any ongoing processing
        await self.interrupt_room_processing(room_id, agent_manager)

        # Remove from active tasks tracking (may already be removed by interrupt, but ensure it's gone)
        if room_id in self.active_room_tasks:
            del self.active_room_tasks[room_id]
            logger.info(f"✅ Removed room {room_id} from active_room_tasks")

        # Remove from last user message time tracking
        if room_id in self.last_user_message_time:
            del self.last_user_message_time[room_id]
            logger.info(f"✅ Removed room {room_id} from last_user_message_time")

        # Clean up memory state for this room
        self.memory_brain.cleanup(room_id)
        logger.info(f"✅ Cleared memory state for room {room_id}")

        logger.info(f"✅ Room state cleanup complete | Room: {room_id}")

    async def handle_user_message(
        self,
        db: AsyncSession,
        room_id: int,
        message_data: dict,
        _manager,  # Deprecated, kept for backward compatibility (always None)
        agent_manager: AgentManager,
        saved_user_message_id: int = None,  # Optional: ID of already-saved message to avoid duplication
    ):
        """
        Handle a user message and orchestrate agent responses.
        Interrupts any ongoing agent processing in this room.

        Args:
            db: Database session
            room_id: Room ID
            message_data: Message data from client
            _manager: Deprecated parameter (kept for backward compatibility, always None)
            agent_manager: AgentManager for generating responses
            saved_user_message_id: Optional ID of pre-saved message (used by REST API to avoid duplication)
        """
        logger.info(f"🔵 USER MESSAGE RECEIVED | Room: {room_id} | Content: {message_data.get('content', '')[:50]}")

        # Record the timestamp of this user message for interruption tracking
        self.last_user_message_time[room_id] = time.time()

        # Increment turn counter for memory state tracking
        self.memory_brain.increment_turn(room_id)

        # Save user message FIRST (only if not already saved)
        if saved_user_message_id is None:
            user_message = schemas.MessageCreate(
                content=message_data["content"],
                role="user",
                participant_type=message_data.get("participant_type"),
                participant_name=message_data.get("participant_name"),
            )
            # Create message and update room activity atomically
            saved_user_msg = await crud.create_message(db, room_id, user_message, update_room_activity=True)
        else:
            # Fetch the already-saved message in this session
            saved_user_msg = await db.get(models.Message, saved_user_message_id)

        # Note: User message broadcasting removed - not needed with HTTP polling architecture
        # Clients poll /api/rooms/{room_id}/messages to get new messages
        # The user message is already saved to database above, so polling will pick it up
        logger.info(
            f"💾 USER MESSAGE SAVED | Room: {room_id} | ID: {saved_user_msg.id} | Content: {saved_user_msg.content[:50]}"
        )

        # NOW interrupt any ongoing agent processing for this room
        await self.interrupt_room_processing(room_id, agent_manager)
        logger.info(f"🛑 INTERRUPTED | Room: {room_id}")

        # Get all agents for the room (use cache for performance)
        all_agents = await crud.get_agents_cached(db, room_id)

        # Filter by mentioned agents if specified (@ mention feature)
        mentioned_agent_ids = message_data.get("mentioned_agent_ids")
        if mentioned_agent_ids:
            mentioned_set = set(mentioned_agent_ids)
            room_agent_ids = {agent.id for agent in all_agents}
            # Validate: only keep mentions that are actually in the room
            valid_mentions = mentioned_set & room_agent_ids
            if valid_mentions != mentioned_set:
                invalid = mentioned_set - room_agent_ids
                logger.warning(f"⚠️ Invalid @mentions (not in room): {invalid}")
            if valid_mentions:
                all_agents = [a for a in all_agents if a.id in valid_mentions]
                logger.info(f"🎯 MENTION FILTER | Room: {room_id} | Only responding: {[a.name for a in all_agents]}")

        # Separate regular agents from critics
        agents = [agent for agent in all_agents if not agent.is_critic]
        critic_agents = [agent for agent in all_agents if agent.is_critic]

        # Separate interrupt agents from regular agents
        interrupt_agents, non_interrupt_agents = separate_interrupt_agents(agents)

        # Create orchestration context
        orch_context = OrchestrationContext(db=db, room_id=room_id, agent_manager=agent_manager)

        # Create a processing task for this room
        logger.info(
            f"🚀 STARTING AGENT PROCESSING | Room: {room_id} | Agents: {len(non_interrupt_agents)} "
            f"| Interrupt Agents: {len(interrupt_agents)} | Critics: {len(critic_agents)}"
        )
        processing_task = asyncio.create_task(
            self._process_agent_responses(
                orch_context=orch_context,
                agents=non_interrupt_agents,
                interrupt_agents=interrupt_agents,
                critic_agents=critic_agents,
                user_message_content=message_data["content"],
            )
        )

        # Track this task so we can cancel it if a new message arrives
        self.active_room_tasks[room_id] = processing_task

        try:
            await processing_task
            logger.info(f"✅ AGENT PROCESSING COMPLETE | Room: {room_id}")
        except asyncio.CancelledError:
            # Task was cancelled by a new message, this is expected
            logger.info(f"❌ AGENT PROCESSING CANCELLED | Room: {room_id}")
            pass
        except Exception as e:
            logger.error(f"💥 ERROR IN AGENT PROCESSING | Room: {room_id} | Error: {e}")
            import traceback

            traceback.print_exc()
        finally:
            # Clean up task tracking
            if room_id in self.active_room_tasks and self.active_room_tasks[room_id] == processing_task:
                del self.active_room_tasks[room_id]

    async def _process_agent_responses(
        self,
        orch_context: OrchestrationContext,
        agents: List,
        interrupt_agents: List,
        critic_agents: List,
        user_message_content: str,
    ):
        """
        Internal method to process all agent responses using tape-based scheduling.
        This can be cancelled if a new user message arrives.
        Critics are processed separately and their feedback is stored but not broadcast.
        Interrupt agents respond after every non-transparent agent message.
        """
        logger.info(f"_process_agent_responses called | Room: {orch_context.room_id}")

        # Check if room is paused
        room = await crud.get_room_cached(orch_context.db, orch_context.room_id)
        if room and room.is_paused:
            logger.info(f"Room {orch_context.room_id} is paused. Skipping agent responses.")
            return

        logger.info(f"Room {orch_context.room_id} is NOT paused. Proceeding with agents...")

        # Create tape generator and executor
        generator = TapeGenerator(agents, interrupt_agents)
        agents_by_id = {a.id: a for a in agents + interrupt_agents}
        executor = TapeExecutor(
            response_generator=self.response_generator,
            agents_by_id=agents_by_id,
            max_total_messages=self.max_total_messages,
        )

        # Generate and execute initial round tape
        logger.info(f"Starting initial agent responses for {len(agents)} agent(s)...")
        initial_tape = generator.generate_initial_round()
        result = await executor.execute(
            tape=initial_tape,
            orch_context=orch_context,
            user_message_content=user_message_content,
        )
        total_messages = result.total_responses
        logger.info(f"Initial agent responses complete. Total messages: {total_messages}")

        # Check stop conditions from initial round
        if result.was_paused or result.reached_limit or result.was_interrupted:
            logger.info(f"Stopping after initial round | paused={result.was_paused} limit={result.reached_limit}")
            if critic_agents:
                await self._process_critic_feedback(orch_context, critic_agents, user_message_content)
            return

        # Skip follow-up rounds if all interrupt agents are transparent
        all_interrupt_transparent = interrupt_agents and all(is_transparent(a) for a in interrupt_agents)
        all_agents = agents + interrupt_agents

        if all_interrupt_transparent:
            logger.info("All interrupt agents are transparent, skipping follow-up rounds")
        elif len(all_agents) > 1:
            # Execute follow-up rounds using tape system
            for round_num in range(self.max_follow_up_rounds):
                follow_up_tape = generator.generate_follow_up_round(round_num)
                result = await executor.execute(
                    tape=follow_up_tape,
                    orch_context=orch_context,
                    user_message_content=None,  # No user message for follow-ups
                    current_total=total_messages,
                )
                total_messages += result.total_responses

                # Check stop conditions
                if result.was_paused or result.reached_limit or result.was_interrupted:
                    logger.info(f"Stopping follow-up round {round_num + 1} | paused={result.was_paused}")
                    break

                # If all agents skipped, conversation is over
                if result.all_skipped:
                    logger.info(f"All agents skipped in round {round_num + 1}, ending conversation")
                    break

        # Process critic feedback (after conversation rounds complete)
        if critic_agents:
            await self._process_critic_feedback(
                orch_context=orch_context, critic_agents=critic_agents, user_message_content=user_message_content
            )

    async def _process_critic_feedback(
        self, orch_context: OrchestrationContext, critic_agents: List, user_message_content: str
    ):
        """
        Generate feedback from critic agents after conversation rounds.
        Critics observe the conversation but don't participate directly.
        Their feedback is stored but not broadcast to the main chat.
        """
        logger.info(f"🔍 Processing critic feedback | Room: {orch_context.room_id} | Critics: {len(critic_agents)}")

        # Create tasks for all critics to run concurrently
        tasks = [
            self.response_generator.generate_response(
                orch_context=orch_context,
                agent=critic,
                user_message_content=user_message_content,
                is_critic=True,  # Flag to indicate this is a critic
            )
            for critic in critic_agents
        ]

        # Wait for all critics to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Critic {critic_agents[i].name} error: {result}")
            else:
                logger.info(f"✅ Critic {critic_agents[i].name} feedback stored")


    async def _count_agent_messages(self, db: AsyncSession, room_id: int) -> int:
        """Count the number of agent messages (role='assistant') in a room."""
        from sqlalchemy import func
        from sqlalchemy.future import select

        result = await db.execute(
            select(func.count(models.Message.id)).where(
                models.Message.room_id == room_id, models.Message.role == "assistant"
            )
        )
        return result.scalar() or 0
