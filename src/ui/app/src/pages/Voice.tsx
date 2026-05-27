import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { Save, Activity, Key } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export const Voice = () => {
  const [devices, setDevices] = useState<any[]>([]);
  const [config, setConfig] = useState<any>({});
  const [isDirty, setIsDirty] = useState(false);
  const { success, error } = useToast();
  const { t } = useLanguage();
  
  useEffect(() => {
    api.getAudioDevices().then(setDevices);
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
      success(t('voice.success'));
    } catch (e) {
      error(t('voice.error'));
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full">
      <div className="space-y-6 flex-1">
        <div className="bg-white dark:bg-[#111] border border-gray-100 dark:border-gray-800 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none rounded-[1.5rem] p-8 transition-colors duration-300">
          <h3 className="font-bold text-gray-900 dark:text-white text-lg">{t('voice.input')}</h3>
          <p className="text-sm font-medium text-gray-500 mt-1 mb-6">{t('voice.input_desc')}</p>
          <select 
            value={config.mic_device ?? ""} 
            onChange={(e) => handleChange("mic_device", e.target.value ? parseInt(e.target.value) : null)}
            className="w-full bg-gray-50 dark:bg-[#0a0a0a] border border-gray-200 dark:border-gray-700 rounded-xl p-4 text-gray-900 dark:text-white font-medium text-sm focus:outline-none focus:border-gray-900 dark:focus:border-white transition-colors"
          >
            <option value="">{t('voice.default')}</option>
            {devices.map((d: any) => (
              <option key={d.index} value={d.index}>{d.name}</option>
            ))}
          </select>
        </div>
        
        <div className="bg-white dark:bg-[#111] border border-gray-100 dark:border-gray-800 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none rounded-[1.5rem] p-8 transition-colors duration-300">
          <h3 className="font-bold text-gray-900 dark:text-white text-lg">{t('voice.wake')}</h3>
          <p className="text-sm font-medium text-gray-500 mt-1 mb-6">{t('voice.wake_desc')}</p>
          <input 
            type="text" 
            value={config.wake_phrases ? config.wake_phrases.join(", ") : ""}
            onChange={(e) => handleChange("wake_phrases", e.target.value.split(",").map(s => s.trim()))}
            className="w-full bg-gray-50 dark:bg-[#0a0a0a] border border-gray-200 dark:border-gray-700 rounded-xl p-4 text-gray-900 dark:text-white font-medium text-sm focus:outline-none focus:border-gray-900 dark:focus:border-white transition-colors"
          />
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
          <Save size={18} /> {t('voice.save')}
        </button>
      </div>
    </div>
  );
};

export const Hermes = () => {
  const [config, setConfig] = useState<any>({});
  const [isDirty, setIsDirty] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const { success, error, toast } = useToast();
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
      success(t('hermes.success'));
    } catch (e) {
      error(t('hermes.error'));
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    // If dirty, save first to test the new URL/Token
    if (isDirty) {
      await api.updateConfig(config);
      setIsDirty(false);
    }
    
    try {
      const isHealthy = await api.checkHealth();
      if (isHealthy) {
        success(t('hermes.test_success'));
      } else {
        error(t('hermes.test_fail'));
      }
    } catch (e) {
      error(t('hermes.test_fatal'));
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full">
      <div className="space-y-6 flex-1">
        <div className="bg-white dark:bg-[#111] border border-gray-100 dark:border-gray-800 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none rounded-[1.5rem] p-8 transition-colors duration-300">
          <h3 className="font-bold text-gray-900 dark:text-white text-lg">{t('hermes.url')}</h3>
          <p className="text-sm font-medium text-gray-500 mt-1 mb-6">{t('hermes.url_desc')}</p>
          <input 
            type="text" 
            value={config.api_base_url || ""}
            onChange={(e) => handleChange("api_base_url", e.target.value)}
            className="w-full bg-gray-50 dark:bg-[#0a0a0a] border border-gray-200 dark:border-gray-700 rounded-xl p-4 text-gray-900 dark:text-white font-mono font-medium text-sm focus:outline-none focus:border-gray-900 dark:focus:border-white transition-colors"
            placeholder="http://91.98.36.55:8642"
          />
        </div>
        
        <div className="bg-white dark:bg-[#111] border border-gray-100 dark:border-gray-800 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-none rounded-[1.5rem] p-8 transition-colors duration-300">
          <div className="flex items-center gap-2 mb-1">
            <Key className="w-5 h-5 text-gray-900 dark:text-white" />
            <h3 className="font-bold text-gray-900 dark:text-white text-lg">{t('hermes.token')}</h3>
          </div>
          <p className="text-sm font-medium text-gray-500 mb-6">{t('hermes.token_desc')}</p>
          <input 
            type="password" 
            value={config.api_token || ""}
            onChange={(e) => handleChange("api_token", e.target.value)}
            className="w-full bg-gray-50 dark:bg-[#0a0a0a] border border-gray-200 dark:border-gray-700 rounded-xl p-4 text-gray-900 dark:text-white font-mono font-medium text-sm focus:outline-none focus:border-gray-900 dark:focus:border-white transition-colors"
            placeholder="sk-..."
          />
        </div>
      </div>

      <div className="mt-8 flex justify-between items-center">
        <button 
          onClick={handleTestConnection}
          disabled={isTesting}
          className="flex items-center gap-2 px-6 py-3 rounded-full font-bold bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        >
          <Activity size={18} className={isTesting ? "animate-pulse text-blue-500" : ""} /> 
          {isTesting ? t('hermes.testing') : t('hermes.test')}
        </button>
        
        <button 
          onClick={handleSave}
          disabled={!isDirty}
          className={`flex items-center gap-2 px-6 py-3 rounded-full font-bold shadow-sm transition-all duration-200 ${
            isDirty 
              ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/25 shadow-lg scale-100' 
              : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed scale-95'
          }`}
        >
          <Save size={18} /> {t('hermes.save')}
        </button>
      </div>
    </div>
  );
};
