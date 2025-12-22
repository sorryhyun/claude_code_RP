import { useState } from 'react';
import { useToast } from '../../../contexts/ToastContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface RoomTitleEditorProps {
  roomName: string;
  isAdmin: boolean;
  onRenameRoom: (name: string) => Promise<void>;
}

export const RoomTitleEditor = ({ roomName, isAdmin, onRenameRoom }: RoomTitleEditorProps) => {
  const { addToast } = useToast();
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const [isSavingName, setIsSavingName] = useState(false);

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
    <>
      {isEditingName ? (
        <div className="flex items-center gap-2 flex-wrap">
          <Input
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            maxLength={60}
            className="w-full sm:w-auto sm:max-w-xs"
          />
          <Button
            onClick={handleRenameRoom}
            disabled={isSavingName}
            size="sm"
          >
            {isSavingName ? 'Saving…' : 'Save'}
          </Button>
          <Button
            onClick={() => setIsEditingName(false)}
            disabled={isSavingName}
            variant="secondary"
            size="sm"
          >
            Cancel
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-1 sm:gap-2 min-w-0">
          <h2 className="text-base sm:text-lg lg:text-xl font-bold text-slate-800 truncate min-w-0">{roomName}</h2>
          {isAdmin && (
            <button
              onClick={startEditingName}
              className="btn-icon-mobile rounded bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors flex-shrink-0"
              title="Rename chatroom"
            >
              <svg className="icon-mobile" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L7.5 19.036H4v-3.572L16.732 3.732z" />
              </svg>
            </button>
          )}
        </div>
      )}
    </>
  );
};
