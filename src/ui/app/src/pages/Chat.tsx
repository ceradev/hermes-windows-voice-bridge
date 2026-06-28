import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { MessageSquare, Plus, Trash2, Copy, Clock, Globe, Volume2, Download, Activity } from 'lucide-react';
import { useToast } from '../contexts/ToastContext';
import { useLanguage } from '../contexts/LanguageContext';
import { SectionHeader } from '../components/Layout/PageHeader';
import type { RecentActivity, SessionRecord, ChatMessage } from '../types';

const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric',
  }).format(date);
};

export const Chat = () => {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activity, setActivity] = useState<RecentActivity[]>([]);
  const [activeSession, setActiveSession] = useState<SessionRecord | null>(null);
  const [viewMode, setViewMode] = useState<'chat' | 'activity'>('chat');
  const [inputText, setInputText] = useState("");
  const { toast } = useToast();
  const { t } = useLanguage();

  const loadData = async () => {
    const list = await api.getSessions();
    setSessions(list);
    
    if (viewMode === 'chat') {
      const active = list.find((s) => s.is_active);
      if (active) {
        setActiveSession(active);
        const msgs = await api.getMessages(active.id);
        setMessages(msgs);
      } else {
        setActiveSession(null);
        setMessages([]);
      }
    } else {
      const recentActivity = await api.getRecentActivity();
      setActivity(recentActivity);
    }
  };

  useEffect(() => {
    loadData();
    const handleNewMessage = () => loadData();
    window.addEventListener('hermes_new_message', handleNewMessage);
    return () => window.removeEventListener('hermes_new_message', handleNewMessage);
  }, [viewMode]);

  const handleSwitchSession = async (id: string) => {
    await api.switchSession(id);
    setViewMode('chat');
    await loadData();
  };

  const handleCreateSession = async () => {
    await api.createSession("New Session");
    setViewMode('chat');
    await loadData();
  };

  const handleDeleteSession = async (id: string) => {
    await api.deleteSession(id);
    await loadData();
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;
    const text = inputText;
    setInputText("");
    setMessages((prev) => [...prev, { role: "user" as const, content: text, id: Date.now() }]);
    await api.sendMessage(text);
    await loadData();
  };

  const handleExport = () => {
    if (!messages || messages.length === 0) return;
    const content = messages.map((m) => `[${m.role.toUpperCase()}] ${m.content}`).join('\n\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hermes_session_${activeSession?.id || 'export'}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast('Chat exported to TXT', "success");
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 h-full flex flex-col pb-6">
      <SectionHeader
        eyebrow="COMMUNICATION"
        title="Chat & Activity"
        description="Review your conversations and recent system events."
        action={
          <button
            onClick={() => void handleCreateSession()}
            className="btn-primary font-bold shadow-[0_0_15px_rgba(255,255,255,0.1)] text-xs tracking-wider uppercase px-5 py-2.5"
          >
            <Plus size={16} /> New Session
          </button>
        }
      />

      <div className="flex gap-6 flex-1 min-h-0">
        {/* Left Sidebar */}
        <div className="w-[300px] flex flex-col gap-4">
          <div className="surface-base flex flex-col overflow-hidden h-full">
            <div className="p-4 border-b border-[var(--border-subtle)]">
              <button 
                onClick={() => setViewMode('activity')}
                className={`w-full p-3 rounded-[var(--radius-md)] flex items-center gap-3 transition-colors ${viewMode === 'activity' ? 'bg-[var(--surface-3)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:bg-[var(--surface-2)]'}`}
              >
                <Activity size={16} />
                <span className="font-semibold text-sm">Activity Log</span>
              </button>
            </div>
            
            <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--surface-0)]">
              <h3 className="eyebrow text-[var(--text-tertiary)]">Sessions</h3>
            </div>
            
            <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
              {sessions.map((s) => (
                <div 
                  key={s.id}
                  onClick={() => handleSwitchSession(s.id)}
                  className={`p-3 rounded-[var(--radius-md)] flex justify-between items-center cursor-pointer group transition-colors ${viewMode === 'chat' && s.is_active ? 'bg-[var(--surface-2)] border border-[var(--border-strong)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:bg-[var(--surface-2)] border border-transparent'}`}
                >
                  <div className="flex items-center gap-3 truncate">
                    <MessageSquare size={16} />
                    <span className="truncate text-sm font-medium">{s.name}</span>
                  </div>
                  {sessions.length > 1 && (
                    <button onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }} className="opacity-0 group-hover:opacity-100 text-[var(--text-tertiary)] hover:text-[var(--state-error)] transition-opacity p-1">
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Content Area */}
        <div className="flex-1 surface-base flex flex-col overflow-hidden relative">
          {viewMode === 'activity' ? (
            <div className="flex flex-col h-full">
              <div className="p-4 border-b border-[var(--border-subtle)] flex items-center justify-between bg-[var(--surface-0)]">
                <h2 className="text-heading">Recent System Activity</h2>
                <span className="eyebrow bg-[var(--surface-2)] px-2 py-1 rounded">{activity.length} Events</span>
              </div>
              <div className="flex-1 overflow-y-auto custom-scrollbar">
                {activity.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-[var(--text-tertiary)] text-sm">No recent activity</div>
                ) : (
                  <div className="divide-y divide-[var(--border-subtle)]">
                    {activity.map((item, index) => {
                      const isSuccess = item.status === 'success';
                      return (
                        <div key={index} className="flex gap-4 p-4 hover:bg-[var(--surface-2)] transition-colors text-sm">
                          <time className="font-mono text-xs text-[var(--text-tertiary)] w-24 shrink-0 mt-0.5">{formatTimestamp(item.timestamp)}</time>
                          <div className={`shrink-0 w-10 text-center font-mono text-[10px] font-bold tracking-wider py-1 rounded ${isSuccess ? 'bg-[var(--state-ready-glow)] text-[var(--state-ready)]' : 'bg-[var(--state-error-glow)] text-[var(--state-error)]'}`}>
                            {isSuccess ? 'OK' : 'ERR'}
                          </div>
                          <div className="flex-1">
                            <span className="eyebrow text-[var(--text-tertiary)] mr-2">{item.type === 'voice' ? 'VOICE' : 'CMD'}</span>
                            <span className="text-[var(--text-primary)]">{item.text}</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <>
              <div className="p-4 border-b border-[var(--border-subtle)] flex items-center justify-between bg-[var(--surface-0)]">
                <div className="flex items-center gap-3">
                  <h2 className="text-heading truncate">{activeSession?.name || 'Session'}</h2>
                  {activeSession?.remote_session_id && (
                    <div className="flex items-center gap-1.5 bg-[var(--surface-2)] px-2 py-1 rounded text-xs text-[var(--text-secondary)]">
                      <Globe size={12} />
                      <span className="font-mono">{activeSession.remote_session_id}</span>
                    </div>
                  )}
                </div>
                {messages.length > 0 && (
                  <button onClick={handleExport} className="btn-base !py-1.5 !px-3 text-xs">
                    <Download size={14} /> Export
                  </button>
                )}
              </div>
              
              <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                {messages.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-[var(--text-tertiary)] text-sm">
                    No messages in this session.
                  </div>
                ) : (
                  messages.map((m) => (
                    <div key={m.id} className={`flex flex-col animate-in slide-in-from-bottom-2 duration-300 ${m.role === 'user' ? 'items-end' : 'items-start'} group`}>
                      <div className={`max-w-[80%] rounded-2xl px-5 py-3.5 ${m.role === 'user' ? 'bg-[var(--text-primary)] text-[var(--bg-base)] rounded-br-sm' : 'bg-[var(--surface-2)] border border-[var(--border-strong)] text-[var(--text-primary)] rounded-bl-sm'}`}>
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.content}</p>
                      </div>
                      
                      <div className={`flex items-center gap-2 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity px-1 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                        {m.role === 'hermes' && m.latency_ms && m.latency_ms > 0 && (
                          <div className="flex items-center gap-1 text-[10px] text-[var(--text-tertiary)] bg-[var(--surface-0)] px-2 py-1 rounded border border-[var(--border-subtle)]">
                            <Clock size={10} />
                            <span>{m.latency_ms}ms</span>
                          </div>
                        )}
                        <button onClick={() => { navigator.clipboard.writeText(m.content); toast('Copied to clipboard', "success"); }} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] p-1">
                          <Copy size={14} />
                        </button>
                        {(m.role === 'hermes' || m.status === 'local') && (
                          <button onClick={() => api.speakText(m.content.replace('⚡ ', ''))} className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] p-1">
                            <Volume2 size={14} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              <div className="p-4 border-t border-[var(--border-subtle)] bg-[var(--surface-0)]">
                <input 
                  type="text" 
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Type a message to Hermes..." 
                  className="field w-full text-sm font-medium"
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
