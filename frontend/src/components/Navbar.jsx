import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { MessageSquare, Shield, Users, Database, Sun, Moon, Globe, Sparkles, Menu, LogOut, User, LogIn } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';

export function TopHeader() {
  const { t, language, toggleLanguage } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Close user menu on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('chatSummary');
    window.dispatchEvent(new Event('clear-chat'));
    logout();
    navigate('/login');
  };

  const links = [
    { path: '/', label: t('chat'), icon: <MessageSquare size={20} /> },
    { path: '/sources', label: t('sources'), icon: <Database size={20} /> },
    { path: '/team', label: t('team'), icon: <Users size={20} /> },
    { path: '/terms', label: t('terms'), icon: <Shield size={20} /> }
  ];

  return (
    <header className="glass" style={{
      display: 'flex', padding: '12px 20px', alignItems: 'center',
      justifyContent: 'space-between', zIndex: 100,
      borderBottom: '1px solid var(--border)',
      borderTop: 'none', borderLeft: 'none', borderRight: 'none',
      borderRadius: 0, flexShrink: 0
    }}>
      
      {/* Sidebar Toggle (Mobile Chat Only) */}
      {isMobile && location.pathname === '/' && (
        <button
          onClick={() => window.dispatchEvent(new Event('toggle-sidebar'))}
          style={{ background: 'transparent', border: 'none', color: 'var(--text)', cursor: 'pointer', padding: '4px', marginRight: '8px', display: 'flex', alignItems: 'center' }}
        >
          <Menu size={24} />
        </button>
      )}

      {/* Brand */}
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', fontSize: isMobile ? '1.1rem' : '1.2rem', color: 'var(--text)', textDecoration: 'none', whiteSpace: 'nowrap', flexShrink: 0 }}>
        <div style={{ background: 'linear-gradient(135deg, var(--primary), var(--accent))', padding: '6px', borderRadius: '10px', display: 'flex' }}>
          <Sparkles size={16} color="#fff" />
        </div>
        MedLens AI
      </Link>

      {/* Desktop Links */}
      {!isMobile && (
        <div style={{ display: 'flex', gap: '10px' }}>
          {links.map(link => (
            <Link
              key={link.path}
              to={link.path}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                color: location.pathname === link.path ? 'var(--primary)' : 'var(--text-muted)',
                textDecoration: 'none', padding: '8px 16px', borderRadius: '12px',
                background: location.pathname === link.path ? 'var(--primary-glow)' : 'transparent',
                fontWeight: location.pathname === link.path ? '600' : 'normal',
                transition: 'all 0.2s ease', fontSize: '0.95rem'
              }}
            >
              {link.icon} {link.label}
            </Link>
          ))}
        </div>
      )}

      {/* Right Actions */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <button
          onClick={toggleTheme}
          style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)', cursor: 'pointer', padding: '8px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s ease' }}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        <button
            onClick={toggleLanguage}
            style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)', cursor: 'pointer', padding: '6px 12px', borderRadius: '20px', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: '600', transition: 'all 0.2s ease' }}
          >
            <Globe size={16} />
            <span style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>
              {language === 'ar' ? 'EN' : 'AR'}
            </span>
          </button>

        {/* User Menu */}
        {user ? (
          <div ref={menuRef} style={{ position: 'relative' }}>
            <button
              onClick={() => setShowUserMenu(prev => !prev)}
              style={{
                background: 'linear-gradient(135deg, var(--primary), var(--accent))',
                border: 'none', cursor: 'pointer', padding: '8px 12px',
                borderRadius: '20px', display: 'flex', alignItems: 'center', gap: '8px',
                color: '#fff', fontWeight: '600', fontSize: '0.85rem', transition: 'opacity 0.2s'
              }}
            >
              <User size={16} />
              {!isMobile && (user.username || 'Profile')}
            </button>
            
            {showUserMenu && (
              <div className="fade-up" style={{
                position: 'absolute', top: 'calc(100% + 8px)',
                right: 0, minWidth: '180px',
                borderRadius: '12px', border: '1px solid var(--border)',
                overflow: 'hidden', zIndex: 200,
                background: theme === 'dark' ? 'rgba(15, 23, 42, 0.98)' : 'rgba(255, 255, 255, 0.98)',
                backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
                boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
              }}>
                <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
                  <div style={{ fontWeight: '600', color: 'var(--text)', fontSize: '0.9rem' }}>{user.username}</div>
                  {user.email && <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '2px' }}>{user.email}</div>}
                </div>
                <button
                  onClick={handleLogout}
                  style={{
                    width: '100%', padding: '12px 16px', background: 'transparent',
                    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center',
                    gap: '10px', color: 'var(--error)', fontWeight: '600', fontSize: '0.9rem',
                    transition: 'background 0.2s', textAlign: 'left'
                  }}
                  onMouseOver={e => e.currentTarget.style.background = 'rgba(239,68,68,0.08)'}
                  onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                >
                  <LogOut size={16} /> {t('sign_out')}
                </button>
              </div>
            )}
          </div>
        ) : (
          <Link
            to="/login"
            style={{
              background: 'var(--primary)', color: '#fff', padding: isMobile ? '8px 12px' : '8px 16px',
              borderRadius: '20px', textDecoration: 'none', fontWeight: '600',
              fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            {isMobile ? <LogIn size={18} /> : t('sign_in')}
          </Link>
        )}
      </div>
    </header>
  );
}

export function BottomNav() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const location = useLocation();
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!isMobile) return null;

  const links = [
    { path: '/', label: t('chat'), icon: <MessageSquare size={20} /> },
    { path: '/sources', label: t('sources'), icon: <Database size={20} /> },
    { path: '/team', label: t('team'), icon: <Users size={20} /> },
    { path: '/terms', label: t('terms'), icon: <Shield size={20} /> }
  ];

  return (
    <nav className="glass" style={{
      display: 'flex', justifyContent: 'space-around', padding: '10px 10px',
      paddingBottom: 'calc(10px + env(safe-area-inset-bottom))', zIndex: 100,
      borderTop: '1px solid var(--border)', borderBottom: 'none',
      borderLeft: 'none', borderRight: 'none', borderRadius: 0, flexShrink: 0
    }}>
      {links.map(link => {
        const isActive = location.pathname === link.path;
        return (
          <Link
            key={link.path}
            to={link.path}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px',
              color: isActive ? 'var(--primary)' : 'var(--text-muted)',
              textDecoration: 'none', fontSize: '0.7rem',
              fontWeight: isActive ? '600' : 'normal', transition: 'all 0.2s ease'
            }}
          >
            <div style={{ padding: '8px', borderRadius: '12px', background: isActive ? 'var(--primary-glow)' : 'transparent', marginBottom: '2px' }}>
              {link.icon}
            </div>
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

export default TopHeader;
