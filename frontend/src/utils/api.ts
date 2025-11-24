import type { Room, RoomSummary, RoomUpdate, Agent, AgentCreate, AgentUpdate, AgentConfig, Message } from '../types';

// Get clean API URL without credentials
function getApiUrl(): string {
  // If VITE_API_BASE_URL is explicitly set, use it
  if (import.meta.env.VITE_API_BASE_URL) {
    const urlString = import.meta.env.VITE_API_BASE_URL;
    try {
      const parsed = new URL(urlString);
      // Remove credentials if present (they're handled by API key now)
      parsed.username = '';
      parsed.password = '';
      // Remove trailing slash to avoid double slashes in API calls
      return parsed.toString().replace(/\/$/, '');
    } catch {
      return urlString;
    }
  }

  // Auto-detect based on current window location
  // If accessing via network IP, use network IP for backend too
  const currentHost = window.location.hostname;
  if (currentHost !== 'localhost' && currentHost !== '127.0.0.1') {
    return `http://${currentHost}:8000`;
  }

  // Default to localhost
  return 'http://localhost:8000';
}

export const API_BASE_URL = getApiUrl();

/**
 * Generate the URL for an agent's profile picture.
 * Returns the URL to the profile pic endpoint if the agent has a profile picture.
 */
export function getAgentProfilePicUrl(agent: { name: string; profile_pic?: string | null }): string | null {
  if (!agent.profile_pic) return null;
  return `${API_BASE_URL}/agents/${encodeURIComponent(agent.name)}/profile-pic`;
}

// Global API key storage for the API module
let globalApiKey: string | null = null;

/**
 * Set the API key to be used for all API requests.
 * This should be called by the AuthContext when the user logs in.
 */
export function setApiKey(key: string | null) {
  globalApiKey = key;
}

/**
 * Get the current API key.
 */
export function getApiKey(): string | null {
  return globalApiKey;
}

// Helper to create fetch options with API key
function getFetchOptions(options: RequestInit = {}): RequestInit {
  // Properly merge headers: user headers first, then add API key
  // This ensures API key is always included and not overwritten by user headers
  const headers: Record<string, string> = {
    ...options.headers as Record<string, string>,
  };

  // Add API key header if available
  if (globalApiKey) {
    headers['X-API-Key'] = globalApiKey;
  }

  // Add ngrok header to skip browser warning page
  headers['ngrok-skip-browser-warning'] = 'true';

  return {
    ...options,
    headers,
  };
}

export const api = {
  // Rooms
  async getRooms(): Promise<RoomSummary[]> {
    const response = await fetch(`${API_BASE_URL}/rooms`, getFetchOptions());
    if (!response.ok) throw new Error('Failed to fetch rooms');
    return response.json();
  },

  async getRoom(roomId: number): Promise<Room> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}`, getFetchOptions());
    if (!response.ok) throw new Error('Failed to fetch room');
    return response.json();
  },

  async createRoom(name: string): Promise<Room> {
    const response = await fetch(`${API_BASE_URL}/rooms`, getFetchOptions({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }));
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to create room' }));
      throw new Error(errorData.detail || 'Failed to create room');
    }
    return response.json();
  },

  async updateRoom(roomId: number, roomData: RoomUpdate): Promise<Room> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}`, getFetchOptions({
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(roomData),
    }));
    if (!response.ok) throw new Error('Failed to update room');
    return response.json();
  },

  async pauseRoom(roomId: number): Promise<Room> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/pause`, getFetchOptions({
      method: 'POST',
    }));
    if (!response.ok) throw new Error('Failed to pause room');
    return response.json();
  },

  async resumeRoom(roomId: number): Promise<Room> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/resume`, getFetchOptions({
      method: 'POST',
    }));
    if (!response.ok) throw new Error('Failed to resume room');
    return response.json();
  },

  async markRoomAsRead(roomId: number): Promise<{ message: string; last_read_at: string }> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/mark-read`, getFetchOptions({
      method: 'POST',
    }));
    if (!response.ok) throw new Error('Failed to mark room as read');
    return response.json();
  },

  async deleteRoom(roomId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}`, getFetchOptions({
      method: 'DELETE',
    }));
    if (!response.ok) throw new Error('Failed to delete room');
    return response.json();
  },

  // Agents
  async getAllAgents(): Promise<Agent[]> {
    const response = await fetch(`${API_BASE_URL}/agents`, getFetchOptions());
    if (!response.ok) throw new Error('Failed to fetch agents');
    return response.json();
  },

  async getAgent(agentId: number): Promise<Agent> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, getFetchOptions());
    if (!response.ok) throw new Error('Failed to fetch agent');
    return response.json();
  },

  async getRoomAgents(roomId: number): Promise<Agent[]> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/agents`, getFetchOptions());
    if (!response.ok) throw new Error('Failed to fetch room agents');
    return response.json();
  },

  async createAgent(agentData: AgentCreate): Promise<Agent> {
    const response = await fetch(`${API_BASE_URL}/agents`, getFetchOptions({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(agentData),
    }));
    if (!response.ok) throw new Error('Failed to create agent');
    return response.json();
  },

  async deleteAgent(agentId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, getFetchOptions({
      method: 'DELETE',
    }));
    if (!response.ok) throw new Error('Failed to delete agent');
    return response.json();
  },

  async addAgentToRoom(roomId: number, agentId: number): Promise<Room> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/agents/${agentId}`, getFetchOptions({
      method: 'POST',
    }));
    if (!response.ok) throw new Error('Failed to add agent to room');
    return response.json();
  },

  async removeAgentFromRoom(roomId: number, agentId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/agents/${agentId}`, getFetchOptions({
      method: 'DELETE',
    }));
    if (!response.ok) throw new Error('Failed to remove agent from room');
    return response.json();
  },

  async updateAgent(agentId: number, agentData: AgentUpdate): Promise<Agent> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, getFetchOptions({
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(agentData),
    }));
    if (!response.ok) throw new Error('Failed to update agent');
    return response.json();
  },

  async getAgentConfigs(): Promise<{ configs: AgentConfig }> {
    const response = await fetch(`${API_BASE_URL}/agent-configs`, getFetchOptions());
    if (!response.ok) throw new Error('Failed to fetch agent configs');
    return response.json();
  },

  async getAgentDirectRoom(agentId: number): Promise<Room> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/direct-room`, getFetchOptions());
    if (!response.ok) throw new Error('Failed to get agent direct room');
    return response.json();
  },

  // Messages
  async getMessages(roomId: number): Promise<Message[]> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/messages`, getFetchOptions());
    if (!response.ok) throw new Error('Failed to fetch messages');
    return response.json();
  },

  async clearRoomMessages(roomId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/messages`, getFetchOptions({
      method: 'DELETE',
    }));
    if (!response.ok) throw new Error('Failed to clear messages');
    return response.json();
  },
};
