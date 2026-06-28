import React, { useEffect, useRef } from 'react';
import { WifiOff, RefreshCw } from 'lucide-react';
import { useHermes } from '../../contexts/HermesContext';
import { useToast } from '../../contexts/ToastContext';
import { useLanguage } from '../../contexts/LanguageContext';

const COOLDOWN_MS = 15000;

export const SystemAlerts: React.FC = () => {
  const { health, healthChecked } = useHermes();
  const { warning, success } = useToast();
  const { t } = useLanguage();

  const wasOnlineRef = useRef<boolean | null>(null);
  const cooldownRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const bannerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Skip until we've confirmed health state at least once
    if (!healthChecked) return;

    const isOnline = health;

    // First load — don't show a toast, just set the baseline
    if (wasOnlineRef.current === null) {
      wasOnlineRef.current = isOnline;
      return;
    }

    // Already in cooldown — nothing to do
    if (cooldownRef.current !== null) return;

    if (!isOnline && wasOnlineRef.current) {
      // Transition: online → offline
      warning(t('alerts.offline', 'Connection lost — Hermes is offline'));
      wasOnlineRef.current = false;

      // Set cooldown
      cooldownRef.current = setTimeout(() => {
        cooldownRef.current = null;
      }, COOLDOWN_MS);
    } else if (isOnline && !wasOnlineRef.current) {
      // Transition: offline → online
      success(t('alerts.offline_recovery', 'Connection restored'));
      wasOnlineRef.current = true;

      cooldownRef.current = setTimeout(() => {
        cooldownRef.current = null;
      }, COOLDOWN_MS);
    }
  }, [health, healthChecked, warning, success, t]);

  // Only show banner when offline AND we've confirmed health state
  if (!health || !healthChecked) {
    return (
      <div
        ref={bannerRef}
        className="glass-panel fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-2xl border border-red-500/30 bg-red-500/15 px-5 py-3 shadow-[0_8px_32px_rgba(239,68,68,0.25)] backdrop-blur-xl"
        style={{ backdropFilter: 'blur(16px)' }}
      >
        <WifiOff size={18} className="text-red-400" />
        <span className="font-mono text-xs font-bold uppercase tracking-[0.16em] text-red-300">
          {t('alerts.health_offline', 'Hermes is offline')}
        </span>
        <div className="flex items-center gap-1">
          <RefreshCw size={12} className="animate-spin text-red-400" />
        </div>
      </div>
    );
  }

  return null;
};