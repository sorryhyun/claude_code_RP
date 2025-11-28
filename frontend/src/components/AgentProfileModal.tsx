import { useState, useEffect } from 'react';
import { useFocusTrap } from '../hooks/useFocusTrap';
import type { Agent, AgentUpdate } from '../types';
import { api } from '../utils/api';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { X, Loader2, Upload, Trash2 } from 'lucide-react';

interface AgentProfileModalProps {
  agent: Agent;
  onClose: () => void;
  onUpdate: () => void;
}

export const AgentProfileModal = ({ agent, onClose, onUpdate }: AgentProfileModalProps) => {
  const [editedAgent, setEditedAgent] = useState<Agent>(agent);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Focus trap for modal
  const modalRef = useFocusTrap<HTMLDivElement>(true);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const handleProfilePicChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        setError('Please select an image file');
        return;
      }

      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        setError('Image size must be less than 5MB');
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        setEditedAgent({ ...editedAgent, profile_pic: base64 });
        setError(null);
      };
      reader.onerror = () => {
        setError('Failed to read image file');
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoveProfilePic = () => {
    setEditedAgent({ ...editedAgent, profile_pic: null });
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setError(null);

      const updateData: AgentUpdate = {
        profile_pic: editedAgent.profile_pic,
        in_a_nutshell: editedAgent.in_a_nutshell,
        characteristics: editedAgent.characteristics,
        backgrounds: editedAgent.backgrounds,
        memory: editedAgent.memory,
        recent_events: editedAgent.recent_events,
      };

      await api.updateAgent(agent.id, updateData);
      onUpdate();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update agent');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-2 sm:p-4">
      <div ref={modalRef} className="bg-card rounded-lg sm:rounded-xl shadow-2xl max-w-3xl w-full max-h-[95vh] sm:max-h-[90vh] overflow-hidden border border-border flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-accent p-4 sm:p-6 z-10 flex-shrink-0">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 sm:gap-4 min-w-0 flex-1">
              <div className="relative group flex-shrink-0">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleProfilePicChange}
                  className="hidden"
                  id="profile-pic-input"
                />
                <label
                  htmlFor="profile-pic-input"
                  className="cursor-pointer block w-12 h-12 sm:w-14 sm:h-14 rounded-full overflow-hidden border-2 border-accent-foreground/30 hover:border-accent-foreground/60 active:border-accent-foreground transition-all touch-manipulation"
                  title="Click to change profile picture"
                >
                  {editedAgent.profile_pic ? (
                    <img
                      src={editedAgent.profile_pic}
                      alt={agent.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-accent-foreground/20 flex items-center justify-center">
                      <span className="text-accent-foreground text-lg sm:text-xl font-bold">
                        {agent.name[0]?.toUpperCase()}
                      </span>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity rounded-full">
                    <Upload className="w-5 h-5 text-white" />
                  </div>
                </label>
                {editedAgent.profile_pic && (
                  <button
                    onClick={handleRemoveProfilePic}
                    className="absolute -top-1 -right-1 w-6 h-6 sm:w-5 sm:h-5 bg-destructive rounded-full text-white flex items-center justify-center hover:bg-destructive/90 active:bg-destructive/80 transition-colors opacity-100 sm:opacity-0 sm:group-hover:opacity-100 touch-manipulation"
                    title="Remove profile picture"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
              <div className="min-w-0">
                <h2 className="text-lg sm:text-2xl font-bold text-accent-foreground truncate">{agent.name}</h2>
                <p className="text-accent-foreground/70 text-xs sm:text-sm">Agent Profile</p>
              </div>
            </div>
            <Button
              onClick={onClose}
              variant="ghost"
              size="icon"
              className="text-accent-foreground hover:bg-accent-foreground/20 h-10 w-10 sm:h-11 sm:w-11"
            >
              <X className="w-5 h-5 sm:w-6 sm:h-6" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <ScrollArea className="flex-1">
          <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
            {/* Config File (Read-only) */}
            {agent.config_file && (
              <div>
                <Label className="text-xs sm:text-sm font-semibold mb-1.5 sm:mb-2">
                  Config File
                </Label>
                <div className="px-3 sm:px-4 py-2 sm:py-3 bg-secondary border border-border rounded-lg text-xs sm:text-sm text-muted-foreground break-all">
                  {agent.config_file}
                </div>
              </div>
            )}

            {/* In a Nutshell */}
            <div>
              <Label className="text-xs sm:text-sm font-semibold mb-1.5 sm:mb-2">
                In a Nutshell
              </Label>
              <Textarea
                value={editedAgent.in_a_nutshell || ''}
                onChange={(e) =>
                  setEditedAgent({ ...editedAgent, in_a_nutshell: e.target.value })
                }
                className="text-xs sm:text-sm resize-none"
                rows={3}
                placeholder="Brief identity summary..."
              />
            </div>

            {/* Characteristics */}
            <div>
              <Label className="text-xs sm:text-sm font-semibold mb-1.5 sm:mb-2">
                Characteristics
              </Label>
              <Textarea
                value={editedAgent.characteristics || ''}
                onChange={(e) =>
                  setEditedAgent({ ...editedAgent, characteristics: e.target.value })
                }
                className="text-xs sm:text-sm resize-none"
                rows={4}
                placeholder="Personality traits, communication style..."
              />
            </div>

            {/* Backgrounds */}
            <div>
              <Label className="text-xs sm:text-sm font-semibold mb-1.5 sm:mb-2">
                Backgrounds
              </Label>
              <Textarea
                value={editedAgent.backgrounds || ''}
                onChange={(e) =>
                  setEditedAgent({ ...editedAgent, backgrounds: e.target.value })
                }
                className="text-xs sm:text-sm resize-none"
                rows={4}
                placeholder="Backstory, history, experience..."
              />
            </div>

            {/* Memory */}
            <div>
              <Label className="text-xs sm:text-sm font-semibold mb-1.5 sm:mb-2">
                Memory
              </Label>
              <Textarea
                value={editedAgent.memory || ''}
                onChange={(e) => setEditedAgent({ ...editedAgent, memory: e.target.value })}
                className="text-xs sm:text-sm resize-none"
                rows={4}
                placeholder="Medium-term memory..."
              />
            </div>

            {/* Recent Events */}
            <div>
              <Label className="text-xs sm:text-sm font-semibold mb-1.5 sm:mb-2">
                Recent Events
              </Label>
              <Textarea
                value={editedAgent.recent_events || ''}
                onChange={(e) =>
                  setEditedAgent({ ...editedAgent, recent_events: e.target.value })
                }
                className="text-xs sm:text-sm resize-none"
                rows={3}
                placeholder="Short-term recent context..."
              />
            </div>

            {/* Current System Prompt (Read-only) */}
            <div>
              <Label className="text-xs sm:text-sm font-semibold mb-1.5 sm:mb-2">
                Current System Prompt (Read-only)
              </Label>
              <Textarea
                value={editedAgent.system_prompt}
                readOnly
                className="text-xs sm:text-sm bg-secondary text-muted-foreground resize-none"
                rows={5}
              />
            </div>

            {/* Created At */}
            <div>
              <Label className="text-xs sm:text-sm font-semibold mb-1.5 sm:mb-2">
                Created At
              </Label>
              <div className="px-3 sm:px-4 py-2 sm:py-3 bg-secondary border border-border rounded-lg text-xs sm:text-sm text-muted-foreground">
                {new Date(agent.created_at).toLocaleString()}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="text-destructive text-xs sm:text-sm bg-destructive/10 border border-destructive/20 rounded-lg px-3 sm:px-4 py-2 sm:py-3">
                {error}
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="sticky bottom-0 bg-secondary/50 p-4 sm:p-6 border-t border-border flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 flex-shrink-0">
          <Button
            onClick={onClose}
            variant="outline"
            className="w-full sm:w-auto min-h-[44px]"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving}
            className="w-full sm:w-auto bg-accent hover:bg-accent/90 min-h-[44px]"
          >
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};
