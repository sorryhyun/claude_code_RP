// Re-export everything from services
export * from './apiClient';
export * from './roomService';
export * from './agentService';
export * from './messageService';

// Import services
import { roomService } from './roomService';
import { agentService } from './agentService';
import { messageService } from './messageService';

/**
 * Legacy API object for backward compatibility.
 * @deprecated Use individual services (roomService, agentService, messageService) instead.
 */
export const api = {
  // Room operations
  ...roomService,

  // Agent operations
  ...agentService,

  // Message operations
  ...messageService,
};
