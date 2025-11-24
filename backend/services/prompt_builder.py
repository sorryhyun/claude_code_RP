"""
Prompt builder service for constructing agent system prompts.

This module provides centralized prompt building logic to avoid duplication
across CRUD operations.
"""

from config import get_base_system_prompt
from domain.agent_config import AgentConfigData
from utils.korean_particles import format_with_particles


def build_system_prompt(agent_name: str, config_data: AgentConfigData) -> str:
    """
    Build a complete system prompt for an agent.

    This function combines the base system prompt with agent-specific
    configuration markdown, applying Korean particle formatting.

    Args:
        agent_name: The name of the agent
        config_data: Agent configuration data

    Returns:
        Complete system prompt string with markdown formatting
    """
    # Start with base system prompt and apply Korean particle formatting
    system_prompt = format_with_particles(get_base_system_prompt(), agent_name=agent_name)

    # Append character configuration with markdown headings
    config_markdown = config_data.to_system_prompt_markdown(agent_name)
    if config_markdown:
        system_prompt += config_markdown

    return system_prompt
