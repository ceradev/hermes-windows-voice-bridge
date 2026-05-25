import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchConfig, fetchDevices, invokeAction, saveConfig } from './lib/api';
import type { VoiceConfig, VoiceDevice, VoiceSnapshot } from './types';

const badgeStyles: Record<string, string> = {
  running: 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30',
  listening: 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30',
  paused: 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30',
  warn: 'bg-blue-500/15 text-blue-300 ring-1 ring-blue-500/30',
  stopped: 'bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30',
  unknown: 'bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/30',
};

const defaultConfig: VoiceConfig = {
  mic_device: '',
  hotkey: '',
  feedback_mode: '',
  feedback_voice: '',
  wake_phrases: '',
  stt_language: '',
  stt_model: '',
  wake_energy: '',
  silence_rms: '',
  block_seconds: '',
  wake_window_seconds: '',
  silence_timeout_seconds: '',
  max_command_seconds: '',
  webhook_sync: '',
  webhook_timeout: '',
};

function Card({ title, value, detail, accent }: { title: string; value: string; detail: string; accent: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-slate-900/70 p-4 shadow-glow backdrop-blur">
      <div className={`h-1 w-16 rounded-full ${accent}`} />
      <div className="mt-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">{title}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
      <div className="mt-1 text-sm text-slate-400">{detail}</div>
    </div>
  );
}

function Button({
  label,
  onClick,
  tone = 'default',
}: {
  label: string;
  onClick: () => Promise<void>;
  tone?: 'default' | 'primary' | 'ghost' | 'danger';
}) {
  const [busy, setBusy] = useState(false);
  const classes =
    tone === 'primary'
      ? 'bg-sky-400 text-slate-950 hover:bg-sky-300'
      : tone === 'danger'
      ? 'bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/30 hover:bg-rose-500/25'
      : tone === 'ghost'
      ? 'bg-white/5 text-slate-200 ring-1 ring-white/8 hover:bg-white/10'
      : 'bg-slate-100 text-slate-950 hover:bg-white';

  return (
    <button
      onClick={async () => {
        setBusy(true);
        try {
          await onClick();
        } finally {
          setBusy(false);
        }
      }}
      className={`rounded-xl px-4 py-2 text-sm font-semibold transition disabled:cursor-wait disabled:opacity-70 ${classes}`}
      disabled={busy}
    >
      {busy ? 'Working…' : label}
    </button>
  );
}

function TextField({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</div>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-white/8 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-600 focus:border-sky-500/50"
      />
    </label>
  );
}

function TextAreaField({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="block">
      <div className="mb-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</div>
      <textarea
        rows={3}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-white/8 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-600 focus:border-sky-500/50"
      />
    </label>
  );
}

export default function App() {
  const [snapshot, setSnapshot] = useState<VoiceSnapshot | null>(null);
  const [devices, setDevices] = useState<VoiceDevice[]>([]);
  const [deviceError, setDeviceError] = useState('');
  const [statusError, setStatusError] = useState('');
  const [updatedAt, setUpdatedAt] = useState('');
  const [config, setConfig] = useState<VoiceConfig>(defaultConfig);
  const [saveNotice, setSaveNotice] = useState('');
  const [copyNotice, setCopyNotice] = useState('');
  const logsRef = useRef<HTMLPreElement | null>(null);

  const refreshDevices = useCallback(async () => {
    try {
      const data = await fetchDevices();
      setDevices(data.devices ?? []);
      setDeviceError(data.error || '');
    } catch (err) {
      setDeviceError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const refreshConfig = useCallback(async () => {
    try {
      const data = await fetchConfig();
      setConfig({ ...defaultConfig, ...(data.config ?? {}) });
      if (data.devices?.devices) setDevices(data.devices.devices);
      setDeviceError(data.devices?.error || '');
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const refreshOnce = useCallback(async () => {
    try {
      setStatusError('');
      const response = await fetch('/api/status');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = (await response.json()) as VoiceSnapshot;
      setSnapshot(data);
      setUpdatedAt(new Date().toLocaleTimeString());
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void refreshOnce();
    void refreshConfig();
  }, [refreshOnce, refreshConfig]);

  useEffect(() => {
    const es = new EventSource('/api/stream');
    es.addEventListener('snapshot', (event) => {
      const payload = JSON.parse((event as MessageEvent).data) as { snapshot: VoiceSnapshot };
      setSnapshot(payload.snapshot);
      setUpdatedAt(new Date().toLocaleTimeString());
      setStatusError('');
    });
    es.onerror = () => {
      setStatusError('Live stream disconnected; retrying…');
    };
    return () => es.close();
  }, []);

  useEffect(() => {
    const el = logsRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [snapshot?.logs]);

  const copyLogs = useCallback(async () => {
    const text = (snapshot?.logs ?? []).join('\n');
    if (!text) {
      setCopyNotice('No hay logs todavía');
      return;
    }
    await navigator.clipboard.writeText(text);
    setCopyNotice('Logs copiados');
    window.setTimeout(() => setCopyNotice(''), 2000);
  }, [snapshot?.logs]);

  const badgeClass = snapshot ? badgeStyles[snapshot.badge.state] ?? badgeStyles.unknown : badgeStyles.unknown;

  const cards = useMemo(() => {
    if (!snapshot) return [];
    return [
      {
        title: 'Tray',
        value: snapshot.summary.tray_running ? 'Running' : 'Stopped',
        detail: snapshot.processes.tray.length ? `PID ${snapshot.processes.tray[0].pid}` : 'No tray process detected',
        accent: snapshot.summary.tray_running ? 'bg-emerald-400' : 'bg-rose-400',
      },
      {
        title: 'Bridge',
        value: snapshot.summary.bridge_running ? 'Running' : 'Stopped',
        detail: snapshot.processes.bridge.length ? `PID ${snapshot.processes.bridge[0].pid}` : 'No bridge process detected',
        accent: snapshot.summary.bridge_running ? 'bg-emerald-400' : 'bg-rose-400',
      },
      {
        title: 'Mode',
        value: snapshot.summary.paused ? 'Paused' : snapshot.summary.mode || 'Unknown',
        detail: snapshot.summary.paused ? 'Shared control file says paused' : 'Live voice control active',
        accent: snapshot.summary.paused ? 'bg-amber-400' : 'bg-sky-400',
      },
      {
        title: 'Health',
        value: snapshot.badge.label,
        detail: snapshot.summary.last_error || snapshot.badge.hint,
        accent: snapshot.summary.health === 'stopped' ? 'bg-rose-400' : 'bg-violet-400',
      },
    ];
  }, [snapshot]);

  const setField = (key: keyof VoiceConfig, value: string) => setConfig((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="min-h-screen px-4 py-6 text-slate-100 md:px-6 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-3xl border border-white/8 bg-slate-950/70 p-6 shadow-glow backdrop-blur">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-500">Hermes Voice Bridge</div>
              <h1 className="mt-2 text-3xl font-semibold text-white md:text-4xl">React control panel</h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
                Live status, logs, microphone selection, wake phrases, hotkey, feedback and bridge controls.
              </p>
            </div>
            <div className={`inline-flex items-center gap-3 rounded-full px-4 py-2 text-sm font-semibold ${badgeClass}`}>
              <span className="h-2.5 w-2.5 rounded-full bg-current" />
              {snapshot ? snapshot.badge.label : 'Loading…'}
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {cards.map((card) => (
              <Card key={card.title} {...card} />
            ))}
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-slate-400">
            <span>Last refresh: {updatedAt || '—'}</span>
            <span>Version: {snapshot?.version || '—'}</span>
            {statusError ? <span className="text-rose-300">{statusError}</span> : <span>Live stream on</span>}
          </div>
        </header>

        <section className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
          <div className="space-y-6">
            <div className="rounded-3xl border border-white/8 bg-slate-950/70 p-5 shadow-glow backdrop-blur">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-white">Live status</h2>
                  <p className="text-sm text-slate-400">Pulled from the Python backend and streamed in real time.</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button label="Refresh now" onClick={refreshOnce} tone="ghost" />
                  <Button label="Probe" onClick={async () => { await invokeAction('probe'); await refreshOnce(); }} tone="primary" />
                  <Button label="Restart bridge" onClick={async () => { await invokeAction('restart-bridge'); await refreshOnce(); }} tone="danger" />
                  <Button label="Restart tray" onClick={async () => { await invokeAction('restart-tray'); await refreshOnce(); }} tone="danger" />
                  <Button label="Repair autostart" onClick={async () => { await invokeAction('repair-autostart'); await refreshOnce(); await refreshConfig(); }} tone="primary" />
                  <Button label="Open logs" onClick={async () => { await invokeAction('open-logs'); }} tone="ghost" />
                  <Button label="Open folder" onClick={async () => { await invokeAction('open-folder'); }} tone="ghost" />
                </div>
              </div>

              <pre className="mt-4 overflow-auto rounded-2xl border border-white/8 bg-slate-900/90 p-4 text-sm leading-6 text-slate-200">
                {(snapshot?.status_lines ?? ['No live status yet.']).join('\n')}
              </pre>
            </div>

            <div className="rounded-3xl border border-white/8 bg-slate-950/70 p-5 shadow-glow backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-white">Live logs</h2>
                  <p className="text-sm text-slate-400">Use this to catch errors and send them back to me.</p>
                </div>
                <div className="flex gap-2">
                  <Button label={snapshot?.control.paused ? 'Resume' : 'Pause'} onClick={async () => { await invokeAction(snapshot?.control.paused ? 'resume' : 'pause'); }} tone="ghost" />
                  <Button label="Start tray" onClick={async () => { await invokeAction('start-tray'); }} tone="primary" />
                  <Button label="Copy logs" onClick={copyLogs} tone="ghost" />
                </div>
              </div>
              <pre ref={logsRef} className="mt-4 max-h-[30rem] overflow-auto rounded-2xl border border-white/8 bg-slate-900/90 p-4 text-xs leading-5 text-slate-300">
                {(snapshot?.logs ?? ['Waiting for log lines…']).join('\n')}
              </pre>
              {copyNotice ? <div className="mt-2 text-xs text-sky-300">{copyNotice}</div> : null}
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-white/8 bg-slate-950/70 p-5 shadow-glow backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-white">Configuration</h2>
                  <p className="text-sm text-slate-400">Mic, wake phrases and timing. Save writes voice.env.</p>
                </div>
                <Button label="Refresh devices" onClick={refreshDevices} tone="ghost" />
              </div>

              <div className="mt-4 grid gap-3">
                <label className="block">
                  <div className="mb-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Microphone</div>
                  <select
                    value={config.mic_device}
                    onChange={(e) => setField('mic_device', e.target.value)}
                    className="w-full rounded-xl border border-white/8 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/50"
                  >
                    <option value="">Default microphone</option>
                    {devices.map((device) => (
                      <option key={device.index} value={device.index}>
                        #{device.index} · {device.name}
                      </option>
                    ))}
                  </select>
                  {deviceError ? <div className="mt-2 text-xs text-rose-300">{deviceError}</div> : null}
                </label>

                <div className="grid gap-3 md:grid-cols-2">
                  <TextField label="Hotkey" value={config.hotkey} onChange={(value) => setField('hotkey', value)} placeholder="ctrl+shift+h" />
                  <TextField label="Feedback mode" value={config.feedback_mode} onChange={(value) => setField('feedback_mode', value)} placeholder="both" />
                  <TextField label="Feedback voice" value={config.feedback_voice} onChange={(value) => setField('feedback_voice', value)} placeholder="en-US-GuyNeural" />
                  <TextField label="STT language" value={config.stt_language} onChange={(value) => setField('stt_language', value)} placeholder="es" />
                  <TextField label="STT model" value={config.stt_model} onChange={(value) => setField('stt_model', value)} placeholder="base" />
                  <TextField label="Wake energy" value={config.wake_energy} onChange={(value) => setField('wake_energy', value)} placeholder="0.008" />
                  <TextField label="Silence RMS" value={config.silence_rms} onChange={(value) => setField('silence_rms', value)} placeholder="0.008" />
                  <TextField label="Block seconds" value={config.block_seconds} onChange={(value) => setField('block_seconds', value)} placeholder="0.25" />
                  <TextField label="Wake window seconds" value={config.wake_window_seconds} onChange={(value) => setField('wake_window_seconds', value)} placeholder="2.0" />
                  <TextField label="Silence timeout seconds" value={config.silence_timeout_seconds} onChange={(value) => setField('silence_timeout_seconds', value)} placeholder="0.85" />
                  <TextField label="Max command seconds" value={config.max_command_seconds} onChange={(value) => setField('max_command_seconds', value)} placeholder="12.0" />
                  <TextField label="Webhook timeout" value={config.webhook_timeout} onChange={(value) => setField('webhook_timeout', value)} placeholder="120" />
                </div>

                <TextAreaField label="Wake phrases" value={config.wake_phrases} onChange={(value) => setField('wake_phrases', value)} placeholder="hermes, oye hermes, hey hermes" />

                <div className="grid gap-3 md:grid-cols-2">
                  <TextField label="Webhook sync" value={config.webhook_sync} onChange={(value) => setField('webhook_sync', value)} placeholder="1" />
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  <Button
                    label="Save settings"
                    onClick={async () => {
                      const result = await saveConfig(config);
                      setSaveNotice(result?.action?.message ? `${result.action.message}. Restart bridge to apply.` : 'Saved. Restart bridge to apply.');
                      await refreshOnce();
                      await refreshConfig();
                    }}
                    tone="primary"
                  />
                  <Button
                    label="Open voice.env"
                    onClick={async () => {
                      await invokeAction('open-env');
                    }}
                    tone="ghost"
                  />
                </div>
                {saveNotice ? <div className="text-sm text-emerald-300">{saveNotice}</div> : null}
              </div>
            </div>

            <div className="rounded-3xl border border-white/8 bg-slate-950/70 p-5 shadow-glow backdrop-blur">
              <h2 className="text-lg font-semibold text-white">Quick notes</h2>
              <ul className="mt-4 space-y-2 text-sm text-slate-400">
                <li>• The panel now streams live status and logs.</li>
                <li>• Microphone selection writes to <code>voice.env</code>.</li>
                <li>• Save settings usually needs a bridge restart.</li>
                <li>• If you find a bug, copy the live log lines here.</li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
