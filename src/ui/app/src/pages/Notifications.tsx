import React, { useEffect, useState } from 'react';
import { Bell, Layers, Save } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { useLanguage } from '../contexts/LanguageContext';
import { SectionHeader } from '../components/Layout/PageHeader';

export const Notifications = () => {
  const [config, setConfig] = useState<any>({});
  const [isDirty, setIsDirty] = useState(false);
  const { success, error } = useToast();
  const { t } = useLanguage();

  useEffect(() => {
    api.getConfig().then(setConfig);
  }, []);

  const handleChange = (key: string, value: boolean) => {
    setConfig((prev: any) => ({ ...prev, [key]: value }));
    setIsDirty(true);
  };

  const handleSave = async () => {
    try {
      await api.updateConfig({
        overlay_enabled: config.overlay_enabled ?? true,
        notifications_enabled: config.notifications_enabled ?? true,
      });
      setIsDirty(false);
      success(t('notifications.success'));
    } catch (e) {
      error(t('notifications.error'));
    }
  };

  const rockerClass =
    "peer h-6 w-11 rounded-full bg-gray-300 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-gray-900 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none dark:bg-gray-700 dark:peer-checked:bg-white dark:peer-checked:after:bg-gray-900";

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 flex h-full flex-col duration-500">
      <SectionHeader
        eyebrow={t('notifications.eyebrow')}
        title={t('notifications.title')}
        description={t('notifications.description')}
        action={
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={!isDirty}
            className={`flex items-center gap-2 rounded-[var(--radius-control)] border px-6 py-3 font-mono text-xs font-bold uppercase tracking-[0.18em] shadow-[inset_0_-2px_0_rgba(0,0,0,0.12)] transition-all duration-200 ${
              isDirty
                ? 'border-gray-900 bg-gray-900 text-white hover:bg-black dark:border-white dark:bg-white dark:text-black dark:hover:bg-gray-200 scale-100'
                : 'border-gray-200 bg-gray-100 text-gray-400 cursor-not-allowed dark:border-gray-700 dark:bg-gray-800 dark:text-gray-500 scale-95'
            }`}
          >
            <Save size={18} /> {t('notifications.save')}
          </button>
        }
      />

      <div className="space-y-6">
        <div className="glass-panel rounded-[var(--radius-panel)] p-6 lg:p-8 transition-colors duration-300">
          <p className="font-mono text-[11px] tracking-[0.24em] uppercase text-gray-500 dark:text-gray-400">
            {t('notifications.overlay_eyebrow')}
          </p>
          <h3 className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{t('notifications.overlay_title')}</h3>
          <p className="mt-2 mb-6 text-sm font-medium text-gray-500 dark:text-gray-400">{t('notifications.overlay_desc')}</p>
          <div className="flex items-center justify-between rounded-[var(--radius-control)] border border-black/10 bg-black/5 p-4 dark:border-white/10 dark:bg-white/5">
            <div className="flex items-center gap-3">
              <Layers className="h-5 w-5 text-sky-400" />
              <span className="text-sm font-bold text-gray-900 dark:text-gray-200">{t('notifications.overlay_toggle')}</span>
            </div>
            <label className="relative inline-flex items-center">
              <input
                type="checkbox"
                checked={config.overlay_enabled ?? true}
                onChange={(e) => handleChange('overlay_enabled', e.target.checked)}
                className="peer sr-only"
              />
              <div className={rockerClass} />
            </label>
          </div>
        </div>

        <div className="glass-panel rounded-[var(--radius-panel)] p-6 lg:p-8 transition-colors duration-300">
          <p className="font-mono text-[11px] tracking-[0.24em] uppercase text-gray-500 dark:text-gray-400">
            {t('notifications.desktop_eyebrow')}
          </p>
          <h3 className="mt-1 text-lg font-bold text-gray-900 dark:text-white">{t('notifications.desktop_title')}</h3>
          <p className="mt-2 mb-6 text-sm font-medium text-gray-500 dark:text-gray-400">{t('notifications.desktop_desc')}</p>
          <div className="flex items-center justify-between rounded-[var(--radius-control)] border border-black/10 bg-black/5 p-4 dark:border-white/10 dark:bg-white/5">
            <div className="flex items-center gap-3">
              <Bell className="h-5 w-5 text-amber-400" />
              <span className="text-sm font-bold text-gray-900 dark:text-gray-200">{t('notifications.desktop_toggle')}</span>
            </div>
            <label className="relative inline-flex items-center">
              <input
                type="checkbox"
                checked={config.notifications_enabled ?? true}
                onChange={(e) => handleChange('notifications_enabled', e.target.checked)}
                className="peer sr-only"
              />
              <div className={rockerClass} />
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};
