import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Bell, Settings, Moon, Sun, Globe } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';
import { useLanguage } from '../../contexts/LanguageContext';

export const Header = () => {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { language, toggleLanguage, t } = useLanguage();
  
  const getPageTitle = (path: string) => {
    switch (path) {
      case '/': return t('nav.general');
      case '/sessions': return t('nav.sessions');
      case '/history': return t('nav.history');
      case '/voice': return t('nav.voice');
      case '/shortcuts': return t('nav.shortcuts');
      case '/commands': return t('nav.commands');
      case '/hermes': return t('nav.hermes');
      case '/tts': return t('nav.tts');
      case '/settings': return t('nav.settings');
      default: return 'Hermes';
    }
  };

  return (
    <header className="h-16 border-b border-gray-200/50 dark:border-white/10 bg-transparent flex items-center justify-between px-8 select-none z-40 transition-colors duration-300">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white tracking-tight">
        {getPageTitle(location.pathname)}
      </h2>
      
      <div className="flex items-center gap-3">
        <button 
          onClick={toggleLanguage}
          className="flex items-center gap-1 p-2 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors focus:outline-none rounded-full hover:bg-gray-100 dark:hover:bg-white/5 font-semibold text-xs uppercase"
          title={t('lang.toggle')}
        >
          <Globe className="w-4 h-4" />
          {language}
        </button>

        <button 
          onClick={toggleTheme}
          className="p-2 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors focus:outline-none rounded-full hover:bg-gray-100 dark:hover:bg-white/5"
          title={t('theme.toggle')}
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        <div className="w-px h-6 bg-gray-200 dark:bg-gray-800 mx-1"></div>

        <button className="relative p-2 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors focus:outline-none rounded-full hover:bg-gray-100 dark:hover:bg-white/5">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-blue-500 rounded-full border border-white dark:border-[#0a0a0a]"></span>
        </button>
        <Link to="/settings" className="p-2 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors focus:outline-none rounded-full hover:bg-gray-100 dark:hover:bg-white/5">
          <Settings className="w-5 h-5" />
        </Link>
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-purple-600 ml-2 shadow-sm border border-gray-200 dark:border-gray-700"></div>
      </div>
    </header>
  );
};
