import { useState, FormEvent, KeyboardEvent } from 'react';
import type { ParticipantType } from '../../types';

interface MessageInputProps {
  isConnected: boolean;
  onSendMessage: (message: string, participantType: ParticipantType, characterName?: string) => void;
}

export const MessageInput = ({ isConnected, onSendMessage }: MessageInputProps) => {
  const [inputMessage, setInputMessage] = useState('');
  const [participantType, setParticipantType] = useState<ParticipantType>('user');
  const [characterName, setCharacterName] = useState('');

  // State to toggle the persona menu
  const [showPersonaMenu, setShowPersonaMenu] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    console.log('[MessageInput] handleSubmit called');
    if (inputMessage.trim() && isConnected) {
      console.log('[MessageInput] Calling onSendMessage from handleSubmit');
      onSendMessage(inputMessage, participantType, participantType === 'character' ? characterName : undefined);
      setInputMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Ctrl+Enter
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      console.log('[MessageInput] handleKeyDown - Ctrl+Enter pressed');
      if (inputMessage.trim() && isConnected) {
        console.log('[MessageInput] Calling onSendMessage from handleKeyDown');
        onSendMessage(inputMessage, participantType, participantType === 'character' ? characterName : undefined);
        setInputMessage('');
      }
    }
    // Allow Enter to create line breaks (default behavior)
  };

  // Helper to get the current icon
  const getPersonaIcon = () => {
    if (participantType === 'user') return <span className="font-bold text-sm">U</span>;
    if (participantType === 'situation_builder') return <span className="font-bold text-sm">S</span>;
    return <span className="font-bold text-sm">C</span>;
  };

  // Helper to get persona label
  const getPersonaLabel = () => {
    if (participantType === 'character' && characterName) return characterName;
    if (participantType === 'situation_builder') return 'Situation Builder';
    return 'User';
  };

  return (
    <div className="bg-white/90 backdrop-blur border-t border-slate-100 p-2 sm:p-4 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.02)] z-20">
      {/* Persona Selection Popup (Only visible when toggled) */}
      {showPersonaMenu && (
        <div className="mb-3 p-3 bg-slate-50 rounded-xl border border-slate-200 animate-fadeIn">
          <label className="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wide">Speaking As</label>
          <div className="flex flex-wrap gap-2">
            {(['user', 'situation_builder', 'character'] as ParticipantType[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => {
                  setParticipantType(type);
                  // Don't close immediately if character (needs name input), otherwise close
                  if (type !== 'character') setShowPersonaMenu(false);
                }}
                className={`px-3 py-2 text-sm rounded-lg border transition-all ${
                  participantType === type
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-md'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300'
                }`}
              >
                {type === 'situation_builder' ? 'Builder' : type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
          {participantType === 'character' && (
            <input
              type="text"
              value={characterName}
              onChange={(e) => setCharacterName(e.target.value)}
              placeholder="Character Name"
              className="mt-3 w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
              autoFocus
            />
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        {/* Compact Toggle Button */}
        <button
          type="button"
          onClick={() => setShowPersonaMenu(!showPersonaMenu)}
          className={`flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center transition-all ${
            participantType === 'user' ? 'bg-slate-100 text-slate-600 hover:bg-slate-200' :
            participantType === 'situation_builder' ? 'bg-amber-100 text-amber-700 hover:bg-amber-200' :
            'bg-purple-100 text-purple-700 hover:bg-purple-200'
          }`}
          title={`Change persona (currently: ${getPersonaLabel()})`}
        >
          {getPersonaIcon()}
        </button>

        {/* Streamlined Input Field */}
        <textarea
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Message as ${getPersonaLabel()}...`}
          className="flex-1 bg-slate-50 px-4 py-3 text-base border-0 rounded-2xl focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all resize-none min-h-[44px] sm:min-h-[48px] max-h-[120px] disabled:bg-slate-100 disabled:text-slate-400"
          disabled={!isConnected}
          rows={1}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = 'auto';
            target.style.height = Math.min(target.scrollHeight, 120) + 'px';
          }}
        />

        {/* Icon-Only Send Button (Saves width) */}
        <button
          type="submit"
          disabled={!isConnected || !inputMessage.trim()}
          className="flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 bg-indigo-600 text-white rounded-full flex items-center justify-center hover:bg-indigo-700 active:scale-95 transition-all shadow-md disabled:bg-slate-300 disabled:shadow-none"
        >
          <svg className="w-5 h-5 translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </form>
    </div>
  );
};
