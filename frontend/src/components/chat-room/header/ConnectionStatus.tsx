import { useTranslation } from 'react-i18next';

interface ConnectionStatusProps {
  isConnected: boolean;
}

export const ConnectionStatus = ({ isConnected }: ConnectionStatusProps) => {
  const { t } = useTranslation('chat');

  return (
    <div className="flex items-center gap-1">
      <div className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
      <span className="text-mobile-sm text-slate-500 hidden sm:inline">
        {isConnected ? t('connected') : t('disconnected')}
      </span>
    </div>
  );
};
