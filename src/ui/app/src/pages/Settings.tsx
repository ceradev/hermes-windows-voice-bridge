import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { Save } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export const Settings = () => {
  const [config, setConfig] = useState<any>({});
  const [initialConfig, setInitialConfig] = useState<any>({});
  const [isDirty, setIsDirty] = useState(false);
  const { success, error } = useToast();
  const { t } = useLanguage();

  useEffect(() => {
    api.getConfig().then(data => {
      setConfig(data);
      setInitialConfig(data);
    });
  }, []);

  const handleChange = (key: string, value: any) => {
    setConfig((prev: any) => ({ ...prev, [key]: value }));
    setIsDirty(true);
  };

  const handleSave = async () => {
    try {
      await api.updateConfig(config);
      setInitialConfig(config);
      setIsDirty(false);
      success(t('settings.success'));
    } catch (e) {
      error(t('settings.error'));
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full">
      <div className="space-y-4 flex-1">
        <div className="bg-white dark:bg-[#111] border border-gray-100 dark:border-gray-800 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none rounded-[1.5rem] p-6 flex items-center justify-between transition-colors duration-300">
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white">{t('settings.autostart')}</h3>
            <p className="text-sm font-medium text-gray-500 mt-1">{t('settings.autostart_desc')}</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" checked={config.autostart || false} onChange={(e) => handleChange("autostart", e.target.checked)} className="sr-only peer" />
            <div className="w-14 h-7 bg-gray-200 dark:bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-gray-900 dark:peer-checked:bg-white dark:peer-checked:after:bg-gray-900 shadow-inner"></div>
          </label>
        </div>

        <div className="bg-white dark:bg-[#111] border border-gray-100 dark:border-gray-800 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none rounded-[1.5rem] p-6 flex items-center justify-between transition-colors duration-300">
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white">{t('settings.minimize')}</h3>
            <p className="text-sm font-medium text-gray-500 mt-1">{t('settings.minimize_desc')}</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" checked={config.minimize_to_tray || false} onChange={(e) => handleChange("minimize_to_tray", e.target.checked)} className="sr-only peer" />
            <div className="w-14 h-7 bg-gray-200 dark:bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-gray-900 dark:peer-checked:bg-white dark:peer-checked:after:bg-gray-900 shadow-inner"></div>
          </label>
        </div>

        <div className="bg-white dark:bg-[#111] border border-gray-100 dark:border-gray-800 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none rounded-[1.5rem] p-6 transition-colors duration-300">
          <h3 className="font-bold text-gray-900 dark:text-white mb-4">Atajos de Teclado (Hotkeys)</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-1 block">Atajo de Voz</label>
              <input 
                type="text" 
                value={config.hotkey || "ctrl+shift+space"} 
                onChange={(e) => handleChange("hotkey", e.target.value)} 
                className="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-xl px-4 py-3 text-sm text-gray-900 dark:text-white font-medium focus:outline-none focus:border-gray-900/50 dark:focus:border-white/50 transition-all shadow-inner"
                placeholder="Ej. ctrl+shift+space"
              />
            </div>
            <div>
              <label className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-1 block">Atajo de Visión de Escritorio</label>
              <input 
                type="text" 
                value={config.visual_hotkey || "ctrl+shift+v"} 
                onChange={(e) => handleChange("visual_hotkey", e.target.value)} 
                className="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-xl px-4 py-3 text-sm text-gray-900 dark:text-white font-medium focus:outline-none focus:border-gray-900/50 dark:focus:border-white/50 transition-all shadow-inner"
                placeholder="Ej. ctrl+shift+v"
              />
              <p className="text-xs text-gray-500 mt-2 font-medium">Pulsa este atajo para hablar con Hermes adjuntando una captura de pantalla.</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-[#111] border border-gray-100 dark:border-gray-800 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none rounded-[1.5rem] p-6 transition-colors duration-300">
          <h3 className="font-bold text-gray-900 dark:text-white mb-6">{t('settings.vad_title')}</h3>
          
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-bold text-gray-700 dark:text-gray-300">{t('settings.vad_wake')}</span>
                <span className="text-xs font-bold text-gray-500">{config.wake_energy || 0.008}</span>
              </div>
              <input type="range" min="0.001" max="0.05" step="0.001" value={config.wake_energy || 0.008} onChange={(e) => handleChange("wake_energy", parseFloat(e.target.value))} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-gray-900 dark:accent-white" />
            </div>
            
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-bold text-gray-700 dark:text-gray-300">{t('settings.vad_silence')}</span>
                <span className="text-xs font-bold text-gray-500">{config.silence_rms || 0.008}</span>
              </div>
              <input type="range" min="0.001" max="0.05" step="0.001" value={config.silence_rms || 0.008} onChange={(e) => handleChange("silence_rms", parseFloat(e.target.value))} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-gray-900 dark:accent-white" />
            </div>
            
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-bold text-gray-700 dark:text-gray-300">{t('settings.vad_timeout')}</span>
                <span className="text-xs font-bold text-gray-500">{config.silence_timeout_seconds || 2.5}s</span>
              </div>
              <input type="range" min="0.5" max="5.0" step="0.1" value={config.silence_timeout_seconds || 2.5} onChange={(e) => handleChange("silence_timeout_seconds", parseFloat(e.target.value))} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-gray-900 dark:accent-white" />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 flex justify-end">
        <button 
          onClick={handleSave}
          disabled={!isDirty}
          className={`flex items-center gap-2 px-6 py-3 rounded-full font-bold shadow-sm transition-all duration-200 ${
            isDirty 
              ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/25 shadow-lg scale-100' 
              : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed scale-95'
          }`}
        >
          <Save size={18} /> {t('settings.save')}
        </button>
      </div>
    </div>
  );
};
