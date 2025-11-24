import { useState } from 'react';
import type { Room, Message } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';

interface ChatHeaderProps {
  roomName: string;
  roomData: Room | null;
  isConnected: boolean;
  messages: Message[];
  onRefreshMessages: () => Promise<void>;
  isRefreshing: boolean;
  onPauseToggle: () => void;
  onLimitUpdate: (limit: number | null) => void;
  onClearMessages: () => void;
  onRenameRoom: (name: string) => Promise<void>;
  onShowAgentManager: () => void;
  isAgentManagerCollapsed: boolean;
  onToggleAgentManagerCollapse: () => void;
}

export const ChatHeader = ({
  roomName,
  roomData,
  isConnected,
  messages,
  onRefreshMessages,
  isRefreshing,
  onPauseToggle,
  onLimitUpdate,
  onClearMessages,
  onRenameRoom,
  onShowAgentManager,
  isAgentManagerCollapsed,
  onToggleAgentManagerCollapse,
}: ChatHeaderProps) => {
  const { isAdmin } = useAuth();
  const { addToast } = useToast();
  const [isEditingLimit, setIsEditingLimit] = useState(false);
  const [limitInput, setLimitInput] = useState('');
  const [copiedConversation, setCopiedConversation] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const [isSavingName, setIsSavingName] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const startEditingLimit = () => {
    setLimitInput(roomData?.max_interactions?.toString() || '');
    setIsEditingLimit(true);
  };

  const handleLimitUpdate = () => {
    const newLimit = limitInput === '' ? null : parseInt(limitInput, 10);
    if (limitInput !== '' && (isNaN(newLimit as number) || (newLimit as number) < 1)) {
      addToast('Please enter a valid positive number or leave empty for unlimited', 'error');
      return;
    }
    onLimitUpdate(newLimit);
    addToast('Interaction limit updated', 'success');
    setIsEditingLimit(false);
    setLimitInput('');
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  const copyConversation = async () => {
    try {
      // Filter out typing/chatting indicators and format messages
      const realMessages = messages.filter(m => !m.is_typing && !m.is_chatting);

      if (realMessages.length === 0) {
        addToast('No messages to copy yet', 'info');
        return;
      }

      // Format as readable transcript
      let transcript = `=== ${roomName} ===\n`;
      transcript += `Conversation Transcript\n`;
      transcript += `Total Messages: ${realMessages.length}\n`;
      transcript += `Exported: ${new Date().toLocaleString()}\n`;
      transcript += `${'='.repeat(60)}\n\n`;

      realMessages.forEach((message) => {
        const timestamp = formatTimestamp(message.timestamp);
        let sender = 'Unknown';

        if (message.role === 'user') {
          if (message.participant_type === 'character' && message.participant_name) {
            sender = message.participant_name;
          } else if (message.participant_type === 'situation_builder') {
            sender = 'Situation Builder';
          } else {
            sender = 'User';
          }
        } else if (message.agent_name) {
          sender = message.agent_name;
        }

        transcript += `[${timestamp}] ${sender}:\n`;
        transcript += `${message.content}\n\n`;
      });

      transcript += `${'='.repeat(60)}\n`;
      transcript += `End of conversation\n`;

      await navigator.clipboard.writeText(transcript);
      setCopiedConversation(true);
      setTimeout(() => setCopiedConversation(false), 2000);
    } catch (err) {
      console.error('Failed to copy conversation:', err);
      addToast('Failed to copy conversation', 'error');
    }
  };

  const startEditingName = () => {
    setNameInput(roomName);
    setIsEditingName(true);
  };

  const handleRenameRoom = async () => {
    if (!nameInput.trim()) {
      addToast('Room name cannot be empty', 'error');
      return;
    }

    try {
      setIsSavingName(true);
      await onRenameRoom(nameInput.trim());
      setIsEditingName(false);
      setNameInput('');
      addToast('Room name updated', 'success');
    } catch (err) {
      console.error('Failed to rename room:', err);
      addToast('Failed to rename room', 'error');
    } finally {
      setIsSavingName(false);
    }
  };

  return (
    <div className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200/50 supports-[backdrop-filter]:bg-white/60 pl-20 pr-3 sm:pr-4 lg:px-6 py-3 sm:py-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            {isEditingName ? (
              <div className="flex items-center gap-2 flex-wrap">
                <input
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  maxLength={60}
                />
                <button
                  onClick={handleRenameRoom}
                  disabled={isSavingName}
                  className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {isSavingName ? 'Saving…' : 'Save'}
                </button>
                <button
                  onClick={() => setIsEditingName(false)}
                  disabled={isSavingName}
                  className="px-3 py-1.5 bg-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-300 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-slate-800 truncate">{roomName}</h2>
                {isAdmin && (
                  <button
                    onClick={startEditingName}
                    className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
                    title="Rename chatroom"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L7.5 19.036H4v-3.572L16.732 3.732z" />
                    </svg>
                  </button>
                )}
              </div>
            )}

            {/* Copy Conversation Button */}
            <button
              onClick={copyConversation}
              className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
              title="Copy conversation transcript"
            >
              {copiedConversation ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              )}
            </button>

            {roomName.startsWith('Direct:') && (
              <span className="px-2 py-0.5 sm:py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full whitespace-nowrap">
                Direct Chat
              </span>
            )}
            {roomData?.is_paused && (
              <span className="px-2 py-0.5 sm:py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded-full whitespace-nowrap">
                Paused
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <p className="text-xs sm:text-sm text-slate-500">
              {isConnected ? 'Connected' : 'Disconnected'}
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Agents Button (Mobile/Tablet Only) */}
          <button
            onClick={onShowAgentManager}
            className="xl:hidden p-2 text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
            title="Show agents"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </button>

          {/* Collapse/Expand Agent Panel Button (Desktop only) */}
          <button
            onClick={onToggleAgentManagerCollapse}
            className="hidden xl:flex p-2 text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
            title={isAgentManagerCollapsed ? 'Show agent panel' : 'Hide agent panel'}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isAgentManagerCollapsed ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              )}
            </svg>
          </button>

          {/* Pause/Resume Button (Primary Action) */}
          <button
            onClick={onPauseToggle}
            className={`flex items-center gap-2 px-4 py-2 rounded-full font-medium transition-colors text-sm ${
              roomData?.is_paused
                ? 'bg-green-600 hover:bg-green-700 active:bg-green-800 text-white'
                : 'bg-orange-600 hover:bg-orange-700 active:bg-orange-800 text-white'
            }`}
            title={roomData?.is_paused ? 'Resume conversation' : 'Pause conversation'}
          >
            {roomData?.is_paused ? (
              <>
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
                <span className="hidden sm:inline">Resume</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                </svg>
                <span className="hidden sm:inline">Pause</span>
              </>
            )}
          </button>

          {/* Clear History Button */}
          {isAdmin && (
            <button
              onClick={() => { onClearMessages(); setIsMenuOpen(false); }}
              className="flex items-center gap-2 px-4 py-2 rounded-full font-medium transition-colors text-sm bg-red-600 hover:bg-red-700 active:bg-red-800 text-white"
              title="Clear conversation history"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              <span className="hidden sm:inline">Clear</span>
            </button>
          )}

          {/* Kebab Menu Button */}
          <div className="relative">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="p-2 text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
              title="More options"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>

            {/* The Dropdown Menu */}
            {isMenuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setIsMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-100 z-20 py-2 animate-fadeIn">
                  {/* Limit Setting - Inline or Popup */}
                  {isEditingLimit ? (
                    <div className="px-4 py-3 border-b border-slate-100">
                      <label className="block text-xs font-medium text-slate-500 mb-2">Message Limit</label>
                      <div className="flex gap-2">
                        <input
                          type="number"
                          value={limitInput}
                          onChange={(e) => setLimitInput(e.target.value)}
                          placeholder="∞"
                          className="flex-1 px-2 py-1.5 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          min="1"
                          autoFocus
                        />
                        <button
                          onClick={handleLimitUpdate}
                          className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => setIsEditingLimit(false)}
                          className="px-3 py-1.5 bg-slate-200 text-slate-700 text-sm rounded hover:bg-slate-300"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => { startEditingLimit(); }}
                      className="w-full text-left px-4 py-3 text-sm hover:bg-slate-50 flex items-center gap-3 text-slate-700"
                    >
                      <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                      </svg>
                      <span className="flex-1">Message Limit</span>
                      <span className="text-xs font-bold text-indigo-600">
                        {roomData?.max_interactions ?? '∞'}
                      </span>
                    </button>
                  )}

                  <button
                    onClick={() => { onRefreshMessages(); setIsMenuOpen(false); }}
                    disabled={isRefreshing}
                    className="w-full text-left px-4 py-3 text-sm hover:bg-slate-50 flex items-center gap-3 text-slate-700 disabled:opacity-50"
                  >
                    <svg className={`w-4 h-4 text-slate-400 ${isRefreshing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Refresh Messages
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
