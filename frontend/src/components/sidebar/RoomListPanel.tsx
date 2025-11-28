import { useState } from 'react';
import { Hash, Trash2, Loader2 } from 'lucide-react';
import type { RoomSummary } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface RoomListPanelProps {
  rooms: RoomSummary[];
  selectedRoomId: number | null;
  onSelectRoom: (roomId: number) => void;
  onDeleteRoom: (roomId: number) => Promise<void>;
}

export const RoomListPanel = ({
  rooms,
  selectedRoomId,
  onSelectRoom,
  onDeleteRoom,
}: RoomListPanelProps) => {
  const { isAdmin } = useAuth();
  const [deletingRoomId, setDeletingRoomId] = useState<number | null>(null);

  return (
    <div className="p-2 space-y-0.5">
      {rooms.length === 0 ? (
        <div className="text-center text-muted-foreground mt-8 px-4">
          <p className="text-sm">No rooms yet</p>
          <p className="text-xs mt-1">Create one or select an agent!</p>
        </div>
      ) : (
        rooms.map((room) => (
          <div
            key={room.id}
            onClick={() => onSelectRoom(room.id)}
            className={cn(
              'group relative flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors',
              selectedRoomId === room.id
                ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
            )}
          >
            <Hash className={cn(
              'w-4 h-4 flex-shrink-0',
              selectedRoomId === room.id ? 'text-sidebar-foreground' : 'text-muted-foreground'
            )} />

            <span className={cn(
              'flex-1 truncate text-sm',
              room.has_unread && 'font-semibold text-sidebar-foreground',
              selectedRoomId === room.id && 'text-sidebar-foreground'
            )}>
              {room.name}
            </span>

            {room.has_unread && (
              <span className="w-2 h-2 rounded-full bg-destructive flex-shrink-0" />
            )}

            {isAdmin && (
              <Button
                onClick={async (e) => {
                  e.stopPropagation();
                  if (confirm(`Delete room "${room.name}"?`)) {
                    setDeletingRoomId(room.id);
                    try {
                      await onDeleteRoom(room.id);
                    } catch (err) {
                      alert(`Failed to delete room: ${err instanceof Error ? err.message : 'Unknown error'}`);
                    } finally {
                      setDeletingRoomId(null);
                    }
                  }
                }}
                disabled={deletingRoomId === room.id}
                variant="ghost"
                size="icon"
                className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 text-muted-foreground hover:text-destructive"
              >
                {deletingRoomId === room.id ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
              </Button>
            )}
          </div>
        ))
      )}
    </div>
  );
};
