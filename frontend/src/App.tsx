import { useState, useEffect } from 'react';
import { useAgents } from './hooks/useAgents';
import { useRooms } from './hooks/useRooms';
import { useFocusTrap } from './hooks/useFocusTrap';
import { useAuth } from './contexts/AuthContext';
import { MainSidebar } from './components/MainSidebar';
import { ChatRoom } from './components/ChatRoom';
import { AgentProfileModal } from './components/AgentProfileModal';
import { Login } from './components/Login';
import type { Agent } from './types';
import { api } from './utils/api';

function App() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { agents, loading: agentsLoading, createAgent, deleteAgent, refreshAgents } = useAgents();
  const { rooms, loading: roomsLoading, createRoom, deleteRoom, renameRoom, refreshRooms, markRoomAsReadOptimistic } = useRooms();

  // Mobile viewport height fix - sets CSS variable to actual window height
  useEffect(() => {
    const setAppHeight = () => {
      const doc = document.documentElement;
      doc.style.setProperty('--app-height', `${window.innerHeight}px`);
    };

    // Debounce resize events to avoid excessive updates
    let timeoutId: number | undefined;
    const debouncedSetAppHeight = () => {
      clearTimeout(timeoutId);
      timeoutId = window.setTimeout(setAppHeight, 100);
    };

    // Set immediately on mount
    setAppHeight();
    window.addEventListener('resize', debouncedSetAppHeight);

    // Keep orientationchange immediate for better mobile UX
    window.addEventListener('orientationchange', setAppHeight);

    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener('resize', debouncedSetAppHeight);
      window.removeEventListener('orientationchange', setAppHeight);
    };
  }, []);

  const [selectedRoomId, setSelectedRoomId] = useState<number | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const [profileAgent, setProfileAgent] = useState<Agent | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Focus trap for mobile sidebar drawer
  const sidebarRef = useFocusTrap<HTMLDivElement>(isSidebarOpen);

  // Close sidebar when a room/agent is selected on mobile
  useEffect(() => {
    if (selectedRoomId !== null || selectedAgentId !== null) {
      setIsSidebarOpen(false);
    }
  }, [selectedRoomId, selectedAgentId]);

  // Handle Escape key to close sidebar
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isSidebarOpen) {
        setIsSidebarOpen(false);
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isSidebarOpen]);

  const handleSelectAgent = async (agentId: number) => {
    try {
      // Get or create direct room with this agent
      const room = await api.getAgentDirectRoom(agentId);
      setSelectedRoomId(room.id);
      setSelectedAgentId(agentId);
    } catch (err) {
      console.error('Failed to open direct chat:', err);
    }
  };

  const handleSelectRoom = (roomId: number) => {
    setSelectedRoomId(roomId);
    setSelectedAgentId(null);
  };

  const handleDeleteRoom = async (roomId: number) => {
    await deleteRoom(roomId);
    // If we deleted the currently selected room, clear the selection
    if (selectedRoomId === roomId) {
      setSelectedRoomId(null);
      setSelectedAgentId(null);
    }
  };

  const handleViewProfile = (agent: Agent) => {
    setProfileAgent(agent);
  };

  const handleCloseProfile = () => {
    setProfileAgent(null);
  };

  const handleUpdateProfile = () => {
    refreshAgents();
  };

  // Show login screen if not authenticated
  if (authLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-lg md:text-xl text-gray-600">Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  if (agentsLoading || roomsLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-lg md:text-xl text-gray-600">Loading...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex bg-slate-50 relative">
      {/* Subtle dot pattern background */}
      <div className="absolute inset-0 bg-grid-slate opacity-[0.05] pointer-events-none" />
      {/* Mobile Hamburger Menu Button - Fixed position */}
      <button
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-3 bg-indigo-600 text-white rounded-lg shadow-lg hover:bg-indigo-700 transition-colors"
        aria-label="Toggle menu"
      >
        {isSidebarOpen ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        )}
      </button>

      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div
          role="button"
          tabIndex={0}
          aria-label="Close menu"
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-30 transition-opacity duration-300 ease-in-out"
          onClick={() => setIsSidebarOpen(false)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setIsSidebarOpen(false);
            }
          }}
        />
      )}

      {/* Main Sidebar with Tabs - Drawer on mobile */}
      <div
        ref={sidebarRef}
        className={`
          fixed lg:static inset-y-0 left-0 z-40
          transform transition-transform duration-300 ease-in-out
          ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <MainSidebar
          rooms={rooms}
          selectedRoomId={selectedRoomId}
          onSelectRoom={handleSelectRoom}
          onCreateRoom={createRoom}
          onDeleteRoom={handleDeleteRoom}
          agents={agents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={handleSelectAgent}
          onCreateAgent={createAgent}
          onDeleteAgent={deleteAgent}
          onViewProfile={handleViewProfile}
        />
      </div>

      {/* Main Chat Area */}
      <ChatRoom
        roomId={selectedRoomId}
        onRoomRead={refreshRooms}
        onMarkRoomAsRead={markRoomAsReadOptimistic}
        onRenameRoom={renameRoom}
      />

      {/* Agent Profile Modal */}
      {profileAgent && (
        <AgentProfileModal
          agent={profileAgent}
          onClose={handleCloseProfile}
          onUpdate={handleUpdateProfile}
        />
      )}
    </div>
  );
}

export default App;
