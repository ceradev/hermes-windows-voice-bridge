import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X, Bell, Check, Trash2 } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  timestamp: number;
  read: boolean;
}

interface ToastContextType {
  toasts: ToastItem[];
  notifications: ToastItem[];
  unreadCount: number;
  addToast: (title: string, message?: string, type?: ToastType) => void;
  markRead: (id: string) => void;
  markAsRead: (id: string) => void;
  markAllRead: () => void;
  markAllAsRead: () => void;
  removeToast: (id: string) => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  clearNotifications: () => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  toast: (title: string, messageOrType?: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

const STORAGE_KEY = 'hermes_notifications_v2';

function safeId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
}

function loadFromStorage(): ToastItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is ToastItem =>
      typeof item === 'object' &&
      typeof item.id === 'string' &&
      typeof item.type === 'string' &&
      typeof item.title === 'string' &&
      typeof item.timestamp === 'number' &&
      typeof item.read === 'boolean'
    );
  } catch {
    return [];
  }
}

function saveToStorage(toasts: ToastItem[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toasts));
  } catch {
    // quota exceeded or unavailable — silently skip
  }
}

const TOAST_ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
  warning: AlertTriangle,
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>(() => loadFromStorage());

  useEffect(() => {
    saveToStorage(toasts);
  }, [toasts]);

  const addToast = useCallback((title: string, message?: string, type: ToastType = 'info') => {
    const newToast: ToastItem = {
      id: safeId(),
      type,
      title,
      message,
      timestamp: Date.now(),
      read: false,
    };
    setToasts(prev => [newToast, ...prev].slice(0, 200));
  }, []);

  const markRead = useCallback((id: string) => {
    setToasts(prev =>
      prev.map(t => t.id === id ? { ...t, read: true } : t)
    );
  }, []);

  const markAllRead = useCallback(() => {
    setToasts(prev => prev.map(t => ({ ...t, read: true })));
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);

  const success = useCallback((title: string, message?: string) => addToast(title, message, 'success'), [addToast]);
  const error = useCallback((title: string, message?: string) => addToast(title, message, 'error'), [addToast]);
  const info = useCallback((title: string, message?: string) => addToast(title, message, 'info'), [addToast]);
  const warning = useCallback((title: string, message?: string) => addToast(title, message, 'warning'), [addToast]);
  const toast = useCallback((title: string, messageOrType?: string, type: ToastType = 'info') => {
    if (messageOrType === 'success' || messageOrType === 'error' || messageOrType === 'info' || messageOrType === 'warning') {
      addToast(title, undefined, messageOrType);
      return;
    }
    addToast(title, messageOrType, type);
  }, [addToast]);

  const unreadCount = toasts.filter(t => !t.read).length;

  return (
      <ToastContext.Provider value={{
        toasts,
        notifications: toasts,
        unreadCount,
        addToast,
        markRead,
        markAsRead: markRead,
        markAllRead,
        markAllAsRead: markAllRead,
        removeToast,
        removeNotification: removeToast,
        clearAll,
        clearNotifications: clearAll,
        success,
        error,
        info,
      warning,
      toast,
    }}>
      {children}
      {/* Inline toast notifications */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3">
        <AnimatePresence>
          {toasts.slice(0, 3).map(t => {
            const Icon = TOAST_ICONS[t.type] ?? Info;
            const iconColorMap = {
              success: 'text-[var(--state-ready)]',
              error: 'text-[var(--state-error)]',
              info: 'text-[var(--accent-primary)]',
              warning: 'text-[var(--state-warn)]',
            };
            const borderMap = {
              success: 'border-[var(--state-ready)]/30',
              error: 'border-[var(--state-error)]/30',
              info: 'border-[var(--border-default)]',
              warning: 'border-[var(--state-warn)]/30',
            };
            return (
              <motion.div
                key={t.id}
                initial={{ opacity: 0, y: 50, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
                className={`flex items-center gap-3 px-5 py-4 bg-[var(--surface-1)] rounded-[var(--radius-lg)] border min-w-[300px] max-w-md shadow-card ${borderMap[t.type] ?? borderMap.info}`}
              >
                <Icon size={20} className={`shrink-0 ${iconColorMap[t.type] ?? iconColorMap.info}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-heading text-[var(--text-primary)]">{t.title}</p>
                  {t.message && <p className="text-body text-[var(--text-secondary)] mt-0.5">{t.message}</p>}
                </div>
                <button onClick={() => removeToast(t.id)} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors focus:outline-none p-1">
                  <X size={16} />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
};
