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
} from 'lucide-react';
import { useHermes } from '../../contexts/HermesContext';
import { api } from '../../services/api';

interface SidebarProps {
  isCollapsed: boolean;
  toggleCollapse: () => void;
}

const navItemClass = (isActive: boolean, isCollapsed: boolean) =>
  ['nav-item', isActive ? 'is-active' : '', isCollapsed ? 'nav-item--collapsed' : '']
    .filter(Boolean)
    .join(' ');

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, toggleCollapse }) => {
  const location = useLocation();
  const { health, isPaused } = useHermes();

  const navItems = [
    { name: 'Overview', path: '/', icon: LayoutDashboard },
    { name: 'Chat & activity', path: '/chat', icon: MessageSquare },
    { name: 'Voice & shortcuts', path: '/configure', icon: Sliders },
    { name: 'Commands', path: '/commands', icon: Terminal },
  ];

  const settingsActive = location.pathname === '/settings';
  const iconSize = isCollapsed ? 24 : 20;

  return (
    <aside
      className={`sidebar relative flex h-full shrink-0 flex-col border-r border-[var(--border-subtle)] bg-[var(--sidebar-bg)] transition-[width] duration-200 ${
        isCollapsed ? 'sidebar--collapsed w-[var(--sidebar-width-collapsed)]' : 'w-[var(--sidebar-width-expanded)]'
      }`}
    >
      <button
        onClick={toggleCollapse}
        className="app-region-no-drag absolute -right-2.5 top-3.5 z-30 flex h-6 w-6 items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--surface-1)] text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
      </button>

      {isPaused && (
        isCollapsed ? (
          <div
            className="mx-auto mt-3 flex h-10 w-10 items-center justify-center rounded-[var(--radius-control)] border border-[var(--state-warn)]/25 bg-[var(--state-warn)]/10 text-[var(--state-warn)]"
            title="Paused"
            aria-label="Assistant paused"
          >
            <Pause size={22} strokeWidth={2} />
          </div>
        ) : (
          <div className="mx-2.5 mt-2.5 flex items-center justify-between gap-2 rounded-[var(--radius-control)] border border-[var(--state-warn)]/25 bg-[var(--state-warn)]/10 px-3 py-2.5 text-[15px] font-medium text-[var(--state-warn)]">
            <span>Paused</span>
            <Pause size={18} strokeWidth={2} />
          </div>
        )
      )}

      <nav className="custom-scrollbar min-h-0 flex-1 overflow-y-auto px-2.5 py-3" aria-label="Primary">
        <ul className={`flex flex-col ${isCollapsed ? 'gap-1' : 'gap-0.5'}`}>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  aria-label={item.name}
                  aria-current={isActive ? 'page' : undefined}
                  className={navItemClass(isActive, isCollapsed)}
                  title={isCollapsed ? item.name : undefined}
                >
                  <item.icon className="nav-icon" size={iconSize} strokeWidth={1.75} aria-hidden />
                  {!isCollapsed && <span className="truncate">{item.name}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="shrink-0 space-y-1 border-t border-[var(--border-subtle)] p-2.5">
        {isCollapsed ? (
          <div
            className="sidebar-status-dot"
            title={health ? 'Online' : 'Offline'}
            aria-label={health ? 'Connection online' : 'Connection offline'}
          >
            <span className={`status-dot h-2.5 w-2.5 ${health ? 'state-ready' : 'state-error'}`} />
          </div>
        ) : (
          <div className="mb-1 flex items-center justify-between rounded-[var(--radius-control)] bg-[var(--surface-inset)] px-3 py-2.5">
            <span className="text-[14px] text-[var(--text-tertiary)]">Connection</span>
            <span className={`inline-flex items-center gap-1.5 text-[14px] font-medium ${health ? 'text-[var(--state-ready)]' : 'text-[var(--state-error)]'}`}>
              <span className={`status-dot ${health ? 'state-ready' : 'state-error'}`} />
              {health ? 'Online' : 'Offline'}
            </span>
          </div>
        )}

        <Link
          to="/settings"
          aria-label="Settings"
          aria-current={settingsActive ? 'page' : undefined}
          className={navItemClass(settingsActive, isCollapsed)}
          title={isCollapsed ? 'Settings' : undefined}
        >
          <Settings className="nav-icon" size={iconSize} strokeWidth={1.75} aria-hidden />
          {!isCollapsed && <span className="truncate">Settings</span>}
        </Link>

        <button
          onClick={() => api.exitApp()}
          aria-label="Exit"
          className={`${navItemClass(false, isCollapsed)} w-full hover:!bg-[rgba(255,107,107,0.1)] hover:!text-[var(--state-error)]`}
          title={isCollapsed ? 'Exit' : undefined}
        >
          <LogOut className="nav-icon" size={iconSize} strokeWidth={1.75} aria-hidden />
          {!isCollapsed && <span className="truncate">Exit</span>}
        </button>
      </div>
    </aside>
  );
};
