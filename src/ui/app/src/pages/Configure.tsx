import { useEffect, useMemo, useState } from 'react';
import { api, type HermesConfigUpdate, type ShortcutsConfig } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { Save, Mic, Keyboard, Volume2, Headphones } from 'lucide-react';
import { PageHeader } from '../components/Layout/PageHeader';
import { Section } from '../components/Layout/Section';
import { HotkeyRecorder } from '../components/HotkeyRecorder';
import type { AudioDevice } from '../types/webview';

export const Configure = () => {
  const [config, setConfig] = useState<HermesConfigUpdate>({});
  const [shortcuts, setShortcuts] = useState<ShortcutsConfig>({ hotkey: '', mute_hotkey: '', pause_hotkey: '' });
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [isDirty, setIsDirty] = useState(false);
  const { success, error } = useToast();

  useEffect(() => {
    Promise.all([
      api.getConfig(),
      api.getShortcuts(),
      api.getAudioDevices()
    ]).then(([cfg, shrt, devs]) => {
      setConfig(cfg);
      setShortcuts(shrt);
      setDevices(devs);
    });
  }, []);

  const handleConfigChange = <K extends keyof HermesConfigUpdate>(key: K, value: HermesConfigUpdate[K]) => {
    setConfig((current) => ({ ...current, [key]: value }));
    setIsDirty(true);
  };

  const handleShortcutChange = (key: keyof ShortcutsConfig, value: string) => {
    setShortcuts({ ...shortcuts, [key]: value });
    setIsDirty(true);
  };

  const handleSave = async () => {
    try {
      await api.updateConfig(config);
      await api.updateShortcuts(shortcuts);
      setIsDirty(false);
      success('Configuration saved successfully');
    } catch (e) {
      error('Failed to save configuration');
    }
  };

  const wakePhrases = useMemo<string[]>(() => {
    if (Array.isArray(config.wake_phrases)) return config.wake_phrases;
    if (typeof config.wake_phrases === 'string') return config.wake_phrases.split(',').map((s: string) => s.trim()).filter(Boolean);
    return [];
  }, [config.wake_phrases]);

  return (
    <div className="flex h-full flex-col pb-16">
      <PageHeader
        title="Voice & shortcuts"
        description="Wake words, microphone, hotkeys, and text-to-speech."
      />

      <div className="ds-stack max-w-3xl flex-1">
        <Section title="Voice detection" icon={Mic} description="Sensitivity and recording limits.">
          <div className="ds-stack">
            <div>
              <div className="flex justify-between mb-1">
                <label className="text-sm font-medium">Wake energy threshold</label>
                <span className="text-mono text-xs text-[var(--text-tertiary)]">{config.wake_energy ?? 0.008}</span>
              </div>
              <input type="range" min="0.001" max="0.05" step="0.001" value={config.wake_energy ?? 0.008} onChange={(e) => handleConfigChange("wake_energy", parseFloat(e.target.value))} className="w-full h-1.5 bg-[var(--surface-3)] rounded-lg appearance-none cursor-pointer" />
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <label className="text-sm font-medium">Silence timeout</label>
                <span className="text-mono text-xs text-[var(--text-tertiary)]">{config.silence_timeout_seconds ?? 2.5}s</span>
              </div>
              <input type="range" min="0.5" max="5.0" step="0.1" value={config.silence_timeout_seconds ?? 2.5} onChange={(e) => handleConfigChange("silence_timeout_seconds", parseFloat(e.target.value))} className="w-full h-1.5 bg-[var(--surface-3)] rounded-lg appearance-none cursor-pointer" />
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <label className="text-sm font-medium">Max command duration</label>
                <span className="text-mono text-xs text-[var(--text-tertiary)]">{config.max_command_seconds ?? 15}s</span>
              </div>
              <input type="range" min="5" max="60" step="1" value={config.max_command_seconds ?? 15} onChange={(e) => handleConfigChange("max_command_seconds", parseInt(e.target.value))} className="w-full h-1.5 bg-[var(--surface-3)] rounded-lg appearance-none cursor-pointer" />
            </div>
          </div>
        </Section>

        <Section title="Input & wake words" icon={Headphones} description="Microphone device and activation phrases.">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] block mb-2">Microphone Device</label>
              <select
                value={config.mic_device ?? ''}
                onChange={(e) => handleConfigChange('mic_device', e.target.value ? parseInt(e.target.value) : null)}
                className="field field-mono w-full text-sm"
              >
                <option value="">System Default</option>
                {devices.map((d) => (
                  <option key={d.index} value={d.index}>{d.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] block mb-2">Wake Phrases (comma separated)</label>
              <input
                type="text"
                value={wakePhrases.join(', ')}
                onChange={(e) => handleConfigChange('wake_phrases', e.target.value.split(',').map((s: string) => s.trim()))}
                className="field field-mono w-full text-sm"
                placeholder="hey hermes, hermes"
              />
            </div>
          </div>
        </Section>

        <Section title="Keyboard shortcuts" icon={Keyboard} description="Hotkeys for voice, mute, pause, and vision.">
          <div className="divide-y divide-[var(--border-subtle)] overflow-hidden rounded-[var(--radius-control)] border border-[var(--border-subtle)]">
            <div className="flex items-center justify-between p-4 bg-[var(--surface-inset)]">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">Voice Trigger</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">Start listening immediately</p>
              </div>
              <div className="w-48">
                <HotkeyRecorder value={shortcuts.hotkey} onChange={(v) => handleShortcutChange('hotkey', v)} />
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-[var(--surface-inset)]">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">Mute Microphone</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">Toggle microphone input</p>
              </div>
              <div className="w-48">
                <HotkeyRecorder value={shortcuts.mute_hotkey} onChange={(v) => handleShortcutChange('mute_hotkey', v)} />
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-[var(--surface-inset)]">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">Pause Assistant</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">Temporarily stop Hermes</p>
              </div>
              <div className="w-48">
                <HotkeyRecorder value={shortcuts.pause_hotkey} onChange={(v) => handleShortcutChange('pause_hotkey', v)} />
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-[var(--surface-inset)]">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">Vision Trigger</p>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">Include a screenshot with the prompt</p>
              </div>
              <div className="w-48">
                <HotkeyRecorder value={config.visual_hotkey || ''} onChange={(v) => handleConfigChange('visual_hotkey', v)} />
              </div>
            </div>
          </div>
        </Section>

        <Section title="Text to speech" icon={Volume2} description="How Hermes confirms commands audibly.">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Feedback Mode</label>
            <select
              value={config.feedback_mode || "both"}
              onChange={(e) => handleConfigChange("feedback_mode", e.target.value)}
              className="field field-mono w-48 text-sm text-center"
            >
              <option value="both">Voice + Beep</option>
              <option value="voice">Voice Only</option>
              <option value="beep">Beep Only</option>
              <option value="off">Silent</option>
            </select>
          </div>
        </Section>
      </div>

      <div className="fixed bottom-8 right-8 z-40 transition-all duration-300 ease-out" style={{ transform: isDirty ? 'translateY(0) scale(1)' : 'translateY(20px) scale(0.95)', opacity: isDirty ? 1 : 0, pointerEvents: isDirty ? 'auto' : 'none' }}>
        <button onClick={handleSave} className="flex items-center gap-2 rounded-full bg-[var(--text-primary)] px-6 py-3 text-[13px] font-bold text-[var(--surface-0)] shadow-[var(--shadow-card-hover)] transition-all hover:bg-[var(--text-secondary)] hover:scale-105 active:scale-95">
          <Save size={16} /> Save Changes
        </button>
      </div>
    </div>
  );
};
