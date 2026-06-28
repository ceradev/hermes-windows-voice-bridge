import React from 'react';
import { useLocation } from 'react-router-dom';
import { Moon, Sun, Globe } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';
import { useLanguage } from '../../contexts/LanguageContext';

export const Header = () => {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { language, toggleLanguage, t } = useLanguage();

  const getPageTitle = (path: string) => {
    switch (path) {
      case '/':
        return t('nav.general');
      case '/chat':
        return t('nav.sessions');
      case '/configure':
        return t('nav.shortcuts');
      case '/commands':
        return t('nav.commands');
      case '/settings':
        return t('nav.settings');
      default:
        return 'Hermes';
    }
  };

  const getPageEyebrow = (path: string) => {
    switch (path) {
      case '/':
        return 'Overview';
      case '/chat':
        return 'Workspace';
      case '/configure':
        return 'Input';
      case '/commands':
        return 'Automation';
      case '/settings':
        return 'System';
      default:
        return 'Page';
    }
  };

  return (
    <header className="surface-titlebar flex h-[60px] shrink-0 select-none items-center justify-between px-6 md:px-8 relative z-40" style={{ borderImage: 'linear-gradient(to right, transparent, var(--border-subtle) 20%, var(--border-subtle) 80%, transparent) 1' }}>
      <div className="flex min-w-0 items-baseline gap-3">
        <p className="eyebrow eyebrow-accent text-[9px]">
          {getPageEyebrow(location.pathname)}
        </p>
        <h2 className="truncate font-display text-[16px] font-bold tracking-[-0.01em] text-[var(--text-primary)]">
          {getPageTitle(location.pathname)}
        </h2>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          onClick={toggleLanguage}
          className="flex items-center gap-1.5 rounded-md border border-transparent px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--text-tertiary)] transition-colors hover:border-[var(--border-subtle)] hover:bg-[var(--surface-1)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--shadow-focus)]"
          title={t('lang.toggle')}
          aria-label={t('lang.toggle')}
        >
          <Globe className="h-3.5 w-3.5" strokeWidth={1.8} />
          {language}
        </button>

        <button
          onClick={toggleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-transparent text-[var(--text-tertiary)] transition-colors hover:border-[var(--border-subtle)] hover:bg-[var(--surface-1)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--shadow-focus)]"
          title={t('theme.toggle')}
          aria-label={t('theme.toggle')}
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4" strokeWidth={1.8} />
          ) : (
            <Moon className="h-4 w-4" strokeWidth={1.8} />
          )}
        </button>
      </div>
    </header>
  );
};
