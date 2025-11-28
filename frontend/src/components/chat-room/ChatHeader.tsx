import { useState } from 'react';
import {
  Hash,
  Copy,
  Check,
  Pencil,
  Users,
  ChevronLeft,
  ChevronRight,
  Play,
  Pause,
  Trash2,
  MoreVertical,
  RefreshCw,
  Settings,
} from 'lucide-react';
import type { Room, Message } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

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
      const realMessages = messages.filter(m => !m.is_typing && !m.is_chatting);

      if (realMessages.length === 0) {
        addToast('No messages to copy yet', 'info');
        return;
      }

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
    <TooltipProvider>
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-border pl-16 pr-3 sm:px-4 lg:px-6 py-3">
        <div className="flex items-center justify-between gap-3">
          {/* Left side: Room info */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              {isEditingName ? (
                <div className="flex items-center gap-2 flex-wrap">
                  <Input
                    value={nameInput}
                    onChange={(e) => setNameInput(e.target.value)}
                    className="h-8 w-48"
                    maxLength={60}
                    autoFocus
                  />
                  <Button
                    onClick={handleRenameRoom}
                    disabled={isSavingName}
                    size="sm"
                  >
                    {isSavingName ? 'Saving...' : 'Save'}
                  </Button>
                  <Button
                    onClick={() => setIsEditingName(false)}
                    disabled={isSavingName}
                    variant="ghost"
                    size="sm"
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <>
                  <Hash className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                  <h2 className="text-base sm:text-lg font-semibold text-foreground truncate">
                    {roomName}
                  </h2>
                  {isAdmin && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          onClick={startEditingName}
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Rename room</TooltipContent>
                    </Tooltip>
                  )}
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        onClick={copyConversation}
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                      >
                        {copiedConversation ? (
                          <Check className="w-3.5 h-3.5 text-accent" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Copy transcript</TooltipContent>
                  </Tooltip>
                </>
              )}

              {/* Badges */}
              {roomName.startsWith('Direct:') && (
                <Badge variant="secondary" className="bg-accent/20 text-accent-foreground">
                  Direct
                </Badge>
              )}
              {roomData?.is_paused && (
                <Badge variant="secondary" className="bg-destructive/20 text-destructive">
                  Paused
                </Badge>
              )}
            </div>

            {/* Connection status */}
            <div className="flex items-center gap-2 mt-1">
              <span className={cn(
                'w-2 h-2 rounded-full',
                isConnected ? 'bg-accent' : 'bg-destructive'
              )} />
              <span className="text-xs text-muted-foreground">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>

          {/* Right side: Actions */}
          <div className="flex items-center gap-1">
            {/* Agents button (mobile/tablet) */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={onShowAgentManager}
                  variant="ghost"
                  size="icon"
                  className="xl:hidden"
                >
                  <Users className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Show agents</TooltipContent>
            </Tooltip>

            {/* Collapse/expand agent panel (desktop) */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={onToggleAgentManagerCollapse}
                  variant="ghost"
                  size="icon"
                  className="hidden xl:flex"
                >
                  {isAgentManagerCollapsed ? (
                    <ChevronLeft className="w-5 h-5" />
                  ) : (
                    <ChevronRight className="w-5 h-5" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {isAgentManagerCollapsed ? 'Show agent panel' : 'Hide agent panel'}
              </TooltipContent>
            </Tooltip>

            {/* Pause/Resume */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={onPauseToggle}
                  variant={roomData?.is_paused ? 'default' : 'secondary'}
                  size="sm"
                  className={cn(
                    'gap-1.5',
                    roomData?.is_paused
                      ? 'bg-accent hover:bg-accent/90'
                      : 'bg-destructive/90 hover:bg-destructive text-destructive-foreground'
                  )}
                >
                  {roomData?.is_paused ? (
                    <>
                      <Play className="w-4 h-4" />
                      <span className="hidden sm:inline">Resume</span>
                    </>
                  ) : (
                    <>
                      <Pause className="w-4 h-4" />
                      <span className="hidden sm:inline">Pause</span>
                    </>
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {roomData?.is_paused ? 'Resume conversation' : 'Pause conversation'}
              </TooltipContent>
            </Tooltip>

            {/* Clear history (admin only) */}
            {isAdmin && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={onClearMessages}
                    variant="destructive"
                    size="sm"
                    className="gap-1.5"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span className="hidden sm:inline">Clear</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Clear conversation</TooltipContent>
              </Tooltip>
            )}

            {/* More options dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreVertical className="w-5 h-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                {isEditingLimit ? (
                  <div className="px-3 py-2">
                    <label className="block text-xs font-medium text-muted-foreground mb-2">
                      Message Limit
                    </label>
                    <div className="flex gap-2">
                      <Input
                        type="number"
                        value={limitInput}
                        onChange={(e) => setLimitInput(e.target.value)}
                        placeholder="∞"
                        className="h-8"
                        min="1"
                        autoFocus
                      />
                      <Button size="sm" onClick={handleLimitUpdate}>
                        <Check className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setIsEditingLimit(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <DropdownMenuItem onClick={startEditingLimit}>
                    <Settings className="w-4 h-4 mr-2" />
                    <span className="flex-1">Message Limit</span>
                    <span className="text-xs font-semibold text-primary">
                      {roomData?.max_interactions ?? '∞'}
                    </span>
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={onRefreshMessages}
                  disabled={isRefreshing}
                >
                  <RefreshCw className={cn('w-4 h-4 mr-2', isRefreshing && 'animate-spin')} />
                  Refresh Messages
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
};
