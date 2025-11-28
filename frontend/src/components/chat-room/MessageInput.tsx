import { useState, FormEvent, KeyboardEvent } from 'react';
import { Send, User, Sparkles, UserCircle } from 'lucide-react';
import type { ParticipantType } from '../../types';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';

interface MessageInputProps {
  isConnected: boolean;
  onSendMessage: (message: string, participantType: ParticipantType, characterName?: string) => void;
}

export const MessageInput = ({ isConnected, onSendMessage }: MessageInputProps) => {
  const [inputMessage, setInputMessage] = useState('');
  const [participantType, setParticipantType] = useState<ParticipantType>('user');
  const [characterName, setCharacterName] = useState('');
  const [showCharacterInput, setShowCharacterInput] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (inputMessage.trim() && isConnected) {
      onSendMessage(inputMessage, participantType, participantType === 'character' ? characterName : undefined);
      setInputMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      if (inputMessage.trim() && isConnected) {
        onSendMessage(inputMessage, participantType, participantType === 'character' ? characterName : undefined);
        setInputMessage('');
      }
    }
  };

  const getPersonaIcon = () => {
    if (participantType === 'user') return <User className="w-4 h-4" />;
    if (participantType === 'situation_builder') return <Sparkles className="w-4 h-4" />;
    return <UserCircle className="w-4 h-4" />;
  };

  const getPersonaLabel = () => {
    if (participantType === 'character' && characterName) return characterName;
    if (participantType === 'situation_builder') return 'Situation Builder';
    return 'User';
  };

  const handlePersonaChange = (type: ParticipantType) => {
    setParticipantType(type);
    if (type === 'character') {
      setShowCharacterInput(true);
    } else {
      setShowCharacterInput(false);
    }
  };

  return (
    <div className="bg-background border-t border-border p-3 sm:p-4">
      {/* Character name input */}
      {showCharacterInput && (
        <div className="mb-3 flex items-center gap-2 animate-fadeIn">
          <Input
            type="text"
            value={characterName}
            onChange={(e) => setCharacterName(e.target.value)}
            placeholder="Character name..."
            className="flex-1 h-9"
            autoFocus
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setShowCharacterInput(false);
              if (!characterName) setParticipantType('user');
            }}
          >
            Done
          </Button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        {/* Persona selector */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className={cn(
                'flex-shrink-0 w-10 h-10 sm:w-11 sm:h-11 rounded-full',
                participantType === 'user' && 'text-primary hover:text-primary hover:bg-primary/10',
                participantType === 'situation_builder' && 'text-amber-500 hover:text-amber-500 hover:bg-amber-500/10',
                participantType === 'character' && 'text-purple-500 hover:text-purple-500 hover:bg-purple-500/10'
              )}
              title={`Speaking as ${getPersonaLabel()}`}
            >
              {getPersonaIcon()}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            <DropdownMenuItem
              onClick={() => handlePersonaChange('user')}
              className={cn(participantType === 'user' && 'bg-primary/10 text-primary')}
            >
              <User className="w-4 h-4 mr-2" />
              User
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => handlePersonaChange('situation_builder')}
              className={cn(participantType === 'situation_builder' && 'bg-amber-500/10 text-amber-500')}
            >
              <Sparkles className="w-4 h-4 mr-2" />
              Situation Builder
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => handlePersonaChange('character')}
              className={cn(participantType === 'character' && 'bg-purple-500/10 text-purple-500')}
            >
              <UserCircle className="w-4 h-4 mr-2" />
              Character
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Input field */}
        <div className="flex-1 bg-muted rounded-lg">
          <Textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message as ${getPersonaLabel()}...`}
            className={cn(
              'min-h-[44px] max-h-[200px] resize-none border-0 bg-transparent',
              'focus-visible:ring-0 focus-visible:ring-offset-0',
              'py-3 px-4'
            )}
            disabled={!isConnected}
            rows={1}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = Math.min(target.scrollHeight, 200) + 'px';
            }}
          />
        </div>

        {/* Send button */}
        <Button
          type="submit"
          size="icon"
          disabled={!isConnected || !inputMessage.trim()}
          className="flex-shrink-0 w-10 h-10 sm:w-11 sm:h-11 rounded-full"
        >
          <Send className="w-4 h-4" />
        </Button>
      </form>
    </div>
  );
};
