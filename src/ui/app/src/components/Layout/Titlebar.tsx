import React from 'react';
import { Minus, Square, X } from 'lucide-react';
import { api } from '../../services/api';
import { useHermes } from '../../contexts/HermesContext';

export const Titlebar = ({ onToggleMini }: { onToggleMini?: () => void }) => {
  const { messages, health } = useHermes();
  
  // Find the last message to display in the titlebar
  const lastMessage = messages.length > 0 ? messages[messages.length - 1].content : null;
  const displayText = lastMessage || "HERMES AI";

  return (
    <div className="h-12 border-b border-gray-800 bg-black flex justify-between items-center px-4 app-region-drag select-none fixed top-0 w-full z-50">
      
      {/* Dynamic Title / Last Phrase with Custom Logo */}
      <div className="flex items-center gap-3 overflow-hidden flex-1 mr-4">
        
        {/* Custom Hermes H Logo with Status Dot */}
        <div className="relative flex-shrink-0 w-6 h-6 bg-[#18181b] rounded border border-gray-800 flex items-center justify-center shadow-md app-region-no-drag">
          <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3.5" strokeLinecap="square" className="w-3.5 h-3.5">
            <path d="M7 4v16M17 4v16M7 12h10" />
          </svg>
          <div className={`absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full border-2 border-black ${health ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)] animate-pulse' : 'bg-red-500'}`}></div>
        </div>

        <span className={`text-sm truncate ${lastMessage ? 'font-medium text-gray-300' : 'font-extrabold tracking-[0.2em] text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-500'}`}>
          {displayText}
        </span>
      </div>

      <div className="flex gap-4 items-center app-region-no-drag">
        <button onClick={onToggleMini || (() => api.minimizeToTray())} className="p-2 text-gray-400 hover:text-white transition-colors focus:outline-none rounded-md hover:bg-white/10" title="Mini Mode">
          <Minus className="w-5 h-5" />
        </button>
        <button onClick={() => api.maximizeWindow()} className="p-2 text-gray-400 hover:text-white transition-colors focus:outline-none rounded-md hover:bg-white/10" title="Maximize">
          <Square className="w-4 h-4" />
        </button>
        <button onClick={() => api.minimizeToTray()} className="p-2 text-gray-400 hover:text-white transition-colors focus:outline-none rounded-md hover:bg-red-500 hover:text-white" title="Close">
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};
