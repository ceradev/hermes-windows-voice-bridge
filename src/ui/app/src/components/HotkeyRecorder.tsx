import React, { useState, useEffect, useCallback, useRef } from 'react';
import { X, Zap } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export interface HotkeyRecorderProps {
  value: string;
  onChange: (hotkey: string) => void;
  placeholder?: string;
}

type RecordingState = 'idle' | 'recording' | 'captured';

const MODIFIER_KEYS = new Set(['Control', 'Alt', 'Shift', 'Meta']);

function normalizeKey(key: string): string {
  const map: Record<string, string> = {
    Control: 'CTRL',
    Alt: 'ALT',
    Shift: 'SHIFT',
    Meta: 'WIN',
    ArrowUp: 'UP',
    ArrowDown: 'DOWN',
    ArrowLeft: 'LEFT',
    ArrowRight: 'RIGHT',
  };
  return map[key] || key.toUpperCase();
}

function isValidShortcut(keys: Set<string>): boolean {
  const hasModifier = Array.from(keys).some((k) => MODIFIER_KEYS.has(k));
  const hasNonModifier = Array.from(keys).some((k) => !MODIFIER_KEYS.has(k));
  return hasModifier && hasNonModifier;
}

export const HotkeyRecorder: React.FC<HotkeyRecorderProps> = ({
  value,
  onChange,
  placeholder,
}) => {
  const { t } = useLanguage();
  const resolvedPlaceholder = placeholder ?? t('shortcuts.recorder_placeholder', 'CLICK TO RECORD');
  const [state, setState] = useState<RecordingState>(value ? 'captured' : 'idle');
  const [pressedKeys, setPressedKeys] = useState<Set<string>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);

  const hotkeyParts = value
    ? value.split('+').map((k) => k.trim()).filter(Boolean)
    : [];

  const stopRecording = useCallback(() => {
    setState('idle');
    setPressedKeys(new Set());
  }, []);

  const handleCapture = useCallback(
    (keys: Set<string>) => {
      if (!isValidShortcut(keys)) return;
      const combo = Array.from(keys)
        .sort((a, b) => {
          const aMod = MODIFIER_KEYS.has(a) ? 0 : 1;
          const bMod = MODIFIER_KEYS.has(b) ? 0 : 1;
          return aMod - bMod;
        })
        .map(normalizeKey)
        .join('+');
      onChange(combo);
      setState('captured');
      setPressedKeys(new Set());
    },
    [onChange]
  );

  useEffect(() => {
    if (state !== 'recording') return;

    const handleKeyDown = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (e.key === 'Escape') {
        stopRecording();
        return;
      }

      setPressedKeys((prev) => {
        const next = new Set(prev);
        next.add(e.key);
        return next;
      });
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();

      setPressedKeys((prev) => {
        const next = new Set(prev);
        // Remove all instances of the key (handles repeated keydowns)
        next.delete(e.key);

        if (next.size === 0 && prev.size > 0) {
          // All keys released - capture the previous set
          requestAnimationFrame(() => handleCapture(prev));
        }

        return next;
      });
    };

    window.addEventListener('keydown', handleKeyDown, { capture: true });
    window.addEventListener('keyup', handleKeyUp, { capture: true });

    return () => {
      window.removeEventListener('keydown', handleKeyDown, { capture: true });
      window.removeEventListener('keyup', handleKeyUp, { capture: true });
    };
  }, [state, stopRecording, handleCapture]);

  const handleClick = () => {
    if (state === 'recording') {
      stopRecording();
    } else {
      setState('recording');
      setPressedKeys(new Set());
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange('');
    setState('idle');
  };

  const isRecording = state === 'recording';
  const isCaptured = state === 'captured' || (!isRecording && value);

  const ariaLabel = isRecording
    ? t('shortcuts.recorder_aria_recording', 'Recording hotkey, press escape to cancel')
    : t('shortcuts.recorder_aria_idle', 'Click to record hotkey');
  const clearAriaLabel = t('shortcuts.recorder_clear', 'Clear hotkey');

  return (
    <div
      ref={containerRef}
      onClick={handleClick}
      tabIndex={0}
      role="button"
      aria-label={ariaLabel}
      className={`
        group relative flex items-center gap-3 px-4 py-3
        rounded-[var(--radius-control)] border cursor-pointer
        transition-all duration-300 select-none outline-none
        min-w-[260px] min-h-[52px]
        ${
          isRecording
            ? 'border-[var(--state-warn)] bg-[var(--surface-0)] shadow-[0_0_16px_var(--state-warn-glow)] animate-pulse'
            : isCaptured
            ? 'border-[var(--border-strong)] bg-[var(--surface-1)] hover:border-[var(--text-primary)]'
            : 'border-[var(--border-default)] bg-[var(--surface-0)] hover:border-[var(--border-strong)]'
        }
      `}
    >
      {isRecording && (
        <Zap
          size={16}
          className="text-[var(--state-warn)] animate-pulse shrink-0"
          aria-hidden="true"
        />
      )}

      <div className="flex flex-1 items-center gap-2 overflow-hidden">
        {isRecording ? (
          <span className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-[var(--state-warn)] animate-pulse">
            {t('shortcuts.recorder_listening', 'LISTENING…')}
          </span>
        ) : isCaptured && hotkeyParts.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {hotkeyParts.map((key, index) => (
              <kbd
                key={`${key}-${index}`}
                className="
                  inline-flex items-center px-2.5 py-1
                  bg-[var(--surface-2)] border border-[var(--border-strong)]
                  rounded-[4px] font-mono font-bold text-[11px]
                  text-[var(--text-primary)] shadow-[inset_0_-2px_0_rgba(255,255,255,0.05)]
                  uppercase tracking-wider
                "
              >
                {key}
              </kbd>
            ))}
          </div>
        ) : (
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--text-secondary)]">
            {resolvedPlaceholder}
          </span>
        )}
      </div>

      {isCaptured && hotkeyParts.length > 0 && (
        <button
          onClick={handleClear}
          className="
            flex items-center justify-center w-6 h-6 rounded
            text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-2)]
            transition-colors focus:outline-none shrink-0
          "
          aria-label={clearAriaLabel}
          tabIndex={0}
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
};
