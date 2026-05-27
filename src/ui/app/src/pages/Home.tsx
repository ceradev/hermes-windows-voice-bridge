import React, { useEffect, useRef } from 'react';
import { Activity, Volume2, Mic, Settings, Play, History, Pause, RefreshCw } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useHermes } from '../contexts/HermesContext';
import { AudioVisualizer } from '../components/Audio/AudioVisualizer';

export const Home = ({ miniMode = false }: { miniMode?: boolean }) => {
  const { t } = useLanguage();
  const { health, config, messages, audioLevel, isPaused, updateConfig, togglePause, restartApp } = useHermes();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const normalMessagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (miniMode && messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
      } else if (!miniMode && normalMessagesEndRef.current) {
        normalMessagesEndRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }, 150); // wait for fade-in animations to establish DOM height
    return () => clearTimeout(timer);
  }, [messages, miniMode]);

  const handleQuickToggle = async (key: string, value: any) => {
    await updateConfig({ [key]: value });
  };

  const handlePauseToggle = async () => {
    await togglePause();
  };

  const handleRestart = async () => {
    await restartApp();
  };

  const systemStatus = !health ? 'OFFLINE' : isPaused ? 'PAUSED' : 'READY';
  const systemStatusTone = !health
    ? 'text-red-600 dark:text-red-400'
    : isPaused
      ? 'text-amber-600 dark:text-amber-300'
      : 'text-gray-950 dark:text-white';
  const ledTone = health ? 'bg-emerald-400 shadow-[0_0_14px_rgba(52,211,153,0.85)]' : 'bg-red-500 shadow-[0_0_14px_rgba(239,68,68,0.85)]';

  const rockerClass = "relative h-7 w-14 cursor-pointer border border-black/15 bg-black/10 shadow-inner transition-colors dark:border-white/15 dark:bg-white/10 peer-checked:bg-gray-950 dark:peer-checked:bg-white after:absolute after:left-[3px] after:top-[3px] after:h-5 after:w-6 after:bg-white after:shadow-sm after:transition-transform after:content-[''] dark:after:bg-gray-950 peer-checked:after:translate-x-5";

  if (miniMode) {
    return (
      <div className="flex flex-col h-full w-full p-2 relative overflow-hidden animate-in fade-in duration-300">
        <div className="absolute inset-0 z-0 opacity-10 pointer-events-none flex justify-center items-center">
            <div 
              className="w-48 h-48 bg-white/20 rounded-full blur-3xl"
              style={{ 
                transform: `scale(${1 + audioLevel * 1.5})`,
                transition: 'transform 0.05s linear'
              }}
            />
        </div>
        
        <div className="flex-1 flex flex-col items-center justify-center relative z-10 pt-2">
          <div className="mb-2">
            <AudioVisualizer audioLevel={audioLevel} isActive={!isPaused && health} />
          </div>
          
          <div className="w-full px-2 flex-1 overflow-y-auto custom-scrollbar flex flex-col justify-start gap-2 relative pb-1" style={{ maskImage: 'linear-gradient(to bottom, transparent, black 10%, black 90%, transparent)' }}>
             <div className="flex-1 min-h-[min-content] flex flex-col justify-center">
               {messages.length > 0 ? (
                 (() => {
                   // Find the last Hermes or System message
                   const lastHermes = [...messages].reverse().find(m => m.role !== 'user');
                   const m = lastHermes || messages[messages.length - 1];
                   return (
                     <div className="animate-in slide-in-from-bottom-2 fade-in flex flex-col items-center">
                       <p className={`text-[10px] font-bold uppercase tracking-widest mb-1 ${
                         m.role === 'user' ? 'text-white/40' : 
                         m.role === 'system' ? 'text-red-400' : 'text-blue-300/80'
                       }`}>
                         {m.role === 'user' ? t('home.you') : m.role === 'system' ? 'ERROR' : 'Hermes'}
                       </p>
                       <p className={`text-sm font-medium leading-relaxed text-center ${
                         m.role === 'system' ? 'text-red-300' :
                         m.role === 'user' ? 'text-white/80' : 'text-white'
                       } break-words max-w-full line-clamp-3`}>
                         {m.content}
                       </p>
                     </div>
                   );
                 })()
               ) : (
                 <div className="flex justify-center items-center h-full mt-auto mb-auto">
                   <p className="text-xs font-medium text-white/50">{t('home.listening', 'Escuchando...')}</p>
                 </div>
               )}
               <div ref={messagesEndRef} />
             </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Top Banner */}
      <div className="mb-5 grid grid-cols-1 gap-5 xl:grid-cols-[1.2fr_420px]">
        <section className="glass-panel relative overflow-hidden rounded-[var(--radius-panel)] border-black/10 p-7 transition-colors duration-300 dark:border-white/10">
          <div className="absolute inset-x-0 top-0 h-px bg-black/20 dark:bg-white/20" />
          <div className="absolute right-5 top-5 flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
            <span className={`h-2.5 w-2.5 rounded-full ${ledTone}`} />
            {health ? t('home.connected') : t('home.offline')}
          </div>

          <div className="relative z-10 max-w-3xl pt-6">
            <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-[0.24em] text-gray-500 dark:text-gray-400">Hermes Voice Bridge</p>
            <h3 className={`font-sans text-7xl font-extrabold uppercase leading-none tracking-tighter [font-stretch:condensed] md:text-8xl ${systemStatusTone}`}>
              {systemStatus}
            </h3>
            <p className="mt-5 max-w-xl text-sm font-semibold leading-6 text-gray-600 dark:text-gray-400">
              {t('home.instruction', { hotkey: config.hotkey || 'CTRL+SHIFT+H' })}
            </p>
          </div>
        </section>

        <section className="glass-panel rounded-[var(--radius-panel)] p-4 transition-colors duration-300">
          <div className="mb-3 flex items-center justify-between border-b border-black/10 pb-3 dark:border-white/10">
            <p className="font-mono text-[11px] font-bold uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Command Deck</p>
            <Settings className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={handlePauseToggle}
              className={`col-span-2 flex items-center justify-between rounded-[var(--radius-control)] border px-4 py-3 font-mono text-xs font-bold uppercase tracking-[0.14em] transition-colors ${isPaused ? 'border-amber-500/30 bg-amber-500/15 text-amber-700 dark:text-amber-300' : 'border-black/10 bg-black/5 text-gray-900 hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10'}`}
            >
              <span className="flex items-center gap-2">{isPaused ? <Play size={16} /> : <Pause size={16} />}{isPaused ? t('home.resume', 'Resume') : t('home.pause', 'Pause')}</span>
              <span className="text-[10px] text-gray-500 dark:text-gray-400">CTRL</span>
            </button>
            <button
              onClick={handleRestart}
              className="col-span-2 flex items-center justify-between rounded-[var(--radius-control)] border border-black/10 bg-black/5 px-4 py-3 font-mono text-xs font-bold uppercase tracking-[0.14em] text-gray-900 transition-colors hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
            >
              <span className="flex items-center gap-2"><RefreshCw size={16} />{t('home.restart', 'Restart')}</span>
              <span className="text-[10px] text-gray-500 dark:text-gray-400">RST</span>
            </button>
            <div className="col-span-2 flex items-center justify-between rounded-[var(--radius-control)] border border-black/10 bg-black/5 p-3 dark:border-white/10 dark:bg-white/5">
              <div className="flex items-center gap-3">
                <div className="relative flex h-11 w-11 items-center justify-center border border-black/10 bg-white/50 dark:border-white/10 dark:bg-black/20">
                  <div
                    className="absolute inset-0 bg-black/10 dark:bg-white/20"
                    style={{
                      transform: `scale(${1 + audioLevel * 0.6})`,
                      opacity: audioLevel > 0.02 ? 0.3 + audioLevel * 0.7 : 0,
                      transition: 'transform 0.05s linear, opacity 0.1s ease-out'
                    }}
                  />
                  <Mic className={`relative z-10 h-5 w-5 transition-colors ${audioLevel > 0.1 ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`} />
                </div>
                <div>
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-gray-500 dark:text-gray-400">Input Level</p>
                  <p className="font-mono text-sm font-bold text-gray-900 dark:text-gray-100">{Math.round(audioLevel * 100).toString().padStart(2, '0')}%</p>
                </div>
              </div>
              <AudioVisualizer audioLevel={audioLevel} isActive={!isPaused && health} />
            </div>
          </div>
        </section>
      </div>

      <div className="mb-5 grid grid-cols-1 gap-5 md:grid-cols-3">
        {/* Connection Status */}
        <div className="glass-panel rounded-[var(--radius-panel)] p-5 transition-colors duration-300">
          <div className="mb-4 flex items-center justify-between border-b border-black/10 pb-3 dark:border-white/10">
            <h3 className="font-mono text-[11px] font-bold uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400">{t('home.connection')}</h3>
            <span className="font-mono text-[10px] font-bold text-gray-500">NET</span>
          </div>
          <div className="mb-4 flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-[0.12em] text-gray-700 dark:text-gray-300">
            <span className={`h-2.5 w-2.5 rounded-full ${ledTone}`} />
            {health ? t('home.connected') : t('home.offline')}
          </div>
          <p className="truncate font-mono text-xs font-semibold text-gray-500 dark:text-gray-400">{config.api_base_url}</p>
        </div>

        {/* Quick Controls */}
        <div className="glass-panel rounded-[var(--radius-panel)] p-5 transition-colors duration-300 md:col-span-2">
          <div className="mb-4 flex items-center justify-between border-b border-black/10 pb-3 dark:border-white/10">
            <h3 className="font-mono text-[11px] font-bold uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400">{t('home.quick_controls')}</h3>
            <Settings className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="flex items-center justify-between rounded-[var(--radius-control)] border border-black/10 bg-black/5 p-4 transition-colors hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10">
              <div className="flex items-center gap-3">
                <Volume2 className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                <div>
                  <span className="block text-sm font-bold text-gray-900 dark:text-gray-200">{t('home.tts_voice')}</span>
                  <span className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">TTS_OUT</span>
                </div>
              </div>
              <label className="relative inline-flex items-center">
                <input type="checkbox" checked={config.tts_enabled ?? true} onChange={(e) => handleQuickToggle("tts_enabled", e.target.checked)} className="peer sr-only" />
                <div className={rockerClass}></div>
              </label>
            </div>

            <div className="flex items-center justify-between rounded-[var(--radius-control)] border border-black/10 bg-black/5 p-4 transition-colors hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10">
              <div className="flex items-center gap-3">
                <Play className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                <div>
                  <span className="block text-sm font-bold text-gray-900 dark:text-gray-200">{t('home.autostart')}</span>
                  <span className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">BOOT_SEQ</span>
                </div>
              </div>
              <label className="relative inline-flex items-center">
                <input type="checkbox" checked={config.autostart ?? true} onChange={(e) => handleQuickToggle("autostart", e.target.checked)} className="peer sr-only" />
                <div className={rockerClass}></div>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {/* Recent Activity */}
        <div className="glass-panel flex h-[280px] flex-col rounded-[var(--radius-panel)] p-5 transition-colors duration-300">
          <div className="mb-4 flex shrink-0 items-center justify-between border-b border-black/10 pb-3 dark:border-white/10">
            <h3 className="font-mono text-[11px] font-bold uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400">{t('home.recent_activity')}</h3>
            <History className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          </div>

          <div className="custom-scrollbar flex-1 overflow-y-auto pr-2">
            {messages.length === 0 ? (
              <p className="mt-10 text-center text-sm font-semibold text-gray-500 dark:text-gray-400">{t('home.no_messages')}</p>
            ) : (
              messages.map((m: any, idx: number) => (
                <div key={idx} className="mb-2 grid grid-cols-[42px_1fr] gap-3 border-b border-black/10 bg-black/5 p-3 transition-colors last:border-b-0 hover:bg-black/10 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10">
                  <div className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] border border-black/10 bg-white/60 text-gray-800 dark:border-white/10 dark:bg-black/20 dark:text-gray-200">
                    {m.role === 'user' ? <Mic size={14} /> : <span className="font-mono text-xs font-bold">H</span>}
                  </div>
                  <div className="min-w-0">
                    <p className="mb-1 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">{m.role === 'user' ? t('home.you') : 'Hermes'}</p>
                    <p className="break-words text-sm font-semibold text-gray-900 dark:text-gray-200">{m.content}</p>
                  </div>
                </div>
              ))
            )}
            <div ref={normalMessagesEndRef} />
          </div>
        </div>

        {/* System Overview */}
        <div className="glass-panel flex flex-col rounded-[var(--radius-panel)] p-5 transition-colors duration-300">
          <div className="mb-4 flex items-center justify-between border-b border-black/10 pb-3 dark:border-white/10">
            <h3 className="font-mono text-[11px] font-bold uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400">{t('home.system_profile')}</h3>
            <Activity className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          </div>

          <div className="space-y-3">
            <div>
              <p className="mb-1 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">{t('home.stt_model')}</p>
              <div className="rounded-[var(--radius-control)] border border-black/10 bg-black/5 px-3 py-2 font-mono text-sm font-bold text-gray-900 shadow-inner dark:border-white/10 dark:bg-white/5 dark:text-gray-200">
                {config.stt_model || 'base'} ({config.stt_language || 'en'})
              </div>
            </div>

            <div>
              <p className="mb-1 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">{t('home.wake_words')}</p>
              <div className="flex flex-wrap gap-2 rounded-[var(--radius-control)] border border-black/10 bg-black/5 px-3 py-2 shadow-inner dark:border-white/10 dark:bg-white/5">
                {(config.wake_phrases || []).map((w: string, i: number) => (
                  <span key={i} className="border border-black/10 bg-white/70 px-2 py-1 font-mono text-xs font-bold text-gray-800 dark:border-white/10 dark:bg-black/20 dark:text-gray-200">
                    {w}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-1 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">{t('home.audio_device')}</p>
              <div className="truncate rounded-[var(--radius-control)] border border-black/10 bg-black/5 px-3 py-2 font-mono text-sm font-bold text-gray-900 shadow-inner dark:border-white/10 dark:bg-white/5 dark:text-gray-200">
                {config.mic_device !== null && config.mic_device !== undefined ? `Device ID: ${config.mic_device}` : t('home.default_mic')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
