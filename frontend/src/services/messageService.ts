import type { Message } from '../types';
import { API_BASE_URL, getFetchOptions } from './apiClient';

export const messageService = {
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
