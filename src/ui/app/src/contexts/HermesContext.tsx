import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { api, RuntimeState } from '../services/api';

type RuntimeSnapshot = RuntimeState['runtime'] & {
  hotkey?: string;
  mic_device?: number | null;
  mic_device_name?: string;
  mic_device_hostapi?: number | null;
  overlay_enabled?: boolean;
  overlay_mode?: string;
  overlay_x?: number | null;
  overlay_y?: number | null;
  overlay_visible?: boolean;
  listening_state?: string;
  overlay_detail?: string;
};

interface HermesContextType {
  health: boolean;
  healthChecked: boolean;
  config: Record<string, unknown>;
  messages: Array<{ id: string; role: string; content: string; timestamp?: string }>;
  audioLevel: number;
  isPaused: boolean;
  runtime: RuntimeSnapshot;
  runtimeLoaded: boolean;
  overlayEnabled: boolean;
  overlayMode: string;
  overlayX: number | null;
  overlayY: number | null;
  overlayVisible: boolean;
  listeningState: string;
  overlayDetail: string;
  updateConfig: (updates: Record<string, unknown>) => Promise<void>;
  updateOverlayConfig: (updates: {
    overlay_enabled?: boolean;
    overlay_mode?: string;
  }) => Promise<void>;
  togglePause: () => Promise<void>;
  restartApp: () => Promise<void>;
  refreshMessages: () => Promise<void>;
  refreshRuntime: () => Promise<void>;
}

const DEFAULT_RUNTIME: RuntimeSnapshot = {
  connection_status: 'unknown',
  hotkey: '',
  mic_device: null,
  mic_device_name: '',
  mic_device_hostapi: null,
  overlay_enabled: true,
  overlay_mode: 'mini',
  overlay_x: null,
  overlay_y: null,
  overlay_visible: false,
  listening_state: 'idle',
  overlay_detail: '',
};

const HermesContext = createContext<HermesContextType | undefined>(undefined);

const pickRuntime = (snapshot: RuntimeState | null | undefined): RuntimeSnapshot => {
  const runtime = snapshot?.runtime;
  if (!runtime) return { ...DEFAULT_RUNTIME };
  return {
    ...DEFAULT_RUNTIME,
    ...runtime,
  };
};

export const HermesProvider = ({ children }: { children: ReactNode }) => {
  const [health, setHealth] = useState(false);
  const [healthChecked, setHealthChecked] = useState(false);
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [messages, setMessages] = useState<Array<{ id: string; role: string; content: string; timestamp?: string }>>([]);
  const [audioLevel, setAudioLevel] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [runtime, setRuntime] = useState<RuntimeSnapshot>({ ...DEFAULT_RUNTIME });
  const [runtimeLoaded, setRuntimeLoaded] = useState(false);

  const loadInitialData = async () => {
    if (!(window as unknown as { pywebview?: { api?: unknown } }).pywebview?.api) {
      await new Promise<void>((resolve) => {
        const handler = () => {
          window.removeEventListener('pywebviewready', handler);
          resolve();
        };
        window.addEventListener('pywebviewready', handler);
        const pollInterval = setInterval(() => {
          if ((window as unknown as { pywebview?: { api?: unknown } }).pywebview?.api) {
            clearInterval(pollInterval);
            window.removeEventListener('pywebviewready', handler);
            resolve();
          }
        }, 100);
      });
    }

    const healthStatus = await api.checkHealth();
    setHealth(healthStatus);
    setHealthChecked(true);

    const configData = await api.getConfig();
    setConfig(configData);

    const sessions = await api.getSessions() as Array<{ id: string; is_active: boolean }>;
    if (sessions && sessions.length > 0) {
      const active = sessions.find((s) => s.is_active);
      if (active) {
        setActiveSessionId(active.id);
      }
    }

    try {
      const snapshot = await api.getRuntimeState();
      setRuntime(pickRuntime(snapshot));
    } catch (err) {
      console.error('Initial runtime fetch error:', err);
    } finally {
      setRuntimeLoaded(true);
    }
  };

  const fetchMessages = async (sessionId: string) => {
    const msgs = await api.getMessages(sessionId) as Array<{ id: string; role: string; content: string; timestamp?: string }>;
    setMessages(msgs.slice(-20));
  };

  const refreshMessages = async () => {
    if (activeSessionId) {
      await fetchMessages(activeSessionId);
    } else {
      const sessions = await api.getSessions() as Array<{ id: string; is_active: boolean }>;
      if (sessions && sessions.length > 0) {
        const active = sessions.find((s) => s.is_active);
        if (active) {
          setActiveSessionId(active.id);
        }
      }
    }
  };

  const refreshConfig = useCallback(async () => {
    const configData = await api.getConfig();
    setConfig(configData);
  }, []);

  const refreshRuntime = useCallback(async () => {
    try {
      const snapshot = await api.getRuntimeState();
      setRuntime(pickRuntime(snapshot));
    } catch (err) {
      console.error('Runtime refresh error:', err);
    }
  }, []);

  useEffect(() => {
    loadInitialData();

    let isPolling = true;
    const poll = async () => {
      if (!isPolling) return;

      if ((window as unknown as { pywebview?: { api?: unknown } }).pywebview?.api) {
        try {
          const currentHealth = await api.checkHealth();
          setHealth(currentHealth);
          setHealthChecked(true);

          const configData = await api.getConfig();
          if (configData && Object.keys(configData).length > 0) {
            setConfig(configData);
          }

          const sessions = await api.getSessions() as Array<{ id: string; is_active: boolean }>;
          if (sessions && sessions.length > 0) {
            const active = sessions.find((s) => s.is_active);
            if (active) {
              setActiveSessionId(prev => prev !== active.id ? active.id : prev);
            }
          }

          try {
            const snapshot = await api.getRuntimeState();
            setRuntime(pickRuntime(snapshot));
            setRuntimeLoaded(true);
          } catch (runtimeErr) {
            console.error('Runtime poll error:', runtimeErr);
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }

      if (isPolling) {
        setTimeout(poll, 2000);
      }
    };

    poll();

    const handleAudioLevel = (e: unknown) => {
      const rawLevel = (e as { detail?: number }).detail ?? 0;
      const normalized = Math.min(rawLevel * 8, 1);
      setAudioLevel(normalized);
    };

    const handleConfigUpdated = () => {
      refreshConfig().catch((err) => {
        console.error('Config refresh error:', err);
      });
      refreshRuntime().catch((err) => {
        console.error('Runtime refresh error:', err);
      });
    };

    window.addEventListener('hermes_audio_level', handleAudioLevel as EventListener);
    window.addEventListener('hermes_config_updated', handleConfigUpdated as EventListener);

    return () => {
      isPolling = false;
      window.removeEventListener('hermes_audio_level', handleAudioLevel as EventListener);
      window.removeEventListener('hermes_config_updated', handleConfigUpdated as EventListener);
    };
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      fetchMessages(activeSessionId);
    }

    const handleNewMessage = () => {
      refreshMessages();
    };

    window.addEventListener('hermes_new_message', handleNewMessage as EventListener);

    return () => {
      window.removeEventListener('hermes_new_message', handleNewMessage as EventListener);
    };
  }, [activeSessionId]);

  const updateConfig = async (updates: Record<string, unknown>) => {
    const previousConfig = config;
    const newConfig = { ...config, ...updates };
    setConfig(newConfig);

    // Optimistically reflect overlay-related fields into the runtime snapshot
    // so the UI stays coherent while the backend round-trip completes.
    if (
      'overlay_enabled' in updates ||
      'overlay_mode' in updates ||
      'overlay_x' in updates ||
      'overlay_y' in updates
    ) {
      setRuntime((prev) => ({
        ...prev,
        overlay_enabled:
          'overlay_enabled' in updates
            ? Boolean(updates.overlay_enabled)
            : prev.overlay_enabled,
        overlay_mode:
          'overlay_mode' in updates && updates.overlay_mode !== undefined
            ? String(updates.overlay_mode).toLowerCase()
            : prev.overlay_mode,
        overlay_x:
          'overlay_x' in updates ? (updates.overlay_x as number | null) : prev.overlay_x,
        overlay_y:
          'overlay_y' in updates ? (updates.overlay_y as number | null) : prev.overlay_y,
      }));
    }

    try {
      const updated = await api.updateConfig(updates);
      if (!updated) {
        throw new Error('update_config returned false');
      }
      // Pull the authoritative snapshot from the backend after applying the
      // update — this is the source of truth for overlay visibility / detail.
      refreshRuntime().catch((err) => {
        console.error('Post-update runtime refresh error:', err);
      });
    } catch (err) {
      setConfig(previousConfig);
      throw err;
    }
  };

  const updateOverlayConfig = async (updates: {
    overlay_enabled?: boolean;
    overlay_mode?: string;
  }) => {
    await updateConfig(updates as Record<string, unknown>);
  };

  const togglePause = async () => {
    const newPaused = !isPaused;
    setIsPaused(newPaused);
    if ((api as unknown as { pauseApp?: (p: boolean) => Promise<void> }).pauseApp) {
      await (api as unknown as { pauseApp: (p: boolean) => Promise<void> }).pauseApp(newPaused);
    }
    refreshRuntime().catch((err) => {
      console.error('Pause runtime refresh error:', err);
    });
  };

  const restartApp = async () => {
    if ((api as unknown as { restartApp?: () => Promise<void> }).restartApp) {
      await (api as unknown as { restartApp: () => Promise<void> }).restartApp();
    }
  };

  const overlayEnabled = runtime.overlay_enabled ?? true;
  const overlayMode = runtime.overlay_mode ?? 'mini';
  const overlayX = runtime.overlay_x ?? null;
  const overlayY = runtime.overlay_y ?? null;
  const overlayVisible = runtime.overlay_visible ?? false;
  const listeningState = runtime.listening_state ?? 'idle';
  const overlayDetail = runtime.overlay_detail ?? '';

  return (
    <HermesContext.Provider
      value={{
        health,
        healthChecked,
        config,
        messages,
        audioLevel,
        isPaused,
        runtime,
        runtimeLoaded,
        overlayEnabled,
        overlayMode,
        overlayX,
        overlayY,
        overlayVisible,
        listeningState,
        overlayDetail,
        updateConfig,
        updateOverlayConfig,
        togglePause,
        restartApp,
        refreshMessages,
        refreshRuntime,
      }}
    >
      {children}
    </HermesContext.Provider>
  );
};

export const useHermes = () => {
  const context = useContext(HermesContext);
  if (context === undefined) {
    throw new Error('useHermes must be used within a HermesProvider');
  }
  return context;
};