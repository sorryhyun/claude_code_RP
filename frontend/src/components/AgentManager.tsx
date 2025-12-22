import { useState, useEffect, useMemo, memo } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services';
import type { Agent } from '../types';
import { AgentAvatar } from './AgentAvatar';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { koreanSearch } from '../utils/koreanSearch';

interface AgentManagerProps {
  roomId: number;
}

export const AgentManager = memo(({ roomId }: AgentManagerProps) => {
  const { t } = useTranslation('agents');
  const { t: tCommon } = useTranslation('common');
  const { isAdmin } = useAuth();
  const { addToast } = useToast();
  const [roomAgents, setRoomAgents] = useState<Agent[]>([]);
  const [allAgents, setAllAgents] = useState<Agent[]>([]);
  const [showAddAgent, setShowAddAgent] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchRoomAgents = async () => {
      try {
        const data = await api.getRoomAgents(roomId);
        setRoomAgents(data);
      } catch {
        addToast(t('unableToLoadRoom'), 'error');
      }
    };

    const fetchAllAgents = async () => {
      try {
        const data = await api.getAllAgents();
        setAllAgents(data);
      } catch {
        addToast(t('unableToLoadAgents'), 'error');
      }
    };

    if (roomId) {
      fetchRoomAgents();
      fetchAllAgents();
    }
  }, [roomId, addToast, t]);

  const fetchRoomAgents = async () => {
    try {
      const data = await api.getRoomAgents(roomId);
      setRoomAgents(data);
    } catch {
      addToast(t('unableToLoadRoom'), 'error');
    }
  };

  const handleAddAgent = async (agentId: number) => {
    try {
      await api.addAgentToRoom(roomId, agentId);
      fetchRoomAgents();
      addToast(t('agentAdded'), 'success');
    } catch (err) {
      console.error('Failed to add agent to room:', err);
      addToast(t('failedToAddAgent'), 'error');
    }
  };

  const handleRemoveAgent = async (agentId: number) => {
    try {
      await api.removeAgentFromRoom(roomId, agentId);
      fetchRoomAgents();
      addToast(t('agentRemoved'), 'success');
    } catch (err) {
      console.error('Failed to remove agent from room:', err);
      addToast(t('failedToRemoveAgent'), 'error');
    }
  };

  const handleUpdateAgent = async () => {
    if (!selectedAgent) return;

    try {
      await api.updateAgent(selectedAgent.id, {
        in_a_nutshell: selectedAgent.in_a_nutshell,
        characteristics: selectedAgent.characteristics,
        backgrounds: selectedAgent.backgrounds,
        memory: selectedAgent.memory,
        recent_events: selectedAgent.recent_events
      });
      setSelectedAgent(null);
      fetchRoomAgents();
      addToast(t('agentUpdated'), 'success');
    } catch (err) {
      console.error('Failed to update agent:', err);
      addToast(t('failedToUpdateAgent'), 'error');
    }
  };

  // Memoized agent filtering with O(1) lookup using Set (supports Korean consonant search)
  const roomAgentIds = useMemo(() => new Set(roomAgents.map(a => a.id)), [roomAgents]);

  const filteredAvailableAgents = useMemo(() => {
    return allAgents
      .filter(agent => !roomAgentIds.has(agent.id))
      .filter(agent => koreanSearch(agent.name, searchTerm));
  }, [allAgents, roomAgentIds, searchTerm]);

  const filteredRoomAgents = useMemo(() => {
    return roomAgents.filter(agent => koreanSearch(agent.name, searchTerm));
  }, [roomAgents, searchTerm]);

  return (
    <div className="h-full flex flex-col p-4 select-none">
      <div className="flex-shrink-0 mb-4 space-y-3">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <h3 className="font-bold text-lg text-slate-700">{t('roomAgents')}</h3>
          <span className="ml-auto text-sm font-medium text-slate-600">({roomAgents.length})</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={t('searchByName')}
              className="w-full pl-10 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-400"
            />
            <svg className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 104.5 4.5a7.5 7.5 0 0012.15 12.15z" />
            </svg>
          </div>
          <button
            onClick={() => setSearchTerm('')}
            className="px-3 py-2 bg-slate-100 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-200"
          >
            {tCommon('clear')}
          </button>
        </div>
        <button
          onClick={() => setShowAddAgent(!showAddAgent)}
          className="w-full px-4 py-2.5 bg-slate-700 text-white rounded-lg hover:bg-slate-600 text-sm font-medium transition-colors flex items-center justify-center gap-2"
        >
          <span>{showAddAgent ? '−' : '+'}</span>
          {showAddAgent ? tCommon('cancel') : t('addToRoom')}
        </button>
      </div>

      {/* Scrollable content area */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="space-y-2">
        {filteredRoomAgents.length === 0 ? (
          <div className="text-center py-8">
            <svg className="w-12 h-12 mx-auto text-slate-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <p className="text-sm text-slate-500">{t('noAgentsInRoom')}</p>
            <p className="text-xs text-slate-500 mt-1">{t('addOneToStart')}</p>
          </div>
        ) : (
          filteredRoomAgents.map((agent) => (
            <div
              key={agent.id}
              className="group px-4 py-3 bg-white border border-slate-300 rounded-lg text-sm font-medium hover:bg-gradient-to-r hover:from-emerald-50 hover:to-cyan-50 hover:border-emerald-300 hover:shadow-sm transition-all flex items-center gap-3"
            >
              <button
                onClick={() => setSelectedAgent(agent)}
                className="flex items-center gap-3 flex-1 min-w-0"
                title={t('clickToViewEdit')}
              >
                <AgentAvatar agent={agent} size="md" />
                <span className="text-slate-700 group-hover:text-emerald-800 truncate">{agent.name}</span>
              </button>
              {isAdmin && (
                <button
                  onClick={() => {
                    if (confirm(t('removeConfirm', { name: agent.name }))) {
                      handleRemoveAgent(agent.id);
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-red-100 rounded text-red-500 hover:text-red-700"
                  title={t('removeFromRoom')}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          ))
        )}
        </div>

        {showAddAgent && (
        <div className="mt-4 p-4 bg-white rounded-lg border border-slate-300 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <h4 className="text-sm font-semibold text-slate-700">{t('availableAgents')}</h4>
            <span className="text-xs text-slate-600">({filteredAvailableAgents.length})</span>
          </div>
          {filteredAvailableAgents.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-4">
              {t('allAgentsInRoom')}
            </p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {filteredAvailableAgents.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => handleAddAgent(agent.id)}
                  className="w-full px-3 py-2 bg-slate-50 hover:bg-emerald-50 border border-slate-300 hover:border-emerald-300 rounded-lg text-sm font-medium text-slate-700 hover:text-emerald-800 transition-all flex items-center gap-3"
                >
                  <AgentAvatar agent={agent} size="sm" />
                  <span className="truncate">{agent.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {selectedAgent && (
        <div className="mt-4 p-4 bg-white rounded-lg shadow-md border border-slate-300 max-h-[60vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-2">
              <AgentAvatar agent={selectedAgent} size="md" className="w-9 h-9" />
              <h4 className="font-bold text-base text-slate-800 truncate">{selectedAgent.name}</h4>
            </div>
            <button
              onClick={() => setSelectedAgent(null)}
              className="text-slate-500 hover:text-slate-700 p-1 hover:bg-slate-100 rounded transition-colors flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {selectedAgent.config_file && (
            <div className="mb-3">
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t('configFile')}
              </label>
              <div className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-600 break-all">
                {selectedAgent.config_file}
              </div>
            </div>
          )}

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t('inANutshell')}
              </label>
              <textarea
                value={selectedAgent.in_a_nutshell || ''}
                onChange={(e) => setSelectedAgent({ ...selectedAgent, in_a_nutshell: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg h-16 text-xs focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent resize-none"
                placeholder={t('inANutshellPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t('characteristics')}
              </label>
              <textarea
                value={selectedAgent.characteristics || ''}
                onChange={(e) => setSelectedAgent({ ...selectedAgent, characteristics: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg h-16 text-xs focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent resize-none"
                placeholder={t('characteristicsPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t('backgrounds')}
              </label>
              <textarea
                value={selectedAgent.backgrounds || ''}
                onChange={(e) => setSelectedAgent({ ...selectedAgent, backgrounds: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg h-16 text-xs focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent resize-none"
                placeholder={t('backgroundsPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t('memory')}
              </label>
              <textarea
                value={selectedAgent.memory || ''}
                onChange={(e) => setSelectedAgent({ ...selectedAgent, memory: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg h-16 text-xs focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent resize-none"
                placeholder={t('memoryPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t('recentEvents')}
              </label>
              <textarea
                value={selectedAgent.recent_events || ''}
                onChange={(e) => setSelectedAgent({ ...selectedAgent, recent_events: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg h-16 text-xs focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-transparent resize-none"
                placeholder={t('recentEventsPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                {t('systemPrompt')}
              </label>
              <textarea
                value={selectedAgent.system_prompt}
                readOnly
                className="w-full px-3 py-2 border border-slate-200 rounded-lg h-24 text-xs bg-slate-50 text-slate-600 resize-none"
              />
            </div>

            <button
              onClick={handleUpdateAgent}
              className="w-full px-4 py-2 text-sm bg-slate-700 text-white rounded-lg hover:bg-slate-600 font-medium transition-colors shadow-sm"
            >
              {t('updateAgent')}
            </button>
          </div>
        </div>
        )}
      </div>
    </div>
  );
});
