import { useState, useMemo } from 'react';
import { ChevronDown, Info, Trash2 } from 'lucide-react';
import type { Agent } from '../../types';
import { AgentAvatar } from '../AgentAvatar';
import { useAuth } from '../../contexts/AuthContext';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

interface AgentListPanelProps {
  agents: Agent[];
  selectedAgentId: number | null;
  onSelectAgent: (agentId: number) => void;
  onDeleteAgent: (agentId: number) => Promise<void>;
  onViewProfile: (agent: Agent) => void;
}

export const AgentListPanel = ({
  agents,
  selectedAgentId,
  onSelectAgent,
  onDeleteAgent,
  onViewProfile,
}: AgentListPanelProps) => {
  const { isAdmin } = useAuth();
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const groupedAgents = useMemo(() => {
    const groups = new Map<string, Agent[]>();

    agents.forEach((agent) => {
      const groupName = agent.group || 'Ungrouped';
      if (!groups.has(groupName)) {
        groups.set(groupName, []);
      }
      groups.get(groupName)!.push(agent);
    });

    const sortedGroups = Array.from(groups.entries()).sort(([a], [b]) => {
      if (a === 'Ungrouped') return 1;
      if (b === 'Ungrouped') return -1;
      return a.localeCompare(b, 'ko-KR', { sensitivity: 'base' });
    });

    return sortedGroups;
  }, [agents]);

  const toggleGroup = (groupName: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupName)) {
        next.delete(groupName);
      } else {
        next.add(groupName);
      }
      return next;
    });
  };

  const renderAgent = (agent: Agent) => (
    <div
      key={agent.id}
      className={cn(
        'group relative flex items-center gap-2.5 px-2 py-1.5 rounded cursor-pointer transition-colors',
        selectedAgentId === agent.id
          ? 'bg-sidebar-accent text-sidebar-accent-foreground'
          : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
      )}
    >
      <div
        onClick={() => onSelectAgent(agent.id)}
        className="flex items-center gap-2.5 flex-1 min-w-0"
      >
        <AgentAvatar
          agent={agent}
          size="sm"
          className={cn(
            'w-8 h-8',
            selectedAgentId === agent.id && 'ring-2 ring-accent'
          )}
        />
        <span className={cn(
          'font-medium truncate text-sm',
          selectedAgentId === agent.id && 'text-sidebar-foreground'
        )}>
          {agent.name}
        </span>
      </div>

      <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          onClick={(e) => {
            e.stopPropagation();
            onViewProfile(agent);
          }}
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground hover:text-primary"
        >
          <Info className="w-3.5 h-3.5" />
        </Button>
        {isAdmin && (
          <Button
            onClick={(e) => {
              e.stopPropagation();
              if (confirm(`Delete agent "${agent.name}"?`)) {
                onDeleteAgent(agent.id);
              }
            }}
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        )}
      </div>
    </div>
  );

  return (
    <div className="p-2 space-y-2">
      {agents.length === 0 ? (
        <div className="text-center text-muted-foreground mt-8 px-4">
          <p className="text-sm">No agents yet</p>
          <p className="text-xs mt-1">Create one to get started!</p>
        </div>
      ) : (
        groupedAgents.map(([groupName, groupAgents]) => {
          const isCollapsed = collapsedGroups.has(groupName);
          return (
            <Collapsible
              key={groupName}
              open={!isCollapsed}
              onOpenChange={() => toggleGroup(groupName)}
            >
              <CollapsibleTrigger asChild>
                <button className="w-full flex items-center justify-between px-2 py-1.5 hover:bg-sidebar-accent/50 rounded transition-colors group/header">
                  <div className="flex items-center gap-2">
                    <ChevronDown
                      className={cn(
                        'w-4 h-4 text-muted-foreground transition-transform',
                        isCollapsed && '-rotate-90'
                      )}
                    />
                    <span className="font-semibold text-xs uppercase tracking-wide text-muted-foreground">
                      {groupName}
                    </span>
                  </div>
                  <Badge variant="secondary" className="text-xs px-1.5 py-0 h-5">
                    {groupAgents.length}
                  </Badge>
                </button>
              </CollapsibleTrigger>

              <CollapsibleContent className="space-y-0.5 mt-1">
                {groupAgents.map(renderAgent)}
              </CollapsibleContent>
            </Collapsible>
          );
        })
      )}
    </div>
  );
};
