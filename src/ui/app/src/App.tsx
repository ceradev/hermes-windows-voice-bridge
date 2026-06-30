import React, { useState } from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { api } from './services/api';
import { Sidebar } from './components/Layout/Sidebar';
import { Titlebar } from './components/Layout/Titlebar';
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

  return (
    <Router>
      <div className="relative flex h-screen flex-col overflow-hidden bg-[var(--bg-base)] font-sans text-[var(--text-primary)]">
        <Titlebar onToggleMini={() => api.minimizeToTray()} />

        <div className="flex flex-1 overflow-hidden pt-10">
          <Sidebar
            isCollapsed={isSidebarCollapsed}
            toggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          />

          <main className="min-w-0 flex-1 overflow-y-auto px-5 py-4">
            <div className="mx-auto h-full w-full max-w-[1200px]">
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/configure" element={<Configure />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/commands" element={<Commands />} />
                <Route
                  path="*"
                  element={
                    <div className="flex h-full min-h-[200px] items-center justify-center">
                      <div className="surface-base p-6 text-center">
                        <p className="text-caption mb-1">Page not found</p>
                        <p className="text-body text-[var(--text-secondary)]">This page does not exist.</p>
                      </div>
                    </div>
                  }
                />
              </Routes>
            </div>
          </main>
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
