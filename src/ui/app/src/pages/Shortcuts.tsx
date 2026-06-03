import React, { useEffect, useMemo, useState } from 'react';
import { api, type ShortcutsConfig } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useLanguage } from '../contexts/LanguageContext';
import { HotkeyRecorder } from '../components/HotkeyRecorder';
import { SectionHeader } from '../components/Layout/PageHeader';
import {
  Mic,
  VolumeX,
  Pause,
  Play,
  Save,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react';

interface ShortcutRow {
  key: keyof ShortcutsConfig;
  label: string;
  description: string;
  icon: React.ReactNode;
  testLabel: string;
}

const shortcutRows: ShortcutRow[] = [
  {
    key: 'hotkey',
    label: 'Voice Trigger',
    description: 'Start listening for a voice command.',
    icon: <Mic size={18} className="text-emerald-400" />,
    testLabel: 'TRIGGER',
  },
  {
    key: 'mute_hotkey',
    label: 'Mute Microphone',
    description: 'Silence the microphone input instantly.',
    icon: <VolumeX size={18} className="text-amber-400" />,
    testLabel: 'MUTE',
  },
  {
    key: 'pause_hotkey',
    label: 'Pause Assistant',
    description: 'Temporarily stop all voice processing.',
    icon: <Pause size={18} className="text-sky-400" />,
    testLabel: 'PAUSE',
  },
];

function findConflicts(shortcuts: ShortcutsConfig): string[] {
  const map = new Map<string, string[]>();
  (Object.entries(shortcuts) as [keyof ShortcutsConfig, string][]).forEach(
    ([key, value]) => {
      if (!value) return;
      const existing = map.get(value) || [];
      existing.push(key);
      map.set(value, existing);
    }
  );

  const conflicts: string[] = [];
  map.forEach((keys, combo) => {
    if (keys.length > 1) {
      conflicts.push(`Combo "${combo}" is assigned to ${keys.length} shortcuts.`);
    }
  });
  return conflicts;
}

const defaultShortcuts: ShortcutsConfig = {
  hotkey: 'CTRL+SHIFT+H',
  mute_hotkey: '',
  pause_hotkey: '',
};

export const Shortcuts = () => {
  const [shortcuts, setShortcuts] = useState<ShortcutsConfig>(defaultShortcuts);
  const [original, setOriginal] = useState<ShortcutsConfig>(defaultShortcuts);
  const [loading, setLoading] = useState(true);
  const { success, error } = useToast();
  const { t } = useLanguage();

  useEffect(() => {
    let cancelled = false;
    api
      .getShortcuts()
      .then((cfg) => {
        if (cancelled) return;
        setShortcuts(cfg);
        setOriginal(cfg);
      })
      .catch(() => {
        if (cancelled) return;
        error(t('shortcuts.error') || 'Failed to load shortcuts');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [error, t]);

  const isDirty = useMemo(() => {
    return (
      shortcuts.hotkey !== original.hotkey ||
      shortcuts.mute_hotkey !== original.mute_hotkey ||
      shortcuts.pause_hotkey !== original.pause_hotkey
    );
  }, [shortcuts, original]);

  const conflicts = useMemo(() => findConflicts(shortcuts), [shortcuts]);

  const handleChange = (key: keyof ShortcutsConfig, value: string) => {
    setShortcuts((prev) => ({ ...prev, [key]: value }));
  };

  const handleReset = () => {
    setShortcuts(original);
  };

  const handleSave = async () => {
    if (conflicts.length > 0) {
      error('Resolve conflicts before saving.');
      return;
    }
    try {
      await api.updateShortcuts(shortcuts);
      setOriginal(shortcuts);
      success(t('shortcuts.success') || 'Shortcuts saved successfully');
    } catch (e) {
      error(t('shortcuts.error') || 'Failed to save shortcuts');
    }
  };

  if (loading) {
    return (
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center">
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-gray-500 animate-pulse">
            Loading...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full">
      <div className="space-y-6 flex-1 pb-24">
        {/* Input Mapping Panel */}
        <div className="glass-panel rounded-[var(--radius-panel)] p-6 lg:p-8 transition-colors duration-300">
          <SectionHeader
            eyebrow="Input Mapping"
            title="Keyboard Shortcuts"
            description="Configure global hotkey combinations for voice control actions."
          />

          {conflicts.length > 0 && (
            <div className="mb-6 flex items-start gap-3 rounded-[var(--radius-control)] border border-red-500/30 bg-red-500/10 px-4 py-3">
              <AlertTriangle
                size={18}
                className="mt-0.5 shrink-0 text-red-400"
              />
              <div className="flex-1">
                <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-red-400">
                  Conflict Detected
                </p>
                <ul className="mt-1 space-y-0.5">
                  {conflicts.map((c, i) => (
                    <li
                      key={i}
                      className="text-xs font-medium text-red-300"
                    >
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <div className="flex flex-col gap-4">
            {shortcutRows.map((row) => (
              <div
                key={row.key}
                className="
                  flex flex-col gap-4 rounded-[var(--radius-control)]
                  border border-black/5 dark:border-white/5
                  bg-black/[0.02] dark:bg-white/[0.02]
                  p-4 lg:p-5
                  lg:flex-row lg:items-center lg:justify-between
                "
              >
                <div className="flex items-start gap-3 lg:w-56 shrink-0">
                  <div className="mt-0.5 shrink-0">{row.icon}</div>
                  <div>
                    <p className="font-mono text-xs font-bold uppercase tracking-[0.12em] text-gray-900 dark:text-white">
                      {row.label}
                    </p>
                    <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-0.5 leading-relaxed">
                      {row.description}
                    </p>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-1 lg:justify-end">
                  <HotkeyRecorder
                    value={shortcuts[row.key]}
                    onChange={(v) => handleChange(row.key, v)}
                  />
                  <button
                    onClick={() => {
                      // Simulate a brief flash or toast to indicate test
                      success(`Test: ${row.label}`);
                    }}
                    className="
                      flex items-center justify-center gap-2
                      rounded-[var(--radius-control)] border border-gray-700
                      bg-[#0a0a0a] px-5 py-3
                      font-mono text-[10px] font-bold uppercase tracking-[0.18em]
                      text-gray-400 hover:text-white hover:border-gray-500
                      transition-all duration-200
                      shadow-[inset_0_-2px_0_rgba(255,255,255,0.04)]
                      shrink-0
                    "
                  >
                    <Play size={14} />
                    <span>TEST</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Feedback Panel (TTS) */}
        <div className="glass-panel rounded-[var(--radius-panel)] p-6 lg:p-8 transition-colors duration-300">
          <p className="font-mono text-[11px] tracking-[0.24em] uppercase text-gray-500 dark:text-gray-400">
            Audio Feedback
          </p>
          <h3 className="font-bold text-gray-900 dark:text-white text-lg mt-1">
            Feedback Mode
          </h3>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-2 mb-6">
            How Hermes responds to voice commands and status changes.
          </p>
          <div className="flex items-center gap-3 rounded-[var(--radius-control)] border border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02] px-4 py-3">
            <span className="font-mono text-xs font-bold uppercase tracking-[0.12em] text-gray-400">
              Current:
            </span>
            <span className="font-mono text-xs font-bold text-emerald-400 uppercase tracking-[0.12em]">
              {original.hotkey || 'CTRL+SHIFT+H'}
            </span>
            <span className="text-gray-600 dark:text-gray-500">—</span>
            <span className="font-mono text-[10px] text-gray-500 dark:text-gray-400 uppercase">
              Trigger mapped to Voice
            </span>
          </div>
        </div>
      </div>

      {/* Sticky Save Bar */}
      <div
        className={`
          fixed bottom-0 left-0 right-0 z-40
          border-t border-black/10 dark:border-white/10
          bg-white/80 dark:bg-black/80
          backdrop-blur-md
          px-6 py-4
          transition-transform duration-300
          ${isDirty ? 'translate-y-0' : 'translate-y-full'}
        `}
        style={{ paddingLeft: 'var(--sidebar-width, 16rem)' }}
      >
        <div className="flex items-center justify-between max-w-5xl mx-auto">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-500 dark:text-gray-400">
            <RotateCcw size={14} />
            <span className="hidden sm:inline">Unsaved changes</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleReset}
              className="
                flex items-center gap-2 rounded-[var(--radius-control)]
                border border-gray-300 dark:border-gray-700
                px-5 py-2.5
                font-mono text-[10px] font-bold uppercase tracking-[0.18em]
                text-gray-600 dark:text-gray-400
                hover:bg-gray-100 dark:hover:bg-gray-800
                transition-all duration-200
              "
            >
              <RotateCcw size={14} />
              Reset
            </button>
            <button
              onClick={handleSave}
              disabled={conflicts.length > 0}
              className={`
                flex items-center gap-2 rounded-[var(--radius-control)]
                border px-5 py-2.5
                font-mono text-[10px] font-bold uppercase tracking-[0.18em]
                transition-all duration-200
                ${
                  conflicts.length > 0
                    ? 'border-gray-200 bg-gray-100 text-gray-400 cursor-not-allowed dark:border-gray-800 dark:bg-gray-900 dark:text-gray-600'
                    : 'border-gray-900 bg-gray-900 text-white hover:bg-black dark:border-white dark:bg-white dark:text-black dark:hover:bg-gray-200'
                }
              `}
            >
              <Save size={14} />
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export const TTS = () => {
  const [config, setConfig] = useState<any>({});
  const [isDirty, setIsDirty] = useState(false);
  const { success, error } = useToast();
  const { t } = useLanguage();

  useEffect(() => {
    api.getConfig().then(setConfig);
  }, []);

  const handleChange = (key: string, value: any) => {
    setConfig({ ...config, [key]: value });
    setIsDirty(true);
  };

  const handleSave = async () => {
    try {
      await api.updateConfig(config);
      setIsDirty(false);
      success(t('tts.success'));
    } catch (e) {
      error(t('tts.error'));
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full">
      <div className="space-y-6 flex-1">
        <div className="glass-panel rounded-[var(--radius-panel)] p-8 transition-colors duration-300">
          <p className="font-mono text-[11px] tracking-[0.24em] uppercase text-gray-500 dark:text-gray-400">Audio Feedback</p>
          <h3 className="font-bold text-gray-900 dark:text-white text-lg mt-1">{t('tts.feedback')}</h3>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-2 mb-6">{t('tts.feedback_desc')}</p>
          <select
            value={config.feedback_mode || "both"}
            onChange={(e) => handleChange("feedback_mode", e.target.value)}
            className="w-full rounded-[var(--radius-control)] border border-black/20 bg-black/[0.03] p-4 font-mono text-sm font-bold uppercase text-gray-900 shadow-[inset_0_2px_4px_rgba(0,0,0,0.08)] transition-colors focus:border-gray-900 focus:outline-none dark:border-white/20 dark:bg-white/[0.04] dark:text-white dark:focus:border-white"
          >
            <option value="both">{t('tts.both')}</option>
            <option value="voice">{t('tts.voice')}</option>
            <option value="beep">{t('tts.beep')}</option>
            <option value="off">{t('tts.off')}</option>
          </select>
        </div>
      </div>

      <div className="mt-8 flex justify-end">
        <button
          onClick={handleSave}
          disabled={!isDirty}
          className={`flex items-center gap-2 rounded-[var(--radius-control)] border px-6 py-3 font-mono text-xs font-bold uppercase tracking-[0.18em] shadow-[inset_0_-2px_0_rgba(0,0,0,0.12)] transition-all duration-200 ${
            isDirty
              ? 'border-gray-900 bg-gray-900 text-white hover:bg-black dark:border-white dark:bg-white dark:text-black dark:hover:bg-gray-200 scale-100'
              : 'border-gray-200 bg-gray-100 text-gray-400 cursor-not-allowed dark:border-gray-700 dark:bg-gray-800 dark:text-gray-500 scale-95'
          }`}
        >
          <Save size={18} /> {t('tts.save')}
        </button>
      </div>
    </div>
  );
};
