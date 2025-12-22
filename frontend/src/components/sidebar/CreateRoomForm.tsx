import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Room } from '../../types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface CreateRoomFormProps {
  onCreateRoom: (name: string) => Promise<Room>;
  onClose: () => void;
}

export const CreateRoomForm = ({ onCreateRoom, onClose }: CreateRoomFormProps) => {
  const { t } = useTranslation('rooms');
  const [newRoomName, setNewRoomName] = useState('');
  const [roomError, setRoomError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newRoomName.trim()) {
      try {
        setRoomError(null);
        await onCreateRoom(newRoomName);
        setNewRoomName('');
        onClose();
      } catch (err) {
        setRoomError(err instanceof Error ? err.message : t('failedToCreateRoom'));
      }
    }
  };

  return (
    <div className="p-3 border-b border-border bg-muted/50">
      <form onSubmit={handleSubmit} className="space-y-3">
        <Input
          type="text"
          value={newRoomName}
          onChange={(e) => {
            setNewRoomName(e.target.value);
            setRoomError(null);
          }}
          placeholder={t('enterRoomName')}
          autoFocus
        />
        {roomError && (
          <div className="text-destructive text-xs sm:text-sm bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
            {roomError}
          </div>
        )}
        <Button type="submit" className="w-full">
          {t('createRoom')}
        </Button>
      </form>
    </div>
  );
};
