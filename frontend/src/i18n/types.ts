import 'i18next';
import type enCommon from './locales/en/common.json';
import type enAuth from './locales/en/auth.json';
import type enSidebar from './locales/en/sidebar.json';
import type enChat from './locales/en/chat.json';
import type enAgents from './locales/en/agents.json';
import type enRooms from './locales/en/rooms.json';
import type enDocs from './locales/en/docs.json';

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: {
      common: typeof enCommon;
      auth: typeof enAuth;
      sidebar: typeof enSidebar;
      chat: typeof enChat;
      agents: typeof enAgents;
      rooms: typeof enRooms;
      docs: typeof enDocs;
    };
  }
}
