import { useState } from 'react';
import type { Agent, AgentCreate, AgentConfig } from '../../types';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

interface CreateAgentFormProps {
  availableConfigs: AgentConfig;
  onCreateAgent: (agentData: AgentCreate) => Promise<Agent>;
  onClose: () => void;
}

export const CreateAgentForm = ({
  availableConfigs,
  onCreateAgent,
  onClose,
}: CreateAgentFormProps) => {
  const [createMode, setCreateMode] = useState<'config' | 'custom'>('config');
  const [newAgent, setNewAgent] = useState({
    name: '',
    config_file: '',
    in_a_nutshell: '',
    characteristics: '',
    backgrounds: '',
    memory: '',
    recent_events: '',
  });
  const [agentError, setAgentError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgent.name.trim()) return;

    try {
      setAgentError(null);
      const agentData = createMode === 'config'
        ? { name: newAgent.name, config_file: newAgent.config_file }
        : {
            name: newAgent.name,
            in_a_nutshell: newAgent.in_a_nutshell || null,
            characteristics: newAgent.characteristics || null,
            backgrounds: newAgent.backgrounds || null,
            memory: newAgent.memory || null,
            recent_events: newAgent.recent_events || null,
          };

      await onCreateAgent(agentData);
      setNewAgent({
        name: '',
        config_file: '',
        in_a_nutshell: '',
        characteristics: '',
        backgrounds: '',
        memory: '',
        recent_events: '',
      });
      onClose();
    } catch (err) {
      setAgentError(err instanceof Error ? err.message : 'Failed to create agent');
    }
  };

  return (
    <div className="p-3 border-b border-sidebar-border bg-sidebar-accent/50">
      <div className="flex gap-2 mb-3">
        <Button
          type="button"
          onClick={() => setCreateMode('config')}
          variant={createMode === 'config' ? 'default' : 'outline'}
          size="sm"
          className={cn(
            'flex-1',
            createMode === 'config' && 'bg-accent hover:bg-accent/90'
          )}
        >
          Config File
        </Button>
        <Button
          type="button"
          onClick={() => setCreateMode('custom')}
          variant={createMode === 'custom' ? 'default' : 'outline'}
          size="sm"
          className={cn(
            'flex-1',
            createMode === 'custom' && 'bg-accent hover:bg-accent/90'
          )}
        >
          Custom
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <Input
          type="text"
          value={newAgent.name}
          onChange={(e) => {
            setNewAgent({ ...newAgent, name: e.target.value });
            setAgentError(null);
          }}
          placeholder="Agent name"
          className="bg-sidebar-background border-sidebar-border"
          autoFocus
        />

        {createMode === 'config' ? (
          <>
            <select
              value={newAgent.config_file}
              onChange={(e) => setNewAgent({ ...newAgent, config_file: e.target.value })}
              className="w-full px-3 py-2 text-sm border rounded-md bg-sidebar-background border-sidebar-border text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              required
            >
              <option value="">Select a config file...</option>
              {Object.entries(availableConfigs).map(([name, path]) => (
                <option key={name} value={path}>
                  {name}
                </option>
              ))}
            </select>
            {Object.keys(availableConfigs).length === 0 && (
              <div className="text-xs text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1.5">
                No config files found
              </div>
            )}
          </>
        ) : (
          <div className="space-y-2">
            <Textarea
              value={newAgent.in_a_nutshell}
              onChange={(e) => setNewAgent({ ...newAgent, in_a_nutshell: e.target.value })}
              placeholder="In a Nutshell (brief identity)"
              className="bg-sidebar-background border-sidebar-border h-16 resize-none text-sm"
            />
            <Textarea
              value={newAgent.characteristics}
              onChange={(e) => setNewAgent({ ...newAgent, characteristics: e.target.value })}
              placeholder="Characteristics (optional)"
              className="bg-sidebar-background border-sidebar-border h-16 resize-none text-sm"
            />
          </div>
        )}

        {agentError && (
          <div className="text-destructive text-xs bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
            {agentError}
          </div>
        )}

        <Button type="submit" className="w-full bg-accent hover:bg-accent/90">
          Create Agent
        </Button>
      </form>
    </div>
  );
};
