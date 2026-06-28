import { useEffect, useState } from 'react';
import { api, type HermesConfigUpdate } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { Save, Activity, Layout, Globe, Monitor } from 'lucide-react';
import { SectionHeader } from '../components/Layout/PageHeader';
import { useHermes } from '../contexts/HermesContext';

export const Settings = () => {
  const [config, setConfig] = useState<HermesConfigUpdate>({});
  const [isDirty, setIsDirty] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const { success, error } = useToast();
  const { overlayEnabled, overlayMode, updateOverlayConfig, refreshRuntime } = useHermes();

  useEffect(() => {
    api.getConfig().then(setConfig);
  }, []);

  const handleChange = <K extends keyof HermesConfigUpdate>(key: K, value: HermesConfigUpdate[K]) => {
    setConfig((current) => ({ ...current, [key]: value }));
    setIsDirty(true);
  };

  const handleSave = async () => {
    try {
      await api.updateConfig(config);
      setIsDirty(false);
      success('Settings saved successfully');
    } catch (e) {
      error('Failed to save settings');
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    if (isDirty) {
      await api.updateConfig(config);
      setIsDirty(false);
    }
    try {
      const isHealthy = await api.checkHealth();
      if (isHealthy) {
        success('Connected to Hermes successfully!');
      } else {
        error('Failed to connect to Hermes');
      }
    } catch (e) {
      error('Failed to connect to Hermes');
    } finally {
      setIsTesting(false);
    }
  };

  const handleOverlayToggle = async (next: boolean) => {
    try {
      await updateOverlayConfig({ overlay_enabled: next });
    } catch (e) {
      error('Failed to update overlay');
    }
  };

  const handleOverlayMode = async (mode: string) => {
    try {
      await updateOverlayConfig({ overlay_mode: mode });
    } catch (e) {
      error('Failed to update overlay mode');
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 h-full flex flex-col pb-24">
      <SectionHeader
        eyebrow="SYSTEM"
        title="Settings & Connection"
        description="Configure app behavior, overlay, and API connection."
      />

      <div className="flex-1 space-y-8 max-w-3xl">
        
        {/* API CONNECTION */}
        <section>
          <div className="flex items-center gap-3 border-b border-[var(--border-subtle)] pb-2 mb-4 text-[var(--text-secondary)]">
            <Globe size={16} />
            <h2 className="eyebrow">Backend Connection</h2>
          </div>
          
          <div className="surface-quiet p-5 space-y-5">
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] block mb-2">Endpoint URL</label>
              <input
                type="text"
                value={config.api_base_url || ''}
                onChange={(e) => handleChange('api_base_url', e.target.value)}
                className="field field-mono w-full text-sm"
                placeholder="http://91.98.36.55:8642"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] block mb-2">Webhook Secret</label>
              <input
                type="password"
                value={config.api_token || ''}
                onChange={(e) => handleChange('api_token', e.target.value)}
                className="field field-mono w-full text-sm"
                placeholder="sk-..."
              />
            </div>
            <div className="pt-2">
              <button onClick={handleTestConnection} disabled={isTesting} className="btn-base bg-[var(--surface-2)]">
                <Activity size={14} className={isTesting ? 'animate-pulse text-[var(--accent)]' : ''} />
                {isTesting ? 'Testing...' : 'Test Connection'}
              </button>
            </div>
          </div>
        </section>

        {/* OVERLAY */}
        <section>
          <div className="flex items-center gap-3 border-b border-[var(--border-subtle)] pb-2 mb-4 text-[var(--text-secondary)]">
            <Layout size={16} />
            <h2 className="eyebrow">Dynamic Overlay</h2>
          </div>
          
          <div className="surface-quiet space-y-0 divide-y divide-[var(--border-subtle)] overflow-hidden">
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">Enable Dynamic Pill</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">Shows status in an always-on-top pill</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked={overlayEnabled} onChange={(e) => handleOverlayToggle(e.target.checked)} className="sr-only peer" />
                <div className="w-11 h-6 bg-[var(--surface-3)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--accent)] shadow-inner"></div>
              </label>
            </div>
            
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">Overlay Mode</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">Choose the detail level</p>
              </div>
              <select
                value={overlayMode}
                onChange={(e) => handleOverlayMode(e.target.value)}
                className="field field-mono w-48 text-sm"
              >
                <option value="mini">Minimalist</option>
                <option value="full">Detailed</option>
              </select>
            </div>
          </div>
        </section>

        {/* APP BEHAVIOR */}
        <section>
          <div className="flex items-center gap-3 border-b border-[var(--border-subtle)] pb-2 mb-4 text-[var(--text-secondary)]">
            <Monitor size={16} />
            <h2 className="eyebrow">App Behavior</h2>
          </div>
          
          <div className="surface-quiet space-y-0 divide-y divide-[var(--border-subtle)] overflow-hidden">
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">Start with Windows</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">Launch Hermes automatically</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked={config.autostart || false} onChange={(e) => handleChange("autostart", e.target.checked)} className="sr-only peer" />
                <div className="w-11 h-6 bg-[var(--surface-3)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--accent)] shadow-inner"></div>
              </label>
            </div>
            
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">Minimize to Tray</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">Hide in the system tray instead of taskbar</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked={config.minimize_to_tray || false} onChange={(e) => handleChange("minimize_to_tray", e.target.checked)} className="sr-only peer" />
                <div className="w-11 h-6 bg-[var(--surface-3)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--accent)] shadow-inner"></div>
              </label>
            </div>
          </div>
        </section>

      </div>

      <div className="fixed bottom-8 right-8 z-40 transition-all duration-300 ease-out" style={{ transform: isDirty ? 'translateY(0) scale(1)' : 'translateY(20px) scale(0.95)', opacity: isDirty ? 1 : 0, pointerEvents: isDirty ? 'auto' : 'none' }}>
        <button onClick={handleSave} className="flex items-center gap-2 rounded-full bg-[var(--text-primary)] px-6 py-3 text-[13px] font-bold text-[var(--surface-0)] shadow-[var(--shadow-card-hover)] transition-all hover:bg-[var(--text-secondary)] hover:scale-105 active:scale-95">
          <Save size={16} /> Save Changes
        </button>
      </div>
    </div>
  );
};
