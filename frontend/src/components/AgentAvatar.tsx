import type { Agent } from '../types';
import { getAgentProfilePicUrl } from '../utils/api';
import { useState } from 'react';

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

  const baseClasses = `rounded-full flex items-center justify-center flex-shrink-0 ${sizeClasses[size]} ${className}`;

  const profilePicUrl = agent.profile_pic ? getAgentProfilePicUrl(agent) : null;

  if (profilePicUrl && !imageError) {
    return (
      <img
        src={profilePicUrl}
        alt={agent.name}
        className={`${baseClasses} object-cover ${onClick ? 'cursor-pointer' : ''}`}
        onClick={onClick}
        title={onClick ? 'Click to change profile picture' : agent.name}
        onError={() => setImageError(true)}
      />
    );
  }

  return (
    <div
      className={`${baseClasses} bg-gradient-to-br from-emerald-400 to-cyan-500 ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
      title={onClick ? 'Click to set profile picture' : agent.name}
    >
      <span className="text-white font-bold">{agent.name[0]?.toUpperCase()}</span>
    </div>
  );
};
