import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api } from '../services/api';

interface HermesContextType {
  health: boolean;
  config: any;
  messages: any[];
  audioLevel: number;
  isPaused: boolean;
  updateConfig: (updates: any) => Promise<void>;
  togglePause: () => Promise<void>;
  restartApp: () => Promise<void>;
  refreshMessages: () => Promise<void>;
}

const HermesContext = createContext<HermesContextType | undefined>(undefined);

export const HermesProvider = ({ children }: { children: ReactNode }) => {
  const [health, setHealth] = useState(false);
  const [config, setConfig] = useState<any>({});
  const [messages, setMessages] = useState<any[]>([]);
  const [audioLevel, setAudioLevel] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const loadInitialData = async () => {
    // Wait for pywebview API to be ready with no strict timeout
    if (!(window as any).pywebview?.api) {
      await new Promise<void>((resolve) => {
        const handler = () => {
          window.removeEventListener('pywebviewready', handler);
          resolve();
        };
        window.addEventListener('pywebviewready', handler);
        
        // Fallback polling in case we missed the event
        const pollInterval = setInterval(() => {
          if ((window as any).pywebview?.api) {
            clearInterval(pollInterval);
            window.removeEventListener('pywebviewready', handler);
            resolve();
          }
        }, 100);
      });
    }

    setHealth(await api.checkHealth());
    const configData = await api.getConfig();
    setConfig(configData);
    
    // Load sessions to find the active one
    const sessions = await api.getSessions();
    if (sessions && sessions.length > 0) {
      const active = sessions.find((s: any) => s.is_active);
      if (active) {
        setActiveSessionId(active.id);
        // fetchMessages is called by the other useEffect when activeSessionId changes
      }
    }
  };

  const fetchMessages = async (sessionId: string) => {
    const msgs = await api.getMessages(sessionId);
    // Keep last 20 messages for the UI
    setMessages(msgs.slice(-20));
  };

  const refreshMessages = async () => {
    if (activeSessionId) {
      await fetchMessages(activeSessionId);
    } else {
      // In case session wasn't loaded yet
      const sessions = await api.getSessions();
      if (sessions && sessions.length > 0) {
        const active = sessions.find((s: any) => s.is_active);
        if (active) {
          setActiveSessionId(active.id);
        }
      }
    }
  };

  // Run only once on mount
  useEffect(() => {
    loadInitialData();

    // Heartbeat: sequentially poll health, config and session if not fully loaded
    let isPolling = true;
    const poll = async () => {
      if (!isPolling) return;
      
      if ((window as any).pywebview?.api) {
        try {
          const currentHealth = await api.checkHealth();
          setHealth(currentHealth);
          
          // Also ensure config is loaded if it was empty
          const configData = await api.getConfig();
          if (configData && Object.keys(configData).length > 0) {
            setConfig(configData);
          }
          
          // Ensure we have an active session
          const sessions = await api.getSessions();
          if (sessions && sessions.length > 0) {
            const active = sessions.find((s: any) => s.is_active);
            if (active) {
              setActiveSessionId(prev => {
                if (prev !== active.id) return active.id;
                return prev;
              });
            }
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      }
      
      if (isPolling) {
        setTimeout(poll, 2000);
      }
    };
    
    poll();

    const handleAudioLevel = (e: any) => {
      // RMS is usually 0 to ~0.2. Normalize it for visual effect.
      const rawLevel = e.detail || 0;
      const normalized = Math.min(rawLevel * 8, 1);
      setAudioLevel(normalized);
    };

    window.addEventListener('hermes_audio_level', handleAudioLevel as EventListener);

    return () => {
      isPolling = false;
      window.removeEventListener('hermes_audio_level', handleAudioLevel as EventListener);
    };
  }, []);

  // Run when activeSessionId changes to fetch messages and listen to new ones
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

  const updateConfig = async (updates: any) => {
    const newConfig = { ...config, ...updates };
    setConfig(newConfig);
    await api.updateConfig(updates);
  };

  const togglePause = async () => {
    const newPaused = !isPaused;
    setIsPaused(newPaused);
    if (api.pauseApp) {
      await api.pauseApp(newPaused);
    }
  };

  const restartApp = async () => {
    if (api.restartApp) {
      await api.restartApp();
    }
  };

  return (
    <HermesContext.Provider 
      value={{ 
        health, 
        config, 
        messages, 
        audioLevel, 
        isPaused, 
        updateConfig, 
        togglePause, 
        restartApp,
        refreshMessages
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
