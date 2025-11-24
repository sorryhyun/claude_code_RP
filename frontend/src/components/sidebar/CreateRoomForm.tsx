import { useState } from 'react';
import type { Room } from '../../types';

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
    <div className="p-3 sm:p-4 border-b border-slate-200 bg-slate-50">
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="text"
          value={newRoomName}
          onChange={(e) => {
            setNewRoomName(e.target.value);
            setRoomError(null);
          }}
          placeholder="Enter room name..."
          className="w-full px-3 sm:px-4 py-2.5 sm:py-3 text-sm sm:text-base border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent min-h-[44px]"
          autoFocus
        />
        {roomError && (
          <div className="text-red-600 text-xs sm:text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {roomError}
          </div>
        )}
        <button
          type="submit"
          className="w-full px-3 sm:px-4 py-2.5 sm:py-3 bg-green-600 hover:bg-green-700 active:bg-green-800 text-white rounded-lg font-medium transition-colors text-sm sm:text-base min-h-[44px]"
        >
          Create Room
        </button>
      </form>
    </div>
  );
};
