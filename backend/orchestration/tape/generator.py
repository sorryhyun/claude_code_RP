"""
Tape generator for creating turn schedules.

This module generates turn tapes based on agent configurations,
weaving in interrupt agents appropriately.
"""

import logging
import random
from typing import List, Tuple

from .models import CellType, TurnCell, TurnTape

logger = logging.getLogger("TapeGenerator")


class TapeGenerator:
    """
    Generates turn tapes based on agent configurations.

    Algorithm:
    1. Separate agents into categories (priority, regular, interrupt)
    2. Build initial tape: all agents sequential (priority first, then shuffled regular)
    3. Weave interrupt agents after each non-transparent agent cell
    4. Build follow-up tapes: all agents sequential (priority first, then shuffled regular)
    """

    def __init__(self, agents: List, interrupt_agents: List):
        """
        Initialize generator with agent lists.

        Args:
            agents: Non-interrupt agents (may include priority agents)
            interrupt_agents: Agents with interrupt_every_turn=1
        """
        self.agents = agents
        self.interrupt_agents = interrupt_agents

        # Pre-sort agents
        self.priority_agents, self.regular_agents = self._separate_priority(agents)

        # Log configuration
        if self.priority_agents:
            priority_info = ", ".join([f"{a.name}(p={getattr(a, 'priority', 0)})" for a in self.priority_agents])
            logger.debug(f"Priority agents: {priority_info}")
        if self.regular_agents:
            logger.debug(f"Regular agents: {[a.name for a in self.regular_agents]}")
        if self.interrupt_agents:
            logger.debug(f"Interrupt agents: {[a.name for a in self.interrupt_agents]}")

    def _separate_priority(self, agents: List) -> Tuple[List, List]:
        """Separate and sort priority vs regular agents."""
        priority = []
        regular = []

        for agent in agents:
            if getattr(agent, "priority", 0) > 0:
                priority.append(agent)
            else:
                regular.append(agent)

        # Sort by priority descending (higher priority first)
        priority.sort(key=lambda a: getattr(a, "priority", 0), reverse=True)

        return priority, regular

    def _is_transparent(self, agent) -> bool:
        """Check if agent is transparent (doesn't trigger interrupt agents)."""
        return getattr(agent, "transparent", 0) == 1

    def _make_interrupt_cell(self, triggering_agent_id: int = None, exclude_agent_id: int = None) -> TurnCell:
        """
        Create an interrupt cell with all interrupt agents.

        Args:
            triggering_agent_id: Agent that triggered this interrupt (for logging)
            exclude_agent_id: Agent ID to exclude (for self-interruption prevention)
        """
        agent_ids = [a.id for a in self.interrupt_agents if a.id != exclude_agent_id]
        return TurnCell(
            cell_type=CellType.INTERRUPT,
            agent_ids=agent_ids,
            triggering_agent_id=triggering_agent_id,
        )

    def generate_initial_round(self) -> TurnTape:
        """
        Generate tape for initial response round (after user message).

        Structure:
        1. Interrupt agents respond to user first
        2. Priority agents sequential (each may trigger interrupts)
        3. Regular agents sequential in shuffled order (each may trigger interrupts)
        """
        tape = TurnTape()

        # Cell 0: Interrupt agents respond to user message first
        if self.interrupt_agents:
            tape.cells.append(
                TurnCell(
                    cell_type=CellType.INTERRUPT,
                    agent_ids=[a.id for a in self.interrupt_agents],
                    triggering_agent_id=None,  # Triggered by user
                )
            )

        # Priority agents: sequential, each triggers interrupts if non-transparent
        for agent in self.priority_agents:
            # Add priority agent cell
            tape.cells.append(
                TurnCell(
                    cell_type=CellType.SEQUENTIAL,
                    agent_ids=[agent.id],
                )
            )

            # Add interrupt cell after non-transparent agents
            if self.interrupt_agents and not self._is_transparent(agent):
                tape.cells.append(self._make_interrupt_cell(triggering_agent_id=agent.id))

        # Regular agents: sequential (one at a time, shuffled order)
        shuffled_regular = list(self.regular_agents)
        random.shuffle(shuffled_regular)

        for agent in shuffled_regular:
            tape.cells.append(
                TurnCell(
                    cell_type=CellType.SEQUENTIAL,
                    agent_ids=[agent.id],
                )
            )

            # Add interrupt cell after non-transparent agents
            if self.interrupt_agents and not self._is_transparent(agent):
                tape.cells.append(
                    self._make_interrupt_cell(
                        triggering_agent_id=agent.id,
                        exclude_agent_id=agent.id,
                    )
                )

        logger.info(f"Generated initial tape: {tape}")
        return tape

    def generate_follow_up_round(self, round_num: int = 0) -> TurnTape:
        """
        Generate tape for follow-up round.

        Structure:
        - All agents sequential
        - Priority agents first (in priority order)
        - Regular agents shuffled (for natural conversation)
        - Interrupt after each non-transparent agent

        Args:
            round_num: Round number (for logging)
        """
        tape = TurnTape()

        # Shuffle regular agents for natural conversation flow
        shuffled_regular = list(self.regular_agents)
        random.shuffle(shuffled_regular)

        # Combine: priority first, then shuffled regular
        ordered_agents = self.priority_agents + shuffled_regular

        for agent in ordered_agents:
            # Add agent cell (sequential)
            tape.cells.append(
                TurnCell(
                    cell_type=CellType.SEQUENTIAL,
                    agent_ids=[agent.id],
                )
            )

            # Add interrupt cell after non-transparent agents
            # Exclude the triggering agent from interrupt list to prevent self-interruption
            if self.interrupt_agents and not self._is_transparent(agent):
                tape.cells.append(
                    self._make_interrupt_cell(
                        triggering_agent_id=agent.id,
                        exclude_agent_id=agent.id,  # Prevent self-interruption
                    )
                )

        logger.debug(f"Generated follow-up tape (round {round_num + 1}): {tape}")
        return tape
