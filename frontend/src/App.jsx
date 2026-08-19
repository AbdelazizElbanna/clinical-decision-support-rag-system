import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ChatInterface from './components/ChatInterface';
import Terms from './pages/Terms';
import Login from './pages/Login';
import Register from './pages/Register';
import Sources from './pages/Sources';
import Team from './pages/Team';
import { ThemeProvider } from './contexts/ThemeContext';
import { LanguageProvider } from './contexts/LanguageContext';
import { AuthProvider } from './contexts/AuthContext';
import './index.css';
import { TopHeader, BottomNav } from './components/Navbar';

function AppShell({ children }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100dvh', width: '100%',
      overflow: 'hidden', background: 'var(--bg-gradient)'
    }}>
      <TopHeader />
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {children}
      </div>
      <BottomNav />
    </div>
  );
}

function AuthShell({ children }) {
  return (
    <div style={{ height: '100dvh', width: '100%', background: 'var(--bg-gradient)' }}>
      {children}
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <Router>
            <Routes>
              <Route path="/login"    element={<AuthShell><Login /></AuthShell>} />
              <Route path="/register" element={<AuthShell><Register /></AuthShell>} />
              <Route path="/terms"    element={<AppShell><Terms /></AppShell>} />
              <Route path="/sources"  element={<AppShell><Sources /></AppShell>} />
              <Route path="/team"     element={<AppShell><Team /></AppShell>} />
              <Route path="/"         element={<AppShell><ChatInterface /></AppShell>} />
              {/* Catch-all - redirect unknown paths to home */}
              <Route path="*"         element={<Navigate to="/" replace />} />
            </Routes>
          </Router>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}

export default App;
