import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { MessageSquare, Plus, Trash2, Copy, Clock, Globe, Volume2, Download } from 'lucide-react';
import { useToast } from '../contexts/ToastContext';
import { useLanguage } from '../contexts/LanguageContext';
import { SectionHeader } from '../components/Layout/PageHeader';

export const Sessions = () => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<any>(null);
  const [inputText, setInputText] = useState("");
  const { toast } = useToast();
  const { t } = useLanguage();

  const loadData = async () => {
    const list = await api.getSessions();
    setSessions(list);
    const active = list.find((s: any) => s.is_active);
    if (active) {
      setActiveSession(active);
      const msgs = await api.getMessages(active.id);
      setMessages(msgs);
    } else {
      setActiveSession(null);
      setMessages([]);
    }
  };

  useEffect(() => {
    loadData();
    
    // Listen for background events from Python (e.g. voice loop)
    const handleNewMessage = () => {
      loadData();
    };
    window.addEventListener('hermes_new_message', handleNewMessage);
    
    return () => {
      window.removeEventListener('hermes_new_message', handleNewMessage);
    };
  }, []);

  const handleSwitchSession = async (id: string) => {
    await api.switchSession(id);
    await loadData();
  };

  const handleCreateSession = async () => {
    await api.createSession("New Session");
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
    
    // Optimistic UI
    setMessages((prev: any) => [...prev, { role: "user", content: text, id: Date.now() }]);
    
    await api.sendMessage(text);
    await loadData();
  };

  const handleExport = () => {
    if (!messages || messages.length === 0) return;
    const content = messages.map((m: any) => `[${m.role.toUpperCase()}] ${m.content}`).join('\n\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hermes_session_${activeSession?.id || 'export'}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast(t('sessions.exported', 'Chat exported to TXT'), "success");
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 h-full flex flex-col">
      <SectionHeader
        eyebrow={t('sessions.eyebrow')}
        title={t('sessions.title')}
        description={t('sessions.description')}
        action={
          <button
            type="button"
            onClick={() => void handleCreateSession()}
            className="flex items-center justify-center gap-2 rounded-[var(--radius-control)] border border-black/10 bg-black/5 px-5 py-3 font-mono text-xs font-bold uppercase tracking-[0.14em] text-gray-900 shadow-lg backdrop-blur-md transition-colors hover:bg-black/10 dark:border-white/20 dark:bg-white/10 dark:text-white dark:hover:bg-white/20"
          >
            <Plus size={16} /> {t('sessions.new_session')}
          </button>
        }
      />

      {activeSession?.remote_session_id ? (
        <div className="mb-6 flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-100 px-3 py-1.5 text-xs font-bold text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200">
          <Globe size={12} />
          <span>{t('sessions.remote_id')} {activeSession.remote_session_id}</span>
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(activeSession.remote_session_id);
              toast(t('sessions.copied'), 'success');
            }}
            className="ml-1 transition-colors hover:text-black dark:hover:text-white"
          >
            <Copy size={12} />
          </button>
        </div>
      ) : null}
      
      <div className="flex gap-6 flex-1 min-h-[500px]">
        <div className="w-1/3 glass-panel rounded-[1.5rem] overflow-hidden flex flex-col transition-all duration-300">
          <div className="p-5 border-b border-black/5 dark:border-white/5 font-bold text-sm text-gray-900 dark:text-gray-300">
            {t('sessions.chat_history')}
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
            {sessions.map((s: any) => (
              <div 
                key={s.id}
                onClick={() => handleSwitchSession(s.id)}
                className={`p-3.5 rounded-xl flex justify-between items-center cursor-pointer group transition-all font-semibold text-sm ${s.is_active ? 'bg-black/10 dark:bg-white/20 border border-black/20 dark:border-white/20 text-gray-900 dark:text-white shadow-lg' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 border border-transparent'}`}
              >
                <div className="flex items-center gap-3 truncate">
                  <MessageSquare size={16} />
                  <span className="truncate">{s.name}</span>
                </div>
                {sessions.length > 1 && (
                  <button onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }} className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity p-1">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 glass-panel rounded-[1.5rem] flex flex-col overflow-hidden transition-all duration-300 relative">
          {messages.length > 0 && (
            <div className="absolute top-4 right-4 z-10">
              <button 
                onClick={handleExport}
                className="bg-white/80 dark:bg-black/40 hover:bg-white dark:hover:bg-black/60 text-gray-700 dark:text-gray-300 backdrop-blur-md px-3 py-1.5 rounded-xl shadow-sm transition-all flex items-center gap-2 text-xs font-bold border border-black/5 dark:border-white/10"
              >
                <Download size={14} /> Export
              </button>
            </div>
          )}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar pt-14">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-400 font-medium text-sm">
                {t('sessions.no_messages')}
              </div>
            ) : (
              messages.map((m: any) => (
                <div key={m.id} className={`flex flex-col animate-in slide-in-from-bottom-2 duration-300 ${m.role === 'user' ? 'items-end' : 'items-start'} group`}>
                  <div className={`max-w-[80%] rounded-2xl px-5 py-3.5 shadow-sm backdrop-blur-md ${m.role === 'user' ? 'bg-gray-800 dark:bg-gray-200 text-white dark:text-black rounded-br-sm border border-gray-900 dark:border-white/10' : 'bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 text-gray-900 dark:text-gray-100 rounded-bl-sm font-medium'}`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.content}</p>
                  </div>
                  
                  <div className={`flex items-center gap-2 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity px-1 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    {m.role === 'hermes' && m.latency_ms > 0 && (
                      <div className="flex items-center gap-1 text-[10px] text-gray-400 font-medium bg-black/5 dark:bg-white/5 px-2 py-1 rounded-md">
                        <Clock size={10} />
                        <span>{t('sessions.latency', { ms: m.latency_ms })}</span>
                      </div>
                    )}
                    
                    <button 
                      onClick={() => {
                        navigator.clipboard.writeText(m.content);
                        toast(t('sessions.copied'), "success");
                      }}
                      className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors bg-black/5 dark:bg-white/5 p-1.5 rounded-md"
                      title="Copy text"
                    >
                      <Copy size={12} />
                    </button>
                    
                    {(m.role === 'hermes' || m.status === 'local') && (
                      <button 
                        onClick={() => api.speakText(m.content.replace('⚡ ', ''))}
                        className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors bg-black/5 dark:bg-white/5 p-1.5 rounded-md"
                        title="Read aloud"
                      >
                        <Volume2 size={12} />
                      </button>
                    )}
                    
                    {m.status === 'error' && (
                      <div className="text-[10px] text-red-500 font-bold bg-red-100 dark:bg-red-900/30 px-2 py-1 rounded-md">{t('sessions.error_sending')}</div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="p-4 border-t border-black/5 dark:border-white/5 bg-white/50 dark:bg-black/20 backdrop-blur-xl">
            <input 
              type="text" 
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder={t('sessions.type_message')} 
              className="w-full bg-black/5 dark:bg-white/5 border border-black/10 dark:border-white/10 rounded-xl px-4 py-3.5 text-sm text-gray-900 dark:text-white font-medium focus:outline-none focus:border-gray-900/50 dark:focus:border-white/50 transition-all shadow-inner placeholder-gray-500"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
