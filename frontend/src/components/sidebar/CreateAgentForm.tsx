import { useState } from 'react';
import type { Agent, AgentCreate, AgentConfig } from '../../types';

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
    <div className="p-3 sm:p-4 border-b border-slate-200 bg-slate-50">
      <div className="flex gap-2 mb-3">
        <button
          onClick={() => setCreateMode('config')}
          className={`flex-1 px-2 sm:px-3 py-2 rounded-lg font-medium text-xs transition-all min-h-[40px] touch-manipulation ${
            createMode === 'config'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-100 active:bg-slate-200'
          }`}
        >
          Config File
        </button>
        <button
          onClick={() => setCreateMode('custom')}
          className={`flex-1 px-2 sm:px-3 py-2 rounded-lg font-medium text-xs transition-all min-h-[40px] touch-manipulation ${
            createMode === 'custom'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'bg-white text-slate-600 border border-slate-300 hover:bg-slate-100 active:bg-slate-200'
          }`}
        >
          Custom
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="text"
          value={newAgent.name}
          onChange={(e) => {
            setNewAgent({ ...newAgent, name: e.target.value });
            setAgentError(null);
          }}
          placeholder="Agent name"
          className="w-full px-3 py-2.5 text-sm sm:text-base border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent min-h-[44px]"
          autoFocus
        />

        {createMode === 'config' ? (
          <>
            <select
              value={newAgent.config_file}
              onChange={(e) => setNewAgent({ ...newAgent, config_file: e.target.value })}
              className="w-full px-3 py-2.5 text-sm sm:text-base border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent min-h-[44px]"
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
              <div className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-1.5">
                No config files found
              </div>
            )}
          </>
        ) : (
          <div className="space-y-2">
            <textarea
              value={newAgent.in_a_nutshell}
              onChange={(e) => setNewAgent({ ...newAgent, in_a_nutshell: e.target.value })}
              placeholder="In a Nutshell (brief identity)"
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg h-16 sm:h-20 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
            />
            <textarea
              value={newAgent.characteristics}
              onChange={(e) => setNewAgent({ ...newAgent, characteristics: e.target.value })}
              placeholder="Characteristics (optional)"
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg h-16 sm:h-20 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
            />
          </div>
        )}

        {agentError && (
          <div className="text-red-600 text-xs sm:text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {agentError}
          </div>
        )}

        <button
          type="submit"
          className="w-full px-3 sm:px-4 py-2.5 sm:py-3 text-sm sm:text-base bg-green-600 text-white rounded-lg hover:bg-green-700 active:bg-green-800 font-medium transition-colors shadow-sm min-h-[44px]"
        >
          Create Agent
        </button>
      </form>
    </div>
  );
};
