import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  Settings,
  Terminal,
  Sliders,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Pause,
  Bell,
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { useHermes } from '../../contexts/HermesContext';
import { useToast } from '../../contexts/ToastContext';
import { api } from '../../services/api';

interface SidebarProps {
  isCollapsed: boolean;
  toggleCollapse: () => void;
}

const ICON_SIZE = 17;

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, toggleCollapse }) => {
  const location = useLocation();
  const { health, isPaused } = useHermes();
  const { unreadCount } = useToast();

  const navItems = [
    { name: 'Overview', path: '/', icon: LayoutDashboard },
    { name: 'Chat & Activity', path: '/chat', icon: MessageSquare },
    { name: 'Behavior', path: '/configure', icon: Sliders },
    { name: 'Commands', path: '/commands', icon: Terminal },
  ];

  const handleExit = () => {
    api.exitApp();
  };

  const settingsActive = location.pathname === '/settings';

  return (
    <aside
      className={`relative flex h-full shrink-0 flex-col border-r border-[var(--border-subtle)] bg-[var(--sidebar-bg)] backdrop-blur-2xl transition-[width] duration-300 [transition-timing-function:var(--ease-out-soft)] ${
        isCollapsed ? 'w-[68px]' : 'w-[244px]'
      }`}
    >
      <button
        onClick={toggleCollapse}
        className="app-region-no-drag absolute -right-3 top-[64px] z-30 flex h-6 w-6 items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--surface-2)] text-[var(--text-tertiary)] shadow-[var(--shadow-soft)] transition-all duration-200 hover:scale-110 hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--shadow-focus)]"
        title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        aria-label={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
      >
        {isCollapsed ? (
          <ChevronRight className="h-3 w-3" strokeWidth={2.5} />
        ) : (
          <ChevronLeft className="h-3 w-3" strokeWidth={2.5} />
        )}
      </button>

      <div
        className={`relative z-10 flex h-14 shrink-0 items-center border-b border-[var(--border-subtle)] px-3 ${
          isCollapsed ? 'justify-center' : 'gap-2.5'
        }`}
      >
        <div className="relative flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-[var(--border-strong)] bg-[var(--surface-1)]">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="square" className="h-3.5 w-3.5 text-[var(--text-primary)]" aria-hidden="true">
            <path d="M7 4v16M17 4v16M7 12h10" />
          </svg>
          <span
            className={`absolute -bottom-0.5 -right-0.5 h-1.5 w-1.5 rounded-full border-2 border-[var(--surface-0)] transition-all duration-500 ${
              health
                ? isPaused ? 'bg-[var(--state-warn)] shadow-[0_0_6px_var(--state-warn)]' : 'bg-[var(--state-ready)] shadow-[0_0_6px_var(--state-ready-glow)]'
                : 'bg-[var(--state-error)] shadow-[0_0_6px_var(--state-error-glow)]'
            }`}
          />
        </div>
        {!isCollapsed && (
          <div className="flex min-w-0 flex-col leading-tight">
            <span className="font-display text-[13px] font-bold tracking-[-0.01em] text-[var(--text-primary)]">
              Hermes
            </span>
            <span className="eyebrow -mt-0.5 text-[9px] tracking-[0.18em]">
              Voice Bridge
            </span>
          </div>
        )}
      </div>

      {isPaused && !isCollapsed && (
        <div className="mx-3 mt-3 px-2.5 py-1.5 bg-[var(--state-warn)]/10 border border-[var(--state-warn)]/20 rounded-md flex items-center justify-between text-[var(--state-warn)] text-xs font-medium">
          <span>Hermes is paused</span>
          <Pause size={12} />
        </div>
      )}

      <nav className="custom-scrollbar relative z-10 min-h-0 flex-1 overflow-y-auto px-2 py-3" aria-label="Primary">
        {!isCollapsed && (
          <p className="eyebrow mb-2 px-2 text-[var(--text-tertiary)]">
            Workspace
          </p>
        )}
        <ul className="flex flex-col gap-0.5">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <li key={item.path} className="relative">
                <Link
                  to={item.path}
                  aria-label={item.name}
                  aria-current={isActive ? 'page' : undefined}
                  className={`nav-item ${isActive ? 'is-active' : ''} ${isCollapsed ? 'justify-center px-0' : ''}`}
                >
                  <item.icon className="nav-icon" size={ICON_SIZE} strokeWidth={1.75} />
                  {!isCollapsed && <span className="truncate">{item.name}</span>}
                  {isCollapsed && <span className="nav-tooltip" role="tooltip">{item.name}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="relative z-10 mt-auto shrink-0 space-y-0.5 border-t border-[var(--border-subtle)] p-2">
        {!isCollapsed && (
          <div className="mx-1 mb-2 flex items-center justify-between rounded-md border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-2.5 py-1.5">
            <span className="eyebrow text-[var(--text-tertiary)]">
              Backend
            </span>
            <span className={`inline-flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-[0.16em] ${health ? 'text-[var(--state-ready)]' : 'text-[var(--state-error)]'}`}>
              <span className={`status-dot ${health ? 'state-ready animate-pulse-glow' : 'state-error'}`} />
              {health ? 'CONNECTED' : 'OFFLINE'}
            </span>
          </div>
        )}

        <Link
          to="/notifications"
          aria-label="Notifications"
          aria-current={location.pathname === '/notifications' ? 'page' : undefined}
          className={`nav-item ${location.pathname === '/notifications' ? 'is-active' : ''} ${isCollapsed ? 'justify-center px-0' : ''}`}
        >
          <div className="relative flex items-center justify-center">
            <Bell className="nav-icon" size={ICON_SIZE} strokeWidth={1.75} />
            {unreadCount > 0 && (
              <span className="absolute -right-1.5 -top-1 flex h-3.5 min-w-[14px] items-center justify-center rounded-full border border-[var(--sidebar-bg)] bg-[var(--state-error)] px-1 text-[8px] font-extrabold leading-none text-white shadow-[0_0_8px_var(--state-error-glow)] animate-pulse-glow">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </div>
          {!isCollapsed && <span className="truncate">Notifications</span>}
          {isCollapsed && <span className="nav-tooltip" role="tooltip">Notifications</span>}
        </Link>

        <Link
          to="/settings"
          aria-label="System Settings"
          aria-current={settingsActive ? 'page' : undefined}
          className={`nav-item ${settingsActive ? 'is-active' : ''} ${isCollapsed ? 'justify-center px-0' : ''}`}
        >
          <Settings className="nav-icon" size={ICON_SIZE} strokeWidth={1.75} />
          {!isCollapsed && <span className="truncate">Settings</span>}
          {isCollapsed && <span className="nav-tooltip" role="tooltip">Settings</span>}
        </Link>

        <button
          onClick={handleExit}
          aria-label="Exit"
          className={`nav-item w-full ${isCollapsed ? 'justify-center px-0' : ''} hover:!border-[var(--state-error-glow)] hover:!bg-[var(--state-error)]/10 hover:!text-[var(--state-error)]`}
        >
          <LogOut className="nav-icon" size={ICON_SIZE} strokeWidth={1.75} />
          {!isCollapsed && <span className="truncate">Exit</span>}
          {isCollapsed && <span className="nav-tooltip" role="tooltip">Exit</span>}
        </button>
      </div>
    </aside>
  );
};
