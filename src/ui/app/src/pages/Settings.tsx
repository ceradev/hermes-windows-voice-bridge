import { useEffect, useState } from 'react';
import { api, type HermesConfigUpdate } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { Save, Activity, Layout, Globe, Monitor, KeyRound } from 'lucide-react';
import { PageHeader } from '../components/Layout/PageHeader';
import { Section } from '../components/Layout/Section';
import { useHermes } from '../contexts/HermesContext';

export const Settings = () => {
  const [config, setConfig] = useState<HermesConfigUpdate>({});
  const [isDirty, setIsDirty] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const { success, error } = useToast();
  const { overlayEnabled, overlayMode, updateOverlayConfig } = useHermes();

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
    <div className="flex h-full flex-col pb-16">
      <PageHeader
        title="Settings"
        description="Hermes API for in-app voice and chat replies. Webhook is optional."
      />

      <div className="ds-stack max-w-3xl flex-1">
        <Section
          title="Hermes API"
          icon={KeyRound}
          description="Primary connection. Voice and chat responses appear and are spoken in this app."
        >
          <div className="ds-stack">
            <div>
              <label className="ds-label mb-2 block">API base URL</label>
              <input
                type="text"
                value={config.api_base_url || ''}
                onChange={(e) => handleChange('api_base_url', e.target.value)}
                className="field field-mono w-full text-sm"
                placeholder="http://91.98.36.55:8642"
              />
            </div>
            <div>
              <label className="ds-label mb-2 block">API token</label>
              <input
                type="password"
                value={config.api_token || ''}
                onChange={(e) => handleChange('api_token', e.target.value)}
                className="field field-mono w-full text-sm"
                placeholder="Bearer / client key"
              />
              <p className="text-caption mt-1 text-[var(--state-warn)]">
                Valor de <code className="font-mono text-[12px]">API_SERVER_KEY</code> en tu VPS (puerto 8642).
                No es <code className="font-mono text-[12px]">webhook_secret</code> — ese solo firma el webhook en :8644.
              </p>
            </div>
            <div className="pt-1">
              <button onClick={handleTestConnection} disabled={isTesting} className="btn-base bg-[var(--surface-2)]">
                <Activity size={14} className={isTesting ? 'animate-pulse text-[var(--accent)]' : ''} />
                {isTesting ? 'Testing...' : 'Test Connection'}
              </button>
            </div>
          </div>
        </Section>

        <Section
          title="Webhook (optional)"
          icon={Globe}
          description="Only if you still route events through the gateway. Discord or other external deliver on the VPS is optional — not required for this app."
        >
          <div className="ds-stack">
            <div>
              <label className="ds-label mb-2 block">Webhook URL</label>
              <input
                type="text"
                value={config.webhook_url || ''}
                onChange={(e) => handleChange('webhook_url', e.target.value)}
                className="field field-mono w-full text-sm"
                placeholder="http://localhost:8644/webhooks/voice"
              />
            </div>
            <div>
              <label className="ds-label mb-2 block">Webhook secret</label>
              <input
                type="password"
                value={config.webhook_secret || ''}
                onChange={(e) => handleChange('webhook_secret', e.target.value)}
                className="field field-mono w-full text-sm"
                placeholder="secreto del webhook"
              />
            </div>
            <div>
              <label className="ds-label mb-2 block">User ID (optional)</label>
              <input
                type="text"
                value={config.webhook_user_id || ''}
                onChange={(e) => handleChange('webhook_user_id', e.target.value)}
                className="field field-mono w-full text-sm"
                placeholder="cesar"
              />
              <p className="text-caption mt-1">Groups messages in the same remote session when using webhook mode.</p>
            </div>
            <div className="flex items-center justify-between rounded-[var(--radius-control)] border border-[var(--border-subtle)] bg-[var(--surface-inset)] px-4 py-3">
              <div>
                <p className="text-sm font-medium">Wait for sync reply</p>
                <p className="text-caption mt-0.5">Keep the webhook HTTP request open until Hermes answers inline</p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input
                  type="checkbox"
                  checked={config.webhook_sync !== false}
                  onChange={(e) => handleChange('webhook_sync', e.target.checked)}
                  className="peer sr-only"
                />
                <div className="peer h-6 w-11 rounded-full bg-[var(--surface-3)] shadow-inner after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all peer-checked:bg-[var(--accent)] peer-checked:after:translate-x-full" />
              </label>
            </div>
          </div>
        </Section>

        <Section title="Overlay" icon={Layout} description="On-screen status while listening and thinking.">
          <div className="divide-y divide-[var(--border-subtle)] overflow-hidden rounded-[var(--radius-control)] border border-[var(--border-subtle)]">
            <div className="flex items-center justify-between bg-[var(--surface-inset)] p-4">
              <div>
                <p className="text-[15px] font-medium text-[var(--text-primary)]">Enable overlay</p>
                <p className="text-caption mt-0.5">Status pill always on top</p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input type="checkbox" checked={overlayEnabled} onChange={(e) => handleOverlayToggle(e.target.checked)} className="peer sr-only" />
                <div className="peer h-6 w-11 rounded-full bg-[var(--surface-3)] shadow-inner after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all peer-checked:bg-[var(--accent)] peer-checked:after:translate-x-full" />
              </label>
            </div>

            <div className="flex items-center justify-between bg-[var(--surface-inset)] p-4">
              <div>
                <p className="text-[15px] font-medium text-[var(--text-primary)]">Overlay mode</p>
                <p className="text-caption mt-0.5">Detail level</p>
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
        </Section>

        <Section title="App behavior" icon={Monitor} description="Startup and tray preferences.">
          <div className="divide-y divide-[var(--border-subtle)] overflow-hidden rounded-[var(--radius-control)] border border-[var(--border-subtle)]">
            <div className="flex items-center justify-between bg-[var(--surface-inset)] p-4">
              <div>
                <p className="text-[15px] font-medium text-[var(--text-primary)]">Start with Windows</p>
                <p className="text-caption mt-0.5">Launch automatically at sign-in</p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input type="checkbox" checked={config.autostart || false} onChange={(e) => handleChange('autostart', e.target.checked)} className="peer sr-only" />
                <div className="peer h-6 w-11 rounded-full bg-[var(--surface-3)] shadow-inner after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all peer-checked:bg-[var(--accent)] peer-checked:after:translate-x-full" />
              </label>
            </div>

            <div className="flex items-center justify-between bg-[var(--surface-inset)] p-4">
              <div>
                <p className="text-[15px] font-medium text-[var(--text-primary)]">Minimize to tray</p>
                <p className="text-caption mt-0.5">Hide in system tray instead of taskbar</p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input type="checkbox" checked={config.minimize_to_tray || false} onChange={(e) => handleChange('minimize_to_tray', e.target.checked)} className="peer sr-only" />
                <div className="peer h-6 w-11 rounded-full bg-[var(--surface-3)] shadow-inner after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all peer-checked:bg-[var(--accent)] peer-checked:after:translate-x-full" />
              </label>
            </div>
          </div>
        </Section>
      </div>

      <div className="fixed bottom-8 right-8 z-40 transition-all duration-300 ease-out" style={{ transform: isDirty ? 'translateY(0) scale(1)' : 'translateY(20px) scale(0.95)', opacity: isDirty ? 1 : 0, pointerEvents: isDirty ? 'auto' : 'none' }}>
        <button onClick={handleSave} className="btn-primary flex items-center gap-2 rounded-full px-5 py-2.5 text-[15px] font-semibold shadow-[var(--shadow-card)]">
          <Save size={16} /> Save Changes
        </button>
      </div>
    </div>
  );
};
