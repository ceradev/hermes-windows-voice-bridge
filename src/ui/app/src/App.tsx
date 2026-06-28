import React, { useState } from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { api } from './services/api';
import { Sidebar } from './components/Layout/Sidebar';
import { Titlebar } from './components/Layout/Titlebar';
import { Header } from './components/Layout/Header';
import { Home } from './pages/Home';
import { Chat } from './pages/Chat';
import { Configure } from './pages/Configure';
import { Settings } from './pages/Settings';
import { Commands } from './pages/Commands';
import { ThemeProvider } from './contexts/ThemeContext';
import { LanguageProvider } from './contexts/LanguageContext';
import { ToastProvider } from './contexts/ToastContext';
import { HermesProvider } from './contexts/HermesContext';

const AppContent = () => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const handleToggleMiniMode = () => {
    api.minimizeToTray();
  };

  return (
    <Router>
      <div className="relative flex h-screen flex-col overflow-hidden font-sans text-[var(--text-primary)]">
        <Titlebar onToggleMini={handleToggleMiniMode} />

        <div className="flex flex-1 overflow-hidden pt-12">
          <Sidebar
            isCollapsed={isSidebarCollapsed}
            toggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          />

          <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden border-l border-[var(--border-subtle)]">


            <Header />

            <main className="relative z-10 flex-1 overflow-y-auto px-6 py-6 md:px-8 md:py-7">
              <div className="mx-auto h-full w-full max-w-[1320px] animate-fade-up">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/chat" element={<Chat />} />
                  <Route path="/configure" element={<Configure />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/commands" element={<Commands />} />
                  <Route
                    path="*"
                    element={
                      <div className="flex h-full items-center justify-center">
                        <div className="surface-base p-8 text-center">
                          <p className="eyebrow text-[var(--accent)] mb-2 text-[10px]">
                            404 · NOT FOUND
                          </p>
                          <p className="text-[13px] font-semibold text-[var(--text-tertiary)]">
                            This page is under construction.
                          </p>
                        </div>
                      </div>
                    }
                  />
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
