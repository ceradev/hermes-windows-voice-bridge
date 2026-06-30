import { useCallback, useEffect, useState } from 'react';
import { useHermes } from '../contexts/HermesContext';
import {
  Mic,
  Activity,
  Keyboard,
  Clock,
  ChevronRight,
  MessageSquare,
  Terminal,
  Wifi,
  Zap,
  History,
  Sliders,
  Pause,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { PageHeader } from '../components/Layout/PageHeader';
import { CardSection } from '../components/Layout/Section';
import type { ChatMessage, CustomCommand, RecentActivity, SessionRecord } from '../types/webview';

const formatTime = (value?: string) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
};

export const Home = () => {
  const { health, isPaused, runtime, config } = useHermes();
  const navigate = useNavigate();
  const [stats, setStats] = useState({ today: 0, week: 0 });
  const [recentInteractions, setRecentInteractions] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [activity, setActivity] = useState<RecentActivity[]>([]);
  const [commands, setCommands] = useState<CustomCommand[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [messageStats, recentMessages, sessionList, recentActivity, customCommands] = await Promise.all([
        api.getMessageStats(),
        api.getRecentMessages(6),
        api.getSessions(),
        api.getRecentActivity(),
        api.getCustomCommands(),
      ]);
      setStats(messageStats);
      setRecentInteractions(recentMessages);
      setSessions(sessionList.slice(0, 5));
      setActivity(recentActivity.slice(0, 6));
      setCommands(customCommands);
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    void loadData();
    const onNewMessage = () => void loadData();
    window.addEventListener('hermes_new_message', onNewMessage);
    return () => window.removeEventListener('hermes_new_message', onNewMessage);
  }, [loadData]);

  const getStatusText = () => {
    if (!health) return 'Offline';
    if (isPaused) return 'Paused';
    if (runtime.listening_state === 'listening') return 'Listening';
    if (runtime.listening_state === 'thinking' || runtime.listening_state === 'processing') return 'Thinking';
    if (runtime.listening_state === 'speaking' || runtime.listening_state === 'responding') return 'Speaking';
    return 'Ready';
  };

  const statusColor = !health
    ? 'text-[var(--state-error)]'
    : isPaused
      ? 'text-[var(--state-warn)]'
      : runtime.listening_state !== 'idle'
        ? 'text-[var(--state-ready)]'
        : 'text-[var(--text-primary)]';

  const lastUserMessage = recentInteractions.find((msg) => msg.role === 'user');
  const wakePhrases = Array.isArray(config.wake_phrases)
    ? config.wake_phrases
    : String(config.wake_phrases || 'hermes')
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

  const quickActions = [
    { label: 'Open chat', sub: 'Continue a conversation', path: '/chat', icon: MessageSquare },
    { label: 'Voice settings', sub: 'Mic, wake word, TTS', path: '/configure', icon: Sliders },
    { label: 'Custom commands', sub: `${commands.length} configured`, path: '/commands', icon: Terminal },
    { label: 'Connection', sub: health ? 'Hermes online' : 'Check API in Settings', path: '/settings', icon: Wifi },
  ];

  return (
    <div className="flex flex-col gap-4 pb-6">
      <PageHeader title="Overview" description="Status, recent chats, and shortcuts." />

      <div className="ds-card ds-card--hero ds-card-padded">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span
              className={`status-dot ${health ? (isPaused ? 'bg-[var(--state-warn)]' : 'bg-[var(--state-ready)]') : 'bg-[var(--state-error)]'}`}
            />
            <h2 className={`ds-page-title text-[22px] ${statusColor}`}>Hermes is {getStatusText().toLowerCase()}</h2>
            {isPaused && (
              <span className="ds-badge ds-badge--warn inline-flex items-center gap-1">
                <Pause size={12} /> Paused
              </span>
            )}
          </div>
          <p className="text-body text-[var(--text-secondary)]">
            {lastUserMessage ? (
              <span className="inline-flex items-center gap-2">
                <Mic size={16} className="shrink-0 text-[var(--accent)]" />
                <span className="truncate">
                  Last: &ldquo;{lastUserMessage.content.substring(0, 64)}
                  {lastUserMessage.content.length > 64 ? '…' : ''}&rdquo;
                </span>
              </span>
            ) : (
              'Say a wake phrase or use the hotkey to start.'
            )}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="ds-card ds-card-padded">
          <div className="mb-2 flex items-center justify-between">
            <Mic size={18} className="text-[var(--accent)]" />
            <span className="ds-badge capitalize">{runtime.listening_state}</span>
          </div>
          <p className="ds-card-title">Microphone</p>
          <p className="mt-1 text-caption">{config.mic_device_name || 'System default'}</p>
        </div>

        <div className="ds-card ds-card-padded">
          <div className="mb-2 flex items-baseline gap-2">
            <span className="ds-stat-value text-[24px]">{stats.today}</span>
            <span className="text-caption">today</span>
          </div>
          <p className="ds-card-title">Commands</p>
          <p className="mt-1 text-caption">{stats.week} this week</p>
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-[var(--surface-inset)]">
            <div
              className="h-full rounded-full bg-[var(--accent-gradient)]"
              style={{ width: `${Math.min(100, stats.week > 0 ? (stats.today / stats.week) * 100 : 0)}%` }}
            />
          </div>
        </div>

        <div className="ds-card ds-card-padded">
          <Keyboard size={18} className="mb-2 text-[var(--accent)]" />
          <p className="ds-card-title">Hotkey</p>
          <kbd className="mt-2 inline-block rounded-[var(--radius-control)] border border-[var(--border-default)] bg-[var(--surface-inset)] px-2 py-1 text-[12px] font-mono font-semibold">
            {String(config.hotkey || 'ctrl+shift+h').toUpperCase()}
          </kbd>
        </div>

        <div className="ds-card ds-card-padded">
          <Wifi size={18} className={`mb-2 ${health ? 'text-[var(--state-ready)]' : 'text-[var(--state-error)]'}`} />
          <p className="ds-card-title">Hermes</p>
          <p className={`mt-1 text-caption ${health ? 'text-[var(--state-ready)]' : 'text-[var(--state-error)]'}`}>
            {health ? 'API reachable' : 'Offline or misconfigured'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <CardSection
          title="Recent chats"
          icon={MessageSquare}
          action={
            <button
              type="button"
              onClick={() => navigate('/chat')}
              className="text-[14px] font-medium text-[var(--accent)] hover:underline"
            >
              All chats
            </button>
          }
        >
          <div className="p-1">
            {sessions.length === 0 ? (
              <div className="px-4 py-8 text-center text-caption">No chats yet</div>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => navigate('/chat')}
                  className="flex w-full items-center justify-between gap-3 rounded-[var(--radius-control)] px-4 py-3 text-left transition-colors hover:bg-[var(--surface-1)]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-[15px] font-medium text-[var(--text-primary)]">{session.name}</p>
                    <p className="text-caption">{formatTime(session.updated_at) || 'Recent'}</p>
                  </div>
                  {(session.is_active === true || session.is_active === 1) && (
                    <span className="ds-badge ds-badge--accent shrink-0">Active</span>
                  )}
                  <ChevronRight size={16} className="shrink-0 text-[var(--text-muted)]" />
                </button>
              ))
            )}
          </div>
        </CardSection>

        <CardSection title="Quick actions" icon={Zap}>
          <div className="grid grid-cols-1 gap-0.5 p-1 sm:grid-cols-2">
            {quickActions.map((item) => (
              <button
                key={item.path}
                type="button"
                onClick={() => navigate(item.path)}
                className="flex items-start gap-3 rounded-[var(--radius-control)] px-4 py-3 text-left transition-colors hover:bg-[var(--surface-1)]"
              >
                <item.icon size={18} className="mt-0.5 shrink-0 text-[var(--accent)]" />
                <div className="min-w-0">
                  <p className="text-[15px] font-medium text-[var(--text-primary)]">{item.label}</p>
                  <p className="text-caption">{item.sub}</p>
                </div>
              </button>
            ))}
          </div>
        </CardSection>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <CardSection
          title="Recent interactions"
          icon={Clock}
          className="lg:col-span-2"
          action={
            <button
              type="button"
              onClick={() => navigate('/chat')}
              className="text-[14px] font-medium text-[var(--accent)] hover:underline"
            >
              View all
            </button>
          }
        >
          <div className="p-1">
            {recentInteractions.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 px-4 py-10 text-[var(--text-tertiary)]">
                <MessageSquare size={28} className="opacity-30" />
                <p className="text-body">No recent interactions</p>
              </div>
            ) : (
              recentInteractions.map((msg) => (
                <button
                  key={msg.id}
                  type="button"
                  onClick={() => navigate('/chat')}
                  className="flex w-full items-center justify-between gap-3 rounded-[var(--radius-control)] px-4 py-3 text-left transition-colors hover:bg-[var(--surface-1)]"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border ${
                        msg.role === 'user'
                          ? 'border-[var(--border-subtle)] bg-[var(--surface-1)]'
                          : 'border-[var(--accent)]/30 bg-[var(--accent-soft)]'
                      }`}
                    >
                      {msg.role === 'user' ? (
                        <Mic size={16} className="text-[var(--text-secondary)]" />
                      ) : (
                        <Activity size={16} className="text-[var(--accent)]" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-[15px] font-medium text-[var(--text-primary)]">{msg.content}</p>
                      <p className="text-caption">{msg.role === 'user' ? 'You' : 'Hermes'}</p>
                    </div>
                  </div>
                  <ChevronRight size={18} className="shrink-0 text-[var(--text-tertiary)]" />
                </button>
              ))
            )}
          </div>
        </CardSection>

        <CardSection title="System log" icon={History}>
          <div className="custom-scrollbar max-h-[280px] overflow-y-auto p-2">
            {activity.length === 0 ? (
              <p className="px-2 py-6 text-center text-caption">No recent events</p>
            ) : (
              activity.map((item, index) => (
                <div
                  key={`${item.timestamp}-${index}`}
                  className="rounded-[var(--radius-control)] px-3 py-2.5 text-[13px] hover:bg-[var(--surface-1)]"
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="ds-badge">{item.type === 'voice' ? 'Voice' : 'Cmd'}</span>
                    <time className="text-caption font-mono">{formatTime(item.timestamp)}</time>
                  </div>
                  <p className="line-clamp-2 text-[var(--text-primary)]">{item.text}</p>
                </div>
              ))
            )}
          </div>
          <div className="border-t border-[var(--border-subtle)] px-5 py-3">
            <p className="ds-label mb-1">Wake phrases</p>
            <div className="flex flex-wrap gap-1.5">
              {wakePhrases.slice(0, 4).map((phrase) => (
                <span key={phrase} className="glass-chip rounded-[var(--radius-xs)] px-2 py-0.5 text-[12px] text-[var(--accent)]">
                  {phrase}
                </span>
              ))}
            </div>
          </div>
        </CardSection>
      </div>
    </div>
  );
};
