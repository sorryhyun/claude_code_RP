import { useState } from 'react';
import type { Message } from '../../../types';
import { useToast } from '../../../contexts/ToastContext';

interface ConversationCopyButtonProps {
  roomName: string;
  messages: Message[];
}

export const ConversationCopyButton = ({ roomName, messages }: ConversationCopyButtonProps) => {
  const { addToast } = useToast();
  const [copiedType, setCopiedType] = useState<'normal' | 'thinking' | null>(null);

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

  const copyConversation = async (includeThinking: boolean) => {
    try {
      // Filter out typing/chatting indicators and format messages
      const realMessages = messages.filter(m => !m.is_typing && !m.is_chatting);

      if (realMessages.length === 0) {
        addToast('No messages to copy yet', 'info');
        return;
      }

      // Format as readable transcript
      let transcript = `=== ${roomName} ===\n`;
      transcript += `Conversation Transcript${includeThinking ? ' (with thinking)' : ''}\n`;
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

        // Include thinking if requested and available
        if (includeThinking && message.thinking) {
          transcript += `<thinking>\n${message.thinking}\n</thinking>\n\n`;
        }

        transcript += `${message.content}\n\n`;
      });

      transcript += `${'='.repeat(60)}\n`;
      transcript += `End of conversation\n`;

      await navigator.clipboard.writeText(transcript);
      setCopiedType(includeThinking ? 'thinking' : 'normal');
      addToast(includeThinking ? 'Copied with thinking' : 'Copied conversation', 'success');
      setTimeout(() => setCopiedType(null), 2000);
    } catch (err) {
      console.error('Failed to copy conversation:', err);
      addToast('Failed to copy conversation', 'error');
    }
  };

  return (
    <div className="flex items-center gap-1">
      {/* Copy conversation button */}
      <button
        onClick={() => copyConversation(false)}
        className="btn-icon-mobile rounded bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
        title="Copy conversation"
      >
        {copiedType === 'normal' ? (
          <svg className="icon-mobile" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <svg className="icon-mobile" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        )}
      </button>

      {/* Copy with thinking button */}
      <button
        onClick={() => copyConversation(true)}
        className="btn-icon-mobile rounded bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors relative"
        title="Copy with thinking"
      >
        {copiedType === 'thinking' ? (
          <svg className="icon-mobile" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <>
            <svg className="icon-mobile" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            {/* T badge */}
            <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-slate-600 text-white text-[8px] font-bold rounded-sm flex items-center justify-center leading-none">
              T
            </span>
          </>
        )}
      </button>
    </div>
  );
};
