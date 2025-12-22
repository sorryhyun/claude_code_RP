interface SidebarToggleProps {
  isSidebarCollapsed: boolean;
  onToggleSidebar: () => void;
}

export const SidebarToggle = ({ isSidebarCollapsed, onToggleSidebar }: SidebarToggleProps) => {
  return (
    <button
      onClick={onToggleSidebar}
      className="hidden lg:flex p-3 bg-slate-700 text-white hover:bg-slate-600 rounded-lg transition-colors flex-shrink-0 shadow-lg"
      title={isSidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}
    >
      <svg
        className={`w-6 h-6 transition-transform duration-200 ${isSidebarCollapsed ? 'rotate-180' : ''}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>
  );
};
