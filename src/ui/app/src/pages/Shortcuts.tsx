import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { Save } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export const Shortcuts = () => {
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
      success(t('shortcuts.success'));
    } catch (e) {
      error(t('shortcuts.error'));
    }
  };

  const hotkeyParts = (config.hotkey || "CTRL+SHIFT+H")
    .split('+')
    .map((key: string) => key.trim())
    .filter(Boolean);

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full">
      <div className="space-y-6 flex-1">
        <div className="glass-panel rounded-[var(--radius-panel)] p-8 transition-colors duration-300">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="font-mono text-[11px] tracking-[0.24em] uppercase text-gray-500 dark:text-gray-400">Hotkey Binding</p>
              <h3 className="font-bold text-gray-900 dark:text-white text-lg mt-1">{t('shortcuts.hotkey')}</h3>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-2">{t('shortcuts.hotkey_desc')}</p>
            </div>

            <div className="flex flex-wrap gap-2">
              {hotkeyParts.map((key: string, index: number) => (
                <kbd key={`${key}-${index}`} className="px-4 py-3 bg-gray-100 dark:bg-[#1a1a1a] border border-gray-300 dark:border-gray-600 rounded-[6px] font-mono font-bold text-sm text-gray-900 dark:text-white shadow-[inset_0_-2px_0_rgba(0,0,0,0.1)] dark:shadow-[inset_0_-2px_0_rgba(255,255,255,0.05)] uppercase">
                  {key}
                </kbd>
              ))}
            </div>
          </div>

          <div className="mt-6 border-t border-black/10 dark:border-white/10 pt-6">
            <label className="mb-2 block font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-gray-500 dark:text-gray-400">
              Press your shortcut to change
            </label>
            <input
              type="text"
              value={config.hotkey || ""}
              onChange={(e) => handleChange("hotkey", e.target.value)}
              className="w-full rounded-[var(--radius-control)] border border-black/20 bg-black/[0.03] px-4 py-3 font-mono text-sm font-bold uppercase text-gray-900 shadow-[inset_0_2px_4px_rgba(0,0,0,0.08)] transition-colors focus:border-gray-900 focus:outline-none dark:border-white/20 dark:bg-white/[0.04] dark:text-white dark:focus:border-white"
              placeholder="CTRL+SHIFT+H"
            />
          </div>
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
          <Save size={18} /> {t('shortcuts.save')}
        </button>
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
