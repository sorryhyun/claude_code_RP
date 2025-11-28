import type { Agent } from '../types';
import { getAgentProfilePicUrl } from '../utils/api';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

interface AgentAvatarProps {
  agent: Agent;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onClick?: () => void;
}

export const AgentAvatar = ({ agent, size = 'md', className = '', onClick }: AgentAvatarProps) => {
  const [imageError, setImageError] = useState(false);

  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-14 h-14 text-xl',
  };

  const profilePicUrl = agent.profile_pic ? getAgentProfilePicUrl(agent) : null;

  return (
    <Avatar
      className={cn(
        sizeClasses[size],
        onClick && 'cursor-pointer hover:ring-2 hover:ring-accent transition-all',
        className
      )}
      onClick={onClick}
      title={onClick ? 'Click to change profile picture' : agent.name}
    >
      {profilePicUrl && !imageError ? (
        <AvatarImage
          src={profilePicUrl}
          alt={agent.name}
          onError={() => setImageError(true)}
        />
      ) : null}
      <AvatarFallback className="bg-accent text-accent-foreground font-semibold">
        {agent.name[0]?.toUpperCase()}
      </AvatarFallback>
    </Avatar>
  );
};
