import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Mic, Settings, LayoutDashboard, MessageSquare, Key, History, Activity, Volume2, ChevronLeft, ChevronRight, LogOut, Terminal } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { api } from '../../services/api';

interface SidebarProps {
  isCollapsed: boolean;
  toggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, toggleCollapse }) => {
  const location = useLocation();
  const { t } = useLanguage();
  
  const navItems = [
    { name: t('nav.general'), path: '/', icon: LayoutDashboard },
    { name: t('nav.sessions'), path: '/sessions', icon: MessageSquare },
    { name: t('nav.history'), path: '/history', icon: History },
    { name: t('nav.voice'), path: '/voice', icon: Mic },
    { name: t('nav.shortcuts'), path: '/shortcuts', icon: Key },
    { name: t('nav.commands'), path: '/commands', icon: Terminal },
    { name: t('nav.hermes'), path: '/hermes', icon: Activity },
    { name: t('nav.tts'), path: '/tts', icon: Volume2 },
  ];

  const handleExit = () => {
    api.exitApp();
  };

  const settingsActive = location.pathname === '/settings';

  return (
    <div className={`glass-panel relative mr-16 flex h-full shrink-0 select-none flex-col rounded-[var(--radius-panel)] pt-4 text-gray-900 transition-all duration-300 dark:text-gray-300 ${isCollapsed ? 'w-20' : 'w-72'}`}>
      {/* Floating Toggle Button */}
      <button 
        onClick={toggleCollapse}
        className="absolute -right-12 top-6 z-50 flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] border border-black/10 bg-white text-gray-500 shadow-md transition-colors hover:text-gray-900 focus:outline-none dark:border-white/10 dark:bg-gray-900 dark:text-gray-400 dark:hover:text-white"
        title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
      >
        {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>

      <div className={`mb-6 flex h-12 items-center border-b border-black/10 px-4 pb-4 dark:border-white/10 ${isCollapsed ? 'justify-center' : 'justify-start'}`}>
        {!isCollapsed && (
          <div className="flex min-w-0 flex-col truncate">
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">Field Console</p>
            <h1 className="truncate text-base font-extrabold leading-tight tracking-tight text-gray-900 dark:text-white">Hermes Voice Bridge</h1>
          </div>
        )}
        
        {isCollapsed && (
          <div className="flex flex-col items-center justify-center">
            <h1 className="text-base font-extrabold leading-tight tracking-tight text-gray-900 dark:text-white">H</h1>
          </div>
        )}
      </div>

      <nav className="custom-scrollbar mt-2 min-h-0 flex-1 space-y-1.5 overflow-y-auto px-3">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              title={isCollapsed ? item.name : undefined}
              className={`group relative flex items-center overflow-hidden rounded-[var(--radius-control)] border px-3 py-3 text-sm font-semibold transition-all duration-200 ${
                isActive 
                  ? 'border-black/15 bg-black/5 text-gray-900 dark:border-white/15 dark:bg-white/10 dark:text-white' 
                  : 'border-transparent text-gray-600 hover:border-black/10 hover:bg-black/5 hover:text-gray-900 dark:text-gray-400 dark:hover:border-white/10 dark:hover:bg-white/5 dark:hover:text-white'
              } ${isCollapsed ? 'justify-center' : 'gap-3'}`}
            >
              {isActive && <span className="absolute left-0 top-1 bottom-1 w-[3px] bg-current" />}
              <item.icon className={`relative z-10 h-5 w-5 flex-shrink-0 transition-colors ${isActive ? 'text-gray-900 dark:text-white' : 'text-gray-500 group-hover:text-gray-900 dark:group-hover:text-gray-300'}`} />
              {!isCollapsed && <span className="relative z-10 truncate">{item.name}</span>}
            </Link>
          );
        })}
      </nav>
      
      <div className="mt-auto space-y-2 border-t border-black/10 p-3 dark:border-white/10">
        <Link
          to="/settings"
          title={isCollapsed ? t('nav.settings') : undefined}
          className={`group relative flex items-center overflow-hidden rounded-[var(--radius-control)] border px-3 py-3 text-sm font-semibold transition-all duration-200 ${
            settingsActive 
              ? 'border-black/15 bg-black/5 text-gray-900 dark:border-white/15 dark:bg-white/10 dark:text-white' 
              : 'border-transparent text-gray-600 hover:border-black/10 hover:bg-black/5 hover:text-gray-900 dark:text-gray-400 dark:hover:border-white/10 dark:hover:bg-white/5 dark:hover:text-white'
          } ${isCollapsed ? 'justify-center' : 'gap-3'}`}
        >
          {settingsActive && <span className="absolute left-0 top-1 bottom-1 w-[3px] bg-current" />}
          <Settings className={`relative z-10 h-5 w-5 flex-shrink-0 transition-colors ${settingsActive ? 'text-gray-900 dark:text-white' : 'text-gray-500 group-hover:text-gray-900 dark:group-hover:text-gray-300'}`} />
          {!isCollapsed && <span className="relative z-10 truncate">{t('nav.settings')}</span>}
        </Link>
        <button onClick={handleExit} className={`group flex w-full items-center rounded-[var(--radius-control)] border border-transparent px-3 py-3 text-sm font-semibold text-gray-600 transition-all duration-200 hover:border-red-500/20 hover:bg-red-500/10 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-300 ${isCollapsed ? 'justify-center' : 'gap-3'}`}>
          <LogOut className="h-5 w-5 text-gray-500 transition-colors group-hover:text-red-500 dark:group-hover:text-red-400" />
          {!isCollapsed && <span>{t('nav.exit', 'Exit')}</span>}
        </button>
      </div>
    </div>
  );
};
