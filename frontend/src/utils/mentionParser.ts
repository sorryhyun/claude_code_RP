/**
 * Mention parser utility for @ mentions
 * Parses and removes @AgentName mentions from message text
 */

import type { Agent } from '../types';

export interface ParsedMention {
  agentId: number;
  agentName: string;
  startIndex: number;
  endIndex: number;
}

/**
 * Parse @mentions from message text.
 * Matches @AgentName against known agents in the room.
 *
 * @param text - The message text to parse
 * @param agents - List of agents in the room
 * @returns Array of parsed mentions with positions
 */
export function parseMentions(text: string, agents: Agent[]): ParsedMention[] {
  if (!text || agents.length === 0) return [];

  const mentions: ParsedMention[] = [];

  // Sort agents by name length (descending) to match longest names first
  // This handles cases like "@Alice" vs "@Alice Smith"
  const sortedAgents = [...agents].sort((a, b) => b.name.length - a.name.length);

  // Find all @ symbols
  let searchStart = 0;
  while (searchStart < text.length) {
    const atIndex = text.indexOf('@', searchStart);
    if (atIndex === -1) break;

    const afterAt = text.slice(atIndex + 1);

    // Try to match against each agent name (longest first)
    let matched = false;
    for (const agent of sortedAgents) {
      // Case-insensitive match
      if (afterAt.toLowerCase().startsWith(agent.name.toLowerCase())) {
        // Avoid duplicate mentions of the same agent
        if (!mentions.some(m => m.agentId === agent.id)) {
          mentions.push({
            agentId: agent.id,
            agentName: agent.name,
            startIndex: atIndex,
            endIndex: atIndex + 1 + agent.name.length,
          });
        }
        searchStart = atIndex + 1 + agent.name.length;
        matched = true;
        break;
      }
    }

    if (!matched) {
      searchStart = atIndex + 1;
    }
  }

  return mentions;
}

/**
 * Remove @mentions from text, returning clean content.
 * Removes mentions and any trailing whitespace.
 *
 * @param text - The original text with @mentions
 * @param mentions - The parsed mentions to remove
 * @returns Clean text without @mentions
 */
export function removeMentions(text: string, mentions: ParsedMention[]): string {
  if (mentions.length === 0) return text;

  // Sort by startIndex descending to remove from end first
  // This preserves indices as we remove
  const sorted = [...mentions].sort((a, b) => b.startIndex - a.startIndex);

  let result = text;
  for (const mention of sorted) {
    const before = result.slice(0, mention.startIndex);
    // Remove the mention and any trailing whitespace (but preserve newlines)
    const after = result.slice(mention.endIndex).replace(/^[ \t]+/, '');
    result = before + after;
  }

  return result.trim();
}

/**
 * Extract mentioned agent IDs and clean content from text.
 * Convenience function combining parseMentions and removeMentions.
 *
 * @param text - The message text
 * @param agents - List of agents in the room
 * @returns Object with clean content and mentioned agent IDs
 */
export function extractMentionsAndClean(
  text: string,
  agents: Agent[]
): { cleanContent: string; mentionedAgentIds: number[] } {
  const mentions = parseMentions(text, agents);
  const cleanContent = removeMentions(text, mentions);
  const mentionedAgentIds = mentions.map(m => m.agentId);

  return { cleanContent, mentionedAgentIds };
}
