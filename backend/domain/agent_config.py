"""
Agent configuration data structure.

Groups agent configuration fields for clean parameter passing.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from domain.memory import MemoryPolicy


@dataclass
class AgentConfigData:
    """
    Agent configuration fields grouped together.

    This dataclass groups the agent configuration fields that are
    stored in the database and passed around in business logic.

    Attributes:
        config_file: Path to agent config folder (e.g., "agents/group_장송의프리렌/프리렌")
        in_a_nutshell: Brief identity summary
        characteristics: Personality traits and behaviors
        recent_events: Short-term recent context
        profile_pic: Optional profile picture filename
        long_term_memory_index: Dict mapping memory subtitles to their full content
        long_term_memory_subtitles: List of available memory subtitles (for context injection)
        memory_brain_enabled: Whether to use memory-brain for this agent
        memory_brain_policy: Memory selection policy (balanced, trauma_biased, etc.)
    """

    config_file: Optional[str] = None
    in_a_nutshell: Optional[str] = None
    characteristics: Optional[str] = None
    recent_events: Optional[str] = None
    profile_pic: Optional[str] = None
    long_term_memory_index: Optional[Dict[str, str]] = None
    long_term_memory_subtitles: Optional[str] = None
    memory_brain_enabled: bool = False
    memory_brain_policy: MemoryPolicy = MemoryPolicy.BALANCED

    def has_content(self) -> bool:
        """
        Check if any configuration field has content.

        Returns:
            True if at least one field is non-empty, False otherwise
        """
        return any([self.in_a_nutshell, self.characteristics, self.recent_events])

    def to_system_prompt_markdown(self, agent_name: str) -> str:
        """
        Build character configuration as markdown for system prompt injection.

        This format replaces the XML-based tool description injection when
        RETIRE_TRAIT_INJECTION is enabled.

        Args:
            agent_name: The name of the agent

        Returns:
            Markdown-formatted configuration string with ## headings
        """
        sections = []

        if self.in_a_nutshell:
            sections.append(f"## {agent_name} in a nutshell\n\n{self.in_a_nutshell}")

        if self.characteristics:
            sections.append(f"## {agent_name}'s characteristics\n\n{self.characteristics}")

        if self.recent_events:
            sections.append(f"## Recent events\n\n{self.recent_events}")

        if self.long_term_memory_subtitles:
            sections.append(
                f"## Long-term memory index\n\n"
                f"Available detailed memories (use 'recall' tool to retrieve): {self.long_term_memory_subtitles}"
            )

        if sections:
            return "\n\n" + "\n\n".join(sections)
        return ""

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfigData":
        """
        Create AgentConfigData from a dictionary.

        Args:
            data: Dictionary with config keys

        Returns:
            AgentConfigData instance
        """
        # Parse memory_brain_policy if present
        policy = data.get("memory_brain_policy", "balanced")
        if isinstance(policy, str):
            try:
                policy = MemoryPolicy(policy.lower())
            except ValueError:
                policy = MemoryPolicy.BALANCED

        return cls(
            config_file=data.get("config_file"),
            in_a_nutshell=data.get("in_a_nutshell"),
            characteristics=data.get("characteristics"),
            recent_events=data.get("recent_events"),
            profile_pic=data.get("profile_pic"),
            long_term_memory_index=data.get("long_term_memory_index"),
            long_term_memory_subtitles=data.get("long_term_memory_subtitles"),
            memory_brain_enabled=data.get("memory_brain_enabled", False),
            memory_brain_policy=policy,
        )
