import { useState } from 'react';
import type { Agent, AgentCreate, RoomSummary, Room } from '../types';
import { useAuth } from '../contexts/AuthContext';
import { useFetchAgentConfigs } from '../hooks/useFetchAgentConfigs';
import { CreateRoomForm } from './sidebar/CreateRoomForm';
import { RoomListPanel } from './sidebar/RoomListPanel';
import { CreateAgentForm } from './sidebar/CreateAgentForm';
import { AgentListPanel } from './sidebar/AgentListPanel';

interface MainSidebarProps {
  // Rooms
  rooms: RoomSummary[];
  selectedRoomId: number | null;
  onSelectRoom: (roomId: number) => void;
  onCreateRoom: (name: string) => Promise<Room>;
  onDeleteRoom: (roomId: number) => Promise<void>;

  // Agents
  agents: Agent[];
  selectedAgentId: number | null;
  onSelectAgent: (agentId: number) => void;
  onCreateAgent: (agentData: AgentCreate) => Promise<Agent>;
  onDeleteAgent: (agentId: number) => Promise<void>;
  onViewProfile: (agent: Agent) => void;
}

export const MainSidebar = ({
  rooms,
  selectedRoomId,
  onSelectRoom,
  onCreateRoom,
  onDeleteRoom,
  agents,
  selectedAgentId,
  onSelectAgent,
  onCreateAgent,
  onDeleteAgent,
  onViewProfile,
}: MainSidebarProps) => {
  const { logout } = useAuth();
  const [activeTab, setActiveTab] = useState<'rooms' | 'agents'>('rooms');
  const [showRoomForm, setShowRoomForm] = useState(false);
  const [showAgentForm, setShowAgentForm] = useState(false);
  const [agentSearchQuery, setAgentSearchQuery] = useState('');
  const { configs: availableConfigs, fetchConfigs } = useFetchAgentConfigs();

  const handleShowAgentForm = () => {
    if (!showAgentForm) {
      fetchConfigs();
    }
    setShowAgentForm(!showAgentForm);
  };

  // Filter and sort agents
  const filteredAndSortedAgents = agents
    .filter(agent =>
      agent.name.toLowerCase().includes(agentSearchQuery.toLowerCase())
    )
    .sort((a, b) =>
      a.name.localeCompare(b.name, 'ko-KR', { sensitivity: 'base' })
    );

  return (
    <div className="w-80 sm:w-80 bg-white shadow-xl flex flex-col border-r border-slate-200 h-full">
      {/* Header */}
      <div className="pl-20 pr-4 py-4 sm:p-6 border-b border-slate-200 bg-gradient-to-r from-indigo-600 to-purple-600">
        <h2 className="text-xl sm:text-2xl font-bold text-white mb-1">Claude Code RP</h2>
        <p className="text-indigo-100 text-xs sm:text-sm">Multi-agent role play</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('rooms')}
          className={`flex-1 px-3 sm:px-4 py-2.5 sm:py-3 font-medium text-xs sm:text-sm transition-all ${
            activeTab === 'rooms'
              ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50'
              : 'text-slate-600 hover:bg-slate-50'
          }`}
        >
          Chatrooms
        </button>
        <button
          onClick={() => setActiveTab('agents')}
          className={`flex-1 px-3 sm:px-4 py-2.5 sm:py-3 font-medium text-xs sm:text-sm transition-all ${
            activeTab === 'agents'
              ? 'text-emerald-600 border-b-2 border-emerald-600 bg-emerald-50'
              : 'text-slate-600 hover:bg-slate-50'
          }`}
        >
          Agent List
        </button>
      </div>

      {/* Rooms Tab Content */}
      {activeTab === 'rooms' && (
        <>
          {/* New Room Button (Desktop only) */}
          <div className="hidden lg:block p-3 sm:p-4 border-b border-slate-200">
            <button
              onClick={() => setShowRoomForm(!showRoomForm)}
              className="w-full px-3 sm:px-4 py-2.5 sm:py-3 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white rounded-lg font-medium transition-colors shadow-sm hover:shadow-md flex items-center justify-center gap-2 text-sm sm:text-base touch-manipulation min-h-[44px]"
            >
              <span className="text-xl">+</span>
              {showRoomForm ? 'Cancel' : 'New Chatroom'}
            </button>
          </div>

          {/* Create Room Form */}
          {showRoomForm && (
            <CreateRoomForm
              onCreateRoom={onCreateRoom}
              onClose={() => setShowRoomForm(false)}
            />
          )}

          {/* Rooms List with FAB Container */}
          <div className="relative flex-1 min-h-0">
            <RoomListPanel
              rooms={rooms}
              selectedRoomId={selectedRoomId}
              onSelectRoom={onSelectRoom}
              onDeleteRoom={onDeleteRoom}
            />

            {/* Floating Action Button (Mobile only) */}
            <button
              onClick={() => setShowRoomForm(!showRoomForm)}
              className="lg:hidden fixed bottom-6 right-6 w-14 h-14 bg-indigo-600 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-indigo-700 active:scale-95 transition-transform z-30"
              title={showRoomForm ? 'Cancel' : 'New Chatroom'}
            >
              {showRoomForm ? (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              )}
            </button>
          </div>
        </>
      )}

      {/* Agents Tab Content */}
      {activeTab === 'agents' && (
        <>
          {/* New Agent Button (Desktop only) */}
          <div className="hidden lg:block p-3 sm:p-4 border-b border-slate-200">
            <button
              onClick={handleShowAgentForm}
              className="w-full px-3 sm:px-4 py-2.5 sm:py-3 bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white rounded-lg font-medium transition-colors shadow-sm hover:shadow-md flex items-center justify-center gap-2 text-sm sm:text-base touch-manipulation min-h-[44px]"
            >
              <span className="text-xl">+</span>
              {showAgentForm ? 'Cancel' : 'New Agent'}
            </button>
          </div>

          {/* Create Agent Form */}
          {showAgentForm && (
            <CreateAgentForm
              availableConfigs={availableConfigs}
              onCreateAgent={onCreateAgent}
              onClose={() => setShowAgentForm(false)}
            />
          )}

          {/* Search Agents */}
          <div className="p-3 sm:p-4 border-b border-slate-200">
            <div className="relative">
              <input
                type="text"
                value={agentSearchQuery}
                onChange={(e) => setAgentSearchQuery(e.target.value)}
                placeholder="Search agents..."
                className="w-full px-3 sm:px-4 py-2 sm:py-2.5 pl-10 sm:pl-11 bg-slate-50 border border-slate-200 rounded-lg text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
              />
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              {agentSearchQuery && (
                <button
                  onClick={() => setAgentSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  title="Clear search"
                >
                  <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Agents List with FAB Container */}
          <div className="relative flex-1 min-h-0">
            <AgentListPanel
              agents={filteredAndSortedAgents}
              selectedAgentId={selectedAgentId}
              onSelectAgent={onSelectAgent}
              onDeleteAgent={onDeleteAgent}
              onViewProfile={onViewProfile}
            />

            {/* Floating Action Button (Mobile only) */}
            <button
              onClick={handleShowAgentForm}
              className="lg:hidden fixed bottom-6 right-6 w-14 h-14 bg-emerald-600 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-emerald-700 active:scale-95 transition-transform z-30"
              title={showAgentForm ? 'Cancel' : 'New Agent'}
            >
              {showAgentForm ? (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              )}
            </button>
          </div>
        </>
      )}

      {/* Logout Button */}
      <div className="mt-auto p-3 sm:p-4 border-t border-slate-200">
        <button
          onClick={() => {
            if (confirm('Are you sure you want to logout?')) {
              logout();
            }
          }}
          className="w-full px-3 sm:px-4 py-2.5 sm:py-3 bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 rounded-lg font-medium transition-colors text-sm sm:text-base touch-manipulation min-h-[44px] flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Logout
        </button>
      </div>
    </div>
  );
};
