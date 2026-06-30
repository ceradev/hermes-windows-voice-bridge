import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Minus, Square, X, Sun, Moon, Globe } from 'lucide-react';
import { api } from '../../services/api';
import { useHermes } from '../../contexts/HermesContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { useChromeSessionTitle } from '../../hooks/useChromeSessionTitle';

export const Titlebar = ({ onToggleMini }: { onToggleMini?: () => void }) => {
  const { health, isPaused, runtime } = useHermes();
  const { theme, toggleTheme } = useTheme();
  const { language, toggleLanguage, t } = useLanguage();
  const chromeTitle = useChromeSessionTitle();
  const navigate = useNavigate();

  const getStatusText = () => {
    if (!health) return 'Offline';
    if (isPaused) return 'Paused';
    if (runtime.listening_state === 'listening') return 'Listening';
    if (runtime.listening_state === 'thinking' || runtime.listening_state === 'processing') return 'Thinking';
    if (runtime.listening_state === 'speaking' || runtime.listening_state === 'responding') return 'Speaking';
    return 'Ready';
  };

  const isActive = runtime?.listening_state === 'listening';

  return (
    <div className="surface-titlebar app-region-drag fixed left-0 right-0 top-0 z-50 flex h-10 select-none items-center justify-between gap-3 px-3">
      <div className="app-region-no-drag flex min-w-0 flex-1 items-center gap-2.5 overflow-hidden">
        <div className="relative flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-control)] bg-[var(--accent)]">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={3}
            strokeLinecap="square"
            className="h-3.5 w-3.5 text-white"
            aria-hidden="true"
          >
            <path d="M7 4v16M17 4v16M7 12h10" />
          </svg>
          <span
            className={`absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border-2 border-[var(--bg-base)] ${
              health ? 'bg-[var(--state-ready)]' : 'bg-[var(--state-error)]'
            }`}
            aria-hidden="true"
          />
        </div>
        <button
          type="button"
          onClick={() => navigate('/chat')}
          className="min-w-0 truncate text-left transition-opacity hover:opacity-90"
          title="Open chat"
        >
          <span className="ds-chrome-title block truncate">{chromeTitle}</span>
        </button>
      </div>

      <div className="app-region-no-drag flex items-center gap-1.5">
        <span
          className={`hidden rounded-[var(--radius-control)] border px-2.5 py-1 text-[13px] font-medium sm:inline-flex ${
            isActive
              ? 'border-[var(--accent)]/40 bg-[var(--accent-soft)] text-[var(--accent)]'
              : 'glass-chip text-[var(--text-secondary)]'
          }`}
        >
          {getStatusText()}
        </span>

        <button
          onClick={toggleLanguage}
          className="flex h-8 items-center gap-1 rounded-[var(--radius-control)] px-2 text-[13px] font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)]"
          title={t('lang.toggle')}
          aria-label={t('lang.toggle')}
        >
          <Globe className="h-4 w-4" strokeWidth={1.75} />
          {language}
        </button>

        <button
          onClick={toggleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)]"
          title={t('theme.toggle')}
          aria-label={t('theme.toggle')}
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" strokeWidth={1.75} /> : <Moon className="h-4 w-4" strokeWidth={1.75} />}
        </button>

        <div className="mx-0.5 h-4 w-px bg-[var(--border-subtle)]" />

        <button
          onClick={onToggleMini || (() => api.minimizeToTray())}
          className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)]"
          title="Mini mode"
          aria-label="Mini mode"
        >
          <Minus className="h-4 w-4" strokeWidth={2} />
        </button>
        <button
          onClick={() => api.maximizeWindow()}
          className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-glass-hover)] hover:text-[var(--text-primary)]"
          title="Maximize"
          aria-label="Maximize"
        >
          <Square className="h-3.5 w-3.5" strokeWidth={2} />
        </button>
        <button
          onClick={() => api.minimizeToTray()}
          className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] text-[var(--text-secondary)] transition-colors hover:bg-[rgba(255,107,107,0.12)] hover:text-[var(--state-error)]"
          title="Close to tray"
          aria-label="Close to tray"
        >
          <X className="h-4 w-4" strokeWidth={2} />
        </button>
      </div>
    </div>
  );
};
