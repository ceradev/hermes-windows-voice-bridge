import React, { useEffect, useState } from 'react';
import { Clock } from 'lucide-react';
import { api } from '../services/api';
import type { RecentActivity } from '../types';

const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    month: 'short',
    day: 'numeric',
  }).format(date);
};

export const History = () => {
  const [activity, setActivity] = useState<RecentActivity[]>([]);

  const loadActivity = async () => {
    const recentActivity = await api.getRecentActivity();
    setActivity(recentActivity);
  };

  useEffect(() => {
    loadActivity();

    const handleNewMessage = () => {
      loadActivity();
    };

    window.addEventListener('hermes_new_message', handleNewMessage);
    return () => window.removeEventListener('hermes_new_message', handleNewMessage);
  }, []);

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 flex h-full flex-col duration-500">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">Flight Recorder</p>
          <h2 className="text-3xl font-extrabold uppercase tracking-tighter text-gray-900 dark:text-white">Activity Ledger</h2>
          <p className="mt-1 text-sm font-semibold text-gray-500">Recent voice transcriptions and executed actions from this app session.</p>
        </div>
        <div className="rounded-[var(--radius-control)] border border-black/10 bg-black/5 px-4 py-2 font-mono text-xs font-bold uppercase tracking-[0.16em] text-gray-600 dark:border-white/10 dark:bg-white/10 dark:text-gray-300">
          Last {activity.length} events
        </div>
      </div>

      <div className="glass-panel flex min-h-0 flex-1 flex-col overflow-hidden rounded-[var(--radius-panel)] transition-all duration-300">
        <div className="grid shrink-0 grid-cols-[140px_56px_88px_1fr] border-b border-black/10 bg-black/5 px-5 py-3 font-mono text-[10px] font-extrabold uppercase tracking-[0.2em] text-gray-500 dark:border-white/10 dark:bg-white/5 dark:text-gray-400">
          <span>Timestamp</span>
          <span>Type</span>
          <span>Status</span>
          <span>Message Body</span>
        </div>

        <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto">
          {activity.length === 0 ? (
            <div className="flex h-full min-h-[360px] items-center justify-center p-6">
              <div className="glass-panel max-w-sm rounded-[var(--radius-panel)] border-black/10 p-8 text-center dark:border-white/10">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-[var(--radius-control)] border border-black/10 bg-black/5 text-gray-400 dark:border-white/10 dark:bg-white/5">
                  <Clock className="h-6 w-6" />
                </div>
                <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">No recent activity</p>
                <p className="mt-2 text-sm font-semibold text-gray-500 dark:text-gray-400">Voice commands and local actions will appear here.</p>
              </div>
            </div>
          ) : (
            <div className="pb-12">
              {activity.map((item, index) => {
                const isVoice = item.type === 'voice';
                const isSuccess = item.status === 'success';
                const typeCode = isVoice ? 'VOC' : 'CMD';

                return (
                  <div
                    key={`${item.timestamp}-${index}`}
                    className={`grid grid-cols-[140px_56px_88px_1fr] items-start border-b border-black/10 px-5 py-4 text-sm transition-colors hover:bg-black/5 dark:border-white/10 dark:hover:bg-white/5 ${isSuccess ? 'border-l-2 border-l-emerald-500/70' : 'border-l-2 border-l-red-500/70'}`}
                  >
                    <time className="font-mono text-xs font-bold uppercase leading-6 text-gray-500 dark:text-gray-400">{formatTimestamp(item.timestamp)}</time>
                    <span className="font-mono text-xs font-extrabold leading-6 tracking-[0.18em] text-gray-900 dark:text-gray-100">{typeCode}</span>
                    <span className={`w-fit border px-2 py-1 font-mono text-[10px] font-extrabold uppercase tracking-[0.14em] ${isSuccess ? 'border-emerald-500/25 text-emerald-700 dark:text-emerald-300' : 'border-red-500/25 text-red-700 dark:text-red-300'}`}>
                      {isSuccess ? 'OK' : 'ERR'}
                    </span>
                    <p className="whitespace-pre-wrap break-words text-sm font-semibold leading-6 text-gray-900 dark:text-gray-100">{item.text}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
