import React, { useEffect, useState } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { useHermes } from '../contexts/HermesContext';
import { Mic, Activity, Keyboard, Clock, ChevronRight, Copy, Search, Calendar, Settings, MessageSquare, Terminal } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { ChatMessage } from '../types';

export const Home = () => {
  const { t } = useLanguage();
  const { health, isPaused, runtime, config } = useHermes();
  const navigate = useNavigate();
  const [stats, setStats] = useState({ today: 0, week: 0 });
  const [recentInteractions, setRecentInteractions] = useState<ChatMessage[]>([]);

  useEffect(() => {
    // Mock loading stats and recent interactions for now, or fetch from DB if available
    const loadData = async () => {
      try {
        const sessions = await api.getSessions();
        if (sessions && sessions.length > 0) {
          const msgs = await api.getMessages(sessions[0].id);
          setRecentInteractions(msgs.slice(-5).reverse());
          setStats({ today: msgs.length, week: msgs.length * 3 }); // Mocked stats
        }
      } catch (e) {
        console.error(e);
      }
    };
    loadData();
  }, []);

  const getHeroGradient = () => {
    if (!health) return 'radial-gradient(ellipse at top right, rgba(239,68,68,0.15), transparent 70%)';
    if (isPaused) return 'radial-gradient(ellipse at top right, rgba(245,158,11,0.15), transparent 70%)';
    if (runtime.listening_state !== 'idle') return 'radial-gradient(ellipse at top right, rgba(34,197,94,0.15), transparent 70%)';
    return 'radial-gradient(ellipse at top right, rgba(99,102,241,0.15), transparent 70%)';
  };

  const getStatusOrb = () => {
    if (!health) return 'bg-[var(--state-error)] shadow-[0_0_12px_var(--state-error-glow)]';
    if (isPaused) return 'bg-[var(--state-warn)]';
    if (runtime.listening_state !== 'idle') return 'bg-[var(--state-ready)] shadow-[0_0_12px_var(--state-ready-glow)] animate-pulse-glow';
    return 'bg-[var(--accent-primary)] shadow-[0_0_12px_var(--accent-primary-glow)]';
  };

  const getStatusText = () => {
    if (!health) return 'Offline';
    if (isPaused) return 'Paused';
    if (runtime.listening_state === 'listening') return 'Listening...';
    if (runtime.listening_state === 'thinking' || runtime.listening_state === 'processing') return 'Thinking...';
    if (runtime.listening_state === 'speaking' || runtime.listening_state === 'responding') return 'Speaking...';
    return 'Online · v2.1';
  };

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      {/* Status Hero */}
      <div className="card-premium p-8 relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div 
          className="absolute inset-0 opacity-100 pointer-events-none transition-colors duration-700" 
          style={{ background: getHeroGradient() }} 
        />
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className={`w-3.5 h-3.5 rounded-full ${getStatusOrb()} transition-all duration-500`} />
            <h1 className="text-display text-[var(--text-primary)]">
              Hermes is {getStatusText().toLowerCase()}
            </h1>
          </div>
          <p className="text-body text-[var(--text-secondary)] flex items-center gap-2">
            {recentInteractions.length > 0 ? (
              <>
                <Mic size={14} className="text-[var(--text-tertiary)]" />
                <span>Last command: "{recentInteractions[0].content.substring(0, 40)}{recentInteractions[0].content.length > 40 ? '...' : ''}"</span>
              </>
            ) : (
              'Waiting for your commands...'
            )}
          </p>
        </div>
        
        <div className="text-left md:text-right relative z-10">
          <p className="eyebrow text-[var(--text-tertiary)] mb-1">System Status</p>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--surface-0)] border border-[var(--border-subtle)]">
            <span className={`w-2 h-2 rounded-full ${health ? 'bg-[var(--state-ready)]' : 'bg-[var(--state-error)]'}`} />
            <span className="text-xs font-medium text-[var(--text-primary)]">{getStatusText()}</span>
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card-premium p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-[var(--text-secondary)]">
              <Mic size={16} />
              <span className="eyebrow">Mic Status</span>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
              runtime.listening_state === 'idle' ? 'bg-[var(--surface-2)] text-[var(--text-secondary)]' :
              'bg-[var(--accent-primary-glow)] text-[var(--accent-primary)] border border-[var(--accent-primary)] shadow-[0_0_8px_var(--accent-primary-glow)] animate-pulse-glow'
            }`}>
              {runtime.listening_state}
            </span>
          </div>
          <div>
            <p className="text-xs text-[var(--text-tertiary)] leading-tight">Microphone is currently {runtime.listening_state}</p>
          </div>
        </div>
        
        <div className="card-premium p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-[var(--text-secondary)]">
              <Activity size={16} />
              <span className="eyebrow">Activity</span>
            </div>
          </div>
          <div>
            <div className="flex items-end gap-2 mb-2">
              <p className="text-display leading-none">{stats.today}</p>
              <p className="text-xs text-[var(--text-tertiary)] mb-0.5">cmds today</p>
            </div>
            <div className="h-1.5 w-full bg-[var(--surface-0)] rounded-full overflow-hidden border border-[var(--border-subtle)]">
              <div 
                className="h-full bg-[var(--accent-gradient)] rounded-full" 
                style={{ width: `${Math.min(100, (stats.today / 50) * 100)}%` }}
              />
            </div>
          </div>
        </div>
        
        <div className="card-premium p-5 flex flex-col justify-between">
          <div className="flex items-center gap-2 text-[var(--text-secondary)] mb-4">
            <Keyboard size={16} />
            <span className="eyebrow">Quick Access</span>
          </div>
          <div className="flex items-center justify-between">
            <p className="text-xs text-[var(--text-tertiary)]">Push to talk</p>
            <div className="px-2.5 py-1 rounded bg-[var(--surface-1)] border-b-2 border-r border-t border-l border-[var(--border-strong)] text-xs font-mono font-bold text-[var(--text-primary)] shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
              {String(config.hotkey || 'CTRL+SHIFT+SPACE').toUpperCase()}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Feed */}
        <div className="lg:col-span-2 card-premium flex flex-col overflow-hidden">
          <div className="p-5 border-b border-[var(--border-subtle)] flex items-center justify-between bg-[var(--surface-1)]">
            <h2 className="text-heading flex items-center gap-2">
              <Clock size={16} className="text-[var(--accent-primary)]" />
              Recent Interactions
            </h2>
            <button onClick={() => navigate('/chat')} className="text-xs font-medium text-[var(--text-tertiary)] hover:text-[var(--accent-primary)] transition-colors">View all</button>
          </div>
          <div className="flex-1 p-2 bg-[var(--surface-0)]/50">
            {recentInteractions.length === 0 ? (
              <div className="p-8 text-center text-[var(--text-tertiary)] text-sm flex flex-col items-center justify-center gap-3">
                <MessageSquare size={24} className="opacity-20" />
                No recent interactions.
              </div>
            ) : (
              recentInteractions.map((msg, idx) => (
                <div 
                  key={idx} 
                  onClick={() => navigate('/chat')}
                  className="flex items-center justify-between p-3 rounded-[var(--radius-md)] hover:bg-[var(--surface-2)] cursor-pointer transition-all group"
                >
                  <div className="flex items-center gap-4 overflow-hidden">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 border shadow-sm ${
                      msg.role === 'user' 
                        ? 'bg-[var(--surface-1)] border-[var(--border-subtle)]' 
                        : 'bg-[var(--accent-primary-glow)] border-[var(--accent-primary)]/30'
                    }`}>
                      {msg.role === 'user' ? <Mic size={14} className="text-[var(--text-secondary)]" /> : <Activity size={14} className="text-[var(--accent-primary)]" />}
                    </div>
                    <div className="truncate">
                      <p className="text-sm font-medium text-[var(--text-primary)] truncate" title={msg.content}>{msg.content}</p>
                      <p className="text-[11px] font-medium text-[var(--text-tertiary)] flex items-center gap-1 mt-0.5 uppercase tracking-wider">
                        {msg.role === 'user' ? 'You' : 'Hermes'}
                      </p>
                    </div>
                  </div>
                  <ChevronRight size={16} className="text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Quick Commands */}
        <div className="card-premium flex flex-col overflow-hidden">
          <div className="p-5 border-b border-[var(--border-subtle)] flex items-center justify-between bg-[var(--surface-1)]">
            <h2 className="text-heading flex items-center gap-2">
              <Terminal size={16} className="text-[var(--accent-secondary)]" />
              Quick Actions
            </h2>
          </div>
          <div className="flex flex-col p-2 bg-[var(--surface-0)]/50 gap-1">
            <button onClick={() => navigate('/commands')} className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] hover:bg-[var(--surface-2)] transition-colors group text-left">
              <div className="w-8 h-8 rounded bg-[var(--surface-1)] border border-[var(--border-subtle)] flex items-center justify-center shrink-0 group-hover:border-[var(--accent-primary)] group-hover:text-[var(--accent-primary)] transition-colors">
                <Copy size={14} />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-[var(--text-primary)]">Copy Text</p>
                <p className="text-[11px] text-[var(--text-tertiary)]">Extract text from screen</p>
              </div>
              <ChevronRight size={14} className="text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
            <button onClick={() => navigate('/commands')} className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] hover:bg-[var(--surface-2)] transition-colors group text-left">
              <div className="w-8 h-8 rounded bg-[var(--surface-1)] border border-[var(--border-subtle)] flex items-center justify-center shrink-0 group-hover:border-[var(--accent-primary)] group-hover:text-[var(--accent-primary)] transition-colors">
                <Search size={14} />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-[var(--text-primary)]">Search Web</p>
                <p className="text-[11px] text-[var(--text-tertiary)]">Quick online query</p>
              </div>
              <ChevronRight size={14} className="text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
            <button onClick={() => navigate('/commands')} className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] hover:bg-[var(--surface-2)] transition-colors group text-left">
              <div className="w-8 h-8 rounded bg-[var(--surface-1)] border border-[var(--border-subtle)] flex items-center justify-center shrink-0 group-hover:border-[var(--accent-primary)] group-hover:text-[var(--accent-primary)] transition-colors">
                <Calendar size={14} />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-[var(--text-primary)]">Agenda</p>
                <p className="text-[11px] text-[var(--text-tertiary)]">View today's events</p>
              </div>
              <ChevronRight size={14} className="text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
            <button onClick={() => navigate('/settings')} className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] hover:bg-[var(--surface-2)] transition-colors group text-left">
              <div className="w-8 h-8 rounded bg-[var(--surface-1)] border border-[var(--border-subtle)] flex items-center justify-center shrink-0 group-hover:border-[var(--accent-primary)] group-hover:text-[var(--accent-primary)] transition-colors">
                <Settings size={14} />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-[var(--text-primary)]">Config</p>
                <p className="text-[11px] text-[var(--text-tertiary)]">System preferences</p>
              </div>
              <ChevronRight size={14} className="text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
