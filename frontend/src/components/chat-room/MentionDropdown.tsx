/**
 * MentionDropdown component for @ mention autocomplete
 * Shows a list of agents that can be mentioned
 */

import { useEffect, useRef } from 'react';
import type { Agent } from '../../types';
import { AgentAvatar } from '../AgentAvatar';
import { cn } from '@/lib/utils';

interface MentionDropdownProps {
  agents: Agent[];
  selectedIndex: number;
  onSelect: (agent: Agent) => void;
  onClose: () => void;
}

export function MentionDropdown({
  agents,
  selectedIndex,
  onSelect,
  onClose,
}: MentionDropdownProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const selectedRef = useRef<HTMLButtonElement>(null);

  // Scroll selected item into view
  useEffect(() => {
    if (selectedRef.current && listRef.current) {
      selectedRef.current.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      });
    }
  }, [selectedIndex]);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (listRef.current && !listRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  if (agents.length === 0) {
    return (
      <div
        ref={listRef}
        className="absolute bottom-full left-0 mb-1 w-64 bg-white rounded-lg shadow-lg border border-slate-200 p-3 text-sm text-slate-500 z-50"
      >
        No matching agents
      </div>
    );
  }

  return (
    <div
      ref={listRef}
      className="absolute bottom-full left-0 mb-1 w-72 max-h-48 overflow-y-auto bg-white rounded-lg shadow-lg border border-slate-200 z-50"
    >
      <div className="py-1">
        {agents.map((agent, index) => (
          <button
            key={agent.id}
            ref={index === selectedIndex ? selectedRef : undefined}
            onClick={() => onSelect(agent)}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2 text-left transition-colors',
              index === selectedIndex
                ? 'bg-blue-50 text-blue-700'
                : 'hover:bg-slate-50'
            )}
          >
            <AgentAvatar agent={agent} size="sm" />
            <div className="flex-1 min-w-0">
              <div className="font-medium truncate">{agent.name}</div>
              {agent.group && (
                <div className="text-xs text-slate-400 truncate">{agent.group}</div>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
