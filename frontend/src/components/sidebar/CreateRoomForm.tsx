import { useState } from 'react';
import type { Room } from '../../types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface CreateRoomFormProps {
  onCreateRoom: (name: string) => Promise<Room>;
  onClose: () => void;
}

export const CreateRoomForm = ({ onCreateRoom, onClose }: CreateRoomFormProps) => {
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
        setRoomError(err instanceof Error ? err.message : 'Failed to create room');
      }
    }
  };

  return (
    <div className="p-3 border-b border-sidebar-border bg-sidebar-accent/50">
      <form onSubmit={handleSubmit} className="space-y-3">
        <Input
          type="text"
          value={newRoomName}
          onChange={(e) => {
            setNewRoomName(e.target.value);
            setRoomError(null);
          }}
          placeholder="Enter room name..."
          className="bg-sidebar-background border-sidebar-border"
          autoFocus
        />
        {roomError && (
          <div className="text-destructive text-xs bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
            {roomError}
          </div>
        )}
        <Button type="submit" className="w-full bg-accent hover:bg-accent/90">
          Create Room
        </Button>
      </form>
    </div>
  );
};
