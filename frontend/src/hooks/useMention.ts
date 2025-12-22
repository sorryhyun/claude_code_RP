/**
 * useMention hook for @ mention functionality
 * Manages mention dropdown state and keyboard navigation
 */

import { useState, useCallback, useMemo, useRef } from 'react';
import type { Agent } from '../types';
import { filterByKoreanSearch } from '../utils/koreanSearch';
import { extractMentionsAndClean } from '../utils/mentionParser';

interface MentionState {
  isOpen: boolean;
  triggerIndex: number; // Position of @ in text
  searchTerm: string;   // Text after @ for filtering
}

interface UseMentionReturn {
  // State
  isDropdownOpen: boolean;
  searchTerm: string;
  selectedIndex: number;
  filteredAgents: Agent[];

  // For positioning the dropdown
  triggerIndex: number;

  // Handlers
  handleInputChange: (value: string, cursorPosition: number) => void;
  handleKeyDown: (e: React.KeyboardEvent) => boolean; // Returns true if handled
  selectAgent: (agent: Agent, currentValue: string) => string; // Returns new input value
  closeDropdown: () => void;

  // For sending
  extractMentionsAndClean: (text: string) => {
    cleanContent: string;
    mentionedAgentIds: number[];
  };
}

export function useMention(agents: Agent[]): UseMentionReturn {
  const [mentionState, setMentionState] = useState<MentionState>({
    isOpen: false,
    triggerIndex: -1,
    searchTerm: '',
  });
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Track last cursor position to handle dropdown on arrow keys
  const lastCursorPosition = useRef<number>(0);

  // Filter agents based on search term
  const filteredAgents = useMemo(() => {
    if (!mentionState.isOpen) return [];
    return filterByKoreanSearch(agents, mentionState.searchTerm, (agent) => agent.name);
  }, [agents, mentionState.isOpen, mentionState.searchTerm]);

  // Reset selected index when filtered list changes
  const handleInputChange = useCallback((value: string, cursorPosition: number) => {
    lastCursorPosition.current = cursorPosition;

    // Find the last @ before cursor
    const textBeforeCursor = value.slice(0, cursorPosition);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');

    if (lastAtIndex === -1) {
      // No @ found before cursor
      setMentionState({ isOpen: false, triggerIndex: -1, searchTerm: '' });
      setSelectedIndex(0);
      return;
    }

    // Check if there's a space between @ and cursor (mention cancelled)
    const textAfterAt = textBeforeCursor.slice(lastAtIndex + 1);
    if (textAfterAt.includes(' ') || textAfterAt.includes('\n')) {
      setMentionState({ isOpen: false, triggerIndex: -1, searchTerm: '' });
      setSelectedIndex(0);
      return;
    }

    // We're in a mention - extract search term
    setMentionState({
      isOpen: true,
      triggerIndex: lastAtIndex,
      searchTerm: textAfterAt,
    });
    setSelectedIndex(0);
  }, []);

  const closeDropdown = useCallback(() => {
    setMentionState({ isOpen: false, triggerIndex: -1, searchTerm: '' });
    setSelectedIndex(0);
  }, []);

  const selectAgent = useCallback((agent: Agent, currentValue: string): string => {
    const { triggerIndex } = mentionState;
    if (triggerIndex === -1) return currentValue;

    // Replace @searchTerm with @AgentName and add a space
    const before = currentValue.slice(0, triggerIndex);
    const cursorPos = lastCursorPosition.current;
    const after = currentValue.slice(cursorPos);

    const newValue = `${before}@${agent.name} ${after}`;

    // Close dropdown
    closeDropdown();

    return newValue;
  }, [mentionState, closeDropdown]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent): boolean => {
    if (!mentionState.isOpen || filteredAgents.length === 0) {
      return false;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filteredAgents.length);
        return true;

      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredAgents.length) % filteredAgents.length);
        return true;

      case 'Enter':
      case 'Tab':
        if (filteredAgents[selectedIndex]) {
          e.preventDefault();
          // The actual selection is handled by MessageInput
          // which calls selectAgent with the current value
          return true;
        }
        return false;

      case 'Escape':
        e.preventDefault();
        closeDropdown();
        return true;

      default:
        return false;
    }
  }, [mentionState.isOpen, filteredAgents, selectedIndex, closeDropdown]);

  // Wrapper for extractMentionsAndClean that uses current agents
  const extractMentions = useCallback((text: string) => {
    return extractMentionsAndClean(text, agents);
  }, [agents]);

  return {
    isDropdownOpen: mentionState.isOpen,
    searchTerm: mentionState.searchTerm,
    selectedIndex,
    filteredAgents,
    triggerIndex: mentionState.triggerIndex,
    handleInputChange,
    handleKeyDown,
    selectAgent,
    closeDropdown,
    extractMentionsAndClean: extractMentions,
  };
}
