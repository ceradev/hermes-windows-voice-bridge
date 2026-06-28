import React from 'react';
import { Minus, Square, X } from 'lucide-react';
import { api } from '../../services/api';
import { useHermes } from '../../contexts/HermesContext';

export const Titlebar = ({ onToggleMini }: { onToggleMini?: () => void }) => {
  const { health, isPaused, runtime } = useHermes();

  const getStatusText = () => {
    if (!health) return 'Offline';
    if (isPaused) return 'Paused';
    if (runtime.listening_state === 'listening') return 'Listening';
    if (runtime.listening_state === 'thinking' || runtime.listening_state === 'processing') return 'Thinking';
    if (runtime.listening_state === 'speaking' || runtime.listening_state === 'responding') return 'Speaking';
    return 'Ready';
  };

  return (
    <div className="surface-titlebar app-region-drag fixed left-0 right-0 top-0 z-50 flex h-12 select-none items-center justify-between px-4">
      {/* Brand */}
      <div className="app-region-no-drag flex flex-1 items-center gap-2.5 overflow-hidden">
        <div className="relative flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-[var(--border-default)] bg-[var(--accent-gradient)] shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={3.5}
            strokeLinecap="square"
            className="h-3 w-3 text-[var(--text-primary)]"
            aria-hidden="true"
          >
            <path d="M7 4v16M17 4v16M7 12h10" />
          </svg>
          <span
            className={`absolute -bottom-0.5 -right-0.5 h-1.5 w-1.5 rounded-full border-2 border-[var(--bg-base)] transition-colors duration-500 ${
              health
                ? 'bg-[var(--state-ready)] shadow-[0_0_6px_var(--state-ready-glow)]'
                : 'bg-[var(--state-error)] shadow-[0_0_6px_var(--state-error-glow)]'
            }`}
            aria-hidden="true"
          />
        </div>
        <span className="font-display text-[12px] font-bold tracking-[-0.005em] text-[var(--text-primary)]">
          Hermes
        </span>
        <span className="eyebrow text-[9px] tracking-[0.2em]">Voice Bridge</span>
      </div>

      {/* Central Status */}
      <div className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 flex items-center justify-center pointer-events-none">
        <span className={`eyebrow px-3 py-1 rounded-full border bg-[var(--surface-1)] transition-colors duration-300 ${
          runtime?.listening_state === 'listening' ? 'border-[var(--accent-primary)] text-[var(--accent-primary)] shadow-[0_0_12px_var(--accent-primary-glow)]' : 
          'border-[var(--border-subtle)] text-[var(--text-tertiary)]'
        }`}>
          {getStatusText()}
        </span>
      </div>

      {/* Window controls */}
      <div className="app-region-no-drag flex items-center gap-1">
        <button
          onClick={onToggleMini || (() => api.minimizeToTray())}
          className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--text-tertiary)] transition-colors hover:bg-[var(--surface-1)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--shadow-focus)]"
          title="Mini Mode"
          aria-label="Mini Mode"
        >
          <Minus className="h-3.5 w-3.5" strokeWidth={2.2} />
        </button>
        <button
          onClick={() => api.maximizeWindow()}
          className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--text-tertiary)] transition-colors hover:bg-[var(--surface-1)] hover:text-[var(--text-primary)] focus-visible:outline-none focus-visible:shadow-[var(--shadow-focus)]"
          title="Maximize"
          aria-label="Maximize"
        >
          <Square className="h-3 w-3" strokeWidth={2.2} />
        </button>
        <button
          onClick={() => api.minimizeToTray()}
          className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--text-tertiary)] transition-colors hover:bg-[rgba(248,113,113,0.10)] hover:text-[var(--state-error)] focus-visible:outline-none focus-visible:shadow-[var(--shadow-focus)]"
          title="Close to Tray"
          aria-label="Close to Tray"
        >
          <X className="h-3.5 w-3.5" strokeWidth={2.2} />
        </button>
      </div>
    </div>
  );
};
