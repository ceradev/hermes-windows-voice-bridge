import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import type { SessionRecord } from '../types/webview';

const DEFAULT_TITLE = 'New chat';

function pickChromeTitle(sessions: SessionRecord[]): string {
  if (sessions.length === 0) return DEFAULT_TITLE;
  const active = sessions.find((s) => s.is_active === true || s.is_active === 1);
  const latest = active ?? sessions[0];
  const name = latest.name?.trim();
  return name || DEFAULT_TITLE;
}

export function useChromeSessionTitle(): string {
  const [title, setTitle] = useState(DEFAULT_TITLE);

  const refresh = useCallback(async () => {
    try {
      const sessions = await api.getSessions();
      setTitle(pickChromeTitle(sessions));
    } catch {
      setTitle(DEFAULT_TITLE);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const onUpdate = () => void refresh();
    window.addEventListener('hermes_new_message', onUpdate);
    return () => window.removeEventListener('hermes_new_message', onUpdate);
  }, [refresh]);

  return title;
}
