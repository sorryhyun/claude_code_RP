import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import English translations
import enCommon from './locales/en/common.json';
import enAuth from './locales/en/auth.json';
import enSidebar from './locales/en/sidebar.json';
import enChat from './locales/en/chat.json';
import enAgents from './locales/en/agents.json';
import enRooms from './locales/en/rooms.json';
import enDocs from './locales/en/docs.json';

// Import Korean translations
import koCommon from './locales/ko/common.json';
import koAuth from './locales/ko/auth.json';
import koSidebar from './locales/ko/sidebar.json';
import koChat from './locales/ko/chat.json';
import koAgents from './locales/ko/agents.json';
import koRooms from './locales/ko/rooms.json';
import koDocs from './locales/ko/docs.json';

const resources = {
  en: {
    common: enCommon,
    auth: enAuth,
    sidebar: enSidebar,
    chat: enChat,
    agents: enAgents,
    rooms: enRooms,
    docs: enDocs,
  },
  ko: {
    common: koCommon,
    auth: koAuth,
    sidebar: koSidebar,
    chat: koChat,
    agents: koAgents,
    rooms: koRooms,
    docs: koDocs,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    defaultNS: 'common',
    ns: ['common', 'auth', 'sidebar', 'chat', 'agents', 'rooms', 'docs'],

    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'chitchats_language',
    },

    interpolation: {
      escapeValue: false, // React already escapes
    },

    react: {
      useSuspense: true,
    },
  });

export default i18n;
