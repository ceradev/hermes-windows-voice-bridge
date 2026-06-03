import React, { useState } from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { api } from './services/api';
import { Sidebar } from './components/Layout/Sidebar';
import { Titlebar } from './components/Layout/Titlebar';
import { Header } from './components/Layout/Header';
import { Home } from './pages/Home';
import { Sessions } from './pages/Sessions';
import { History } from './pages/History';
import { Notifications } from './pages/Notifications';
import { Settings } from './pages/Settings';
import { Voice, Hermes } from './pages/Voice';
import { Shortcuts, TTS } from './pages/Shortcuts';
import { Commands } from './pages/Commands';
import { ThemeProvider } from './contexts/ThemeContext';
import { LanguageProvider } from './contexts/LanguageContext';
import { ToastProvider } from './contexts/ToastContext';
import { HermesProvider } from './contexts/HermesContext';

const AppContent = () => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMiniMode, setIsMiniMode] = useState(false);

  const handleToggleMiniMode = async () => {
    const newState = !isMiniMode;
    await api.toggleMiniMode(newState);
    setIsMiniMode(newState);
  };

  if (isMiniMode) {
    return (
      <div className="flex flex-col h-screen bg-black text-white font-sans overflow-hidden transition-all duration-300 app-region-drag relative rounded-lg border border-white/10 shadow-2xl">
        <div className="absolute top-3 right-3 flex gap-3 app-region-no-drag z-50">
          <button onClick={handleToggleMiniMode} className="text-gray-400 hover:text-white transition-colors" title="Expandir">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>
          </button>
          <button onClick={() => api.closeApp()} className="text-gray-400 hover:text-red-500 transition-colors">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center app-region-no-drag">
           <Home miniMode={true} />
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="flex flex-col h-screen text-gray-900 dark:text-white font-sans overflow-hidden transition-colors duration-300">
        <Titlebar onToggleMini={handleToggleMiniMode} />
        <div className="flex flex-1 overflow-hidden pt-12">
          <Sidebar 
            isCollapsed={isSidebarCollapsed} 
            toggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <Header />
            <main className="flex-1 overflow-y-auto p-8 transition-colors duration-300">
              <div className="w-full h-full">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/sessions" element={<Sessions />} />
                  <Route path="/history" element={<History />} />
                  <Route path="/notifications" element={<Notifications />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/voice" element={<Voice />} />
                  <Route path="/hermes" element={<Hermes />} />
                  <Route path="/shortcuts" element={<Shortcuts />} />
                  <Route path="/commands" element={<Commands />} />
                  <Route path="/tts" element={<TTS />} />
                  <Route path="*" element={
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                      <p className="text-gray-400">This page is under construction.</p>
                    </div>
                  } />
                </Routes>
              </div>
            </main>
          </div>
        </div>
      </div>
    </Router>
  );
};

const App = () => {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <ToastProvider>
          <HermesProvider>
            <AppContent />
          </HermesProvider>
        </ToastProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
};

export default App;
