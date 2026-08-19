import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const CACHE_KEY = 'medlens_user';
const TOKEN_KEY = 'access_token';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    // Load from cache immediately — no flicker on refresh
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      return cached ? JSON.parse(cached) : null;
    } catch { return null; }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    // Verify token validity in background — don't block UI
    fetch(`${BASE_URL}/api/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => res.ok ? res.json() : null)
    .then(data => {
      if (data) {
        const userObj = { username: data.username, terms_accepted: data.terms_accepted, ...data.profile };
        setUser(userObj);
        localStorage.setItem(CACHE_KEY, JSON.stringify(userObj));
      } else {
        // Token expired or invalid
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(CACHE_KEY);
        localStorage.removeItem('chatSummary');
        setUser(null);
      }
    })
    .catch(() => {
      // Network error — keep using cached data (offline tolerance)
      console.warn('Could not verify token, using cached session.');
    })
    .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const res = await fetch(`${BASE_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      console.error("Login API Error:", err);
      let errorMsg = "Invalid email or password";
      if (err.detail) {
        if (Array.isArray(err.detail)) {
          errorMsg = err.detail.map(e => e.msg).join(', ');
        } else if (typeof err.detail === 'string') {
          errorMsg = err.detail;
        }
      }
      throw new Error(errorMsg);
    }
    const data = await res.json();
    const userObj = { username: data.username, email, terms_accepted: data.terms_accepted, ...data.profile };
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(CACHE_KEY, JSON.stringify(userObj));
    setUser(userObj);
    return userObj;
  };

  const register = async (userData) => {
    const res = await fetch(`${BASE_URL}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Registration failed");
    }
    const data = await res.json();
    const userObj = { username: userData.username, terms_accepted: data.terms_accepted, ...data.profile };
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(CACHE_KEY, JSON.stringify(userObj));
    setUser(userObj);
    return userObj;
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(CACHE_KEY);
    localStorage.removeItem('chatSummary');
    setUser(null);
  };

  const setTermsAccepted = (accepted) => {
    setUser(prev => {
      if (!prev) return null;
      const updated = { ...prev, terms_accepted: accepted };
      localStorage.setItem(CACHE_KEY, JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading, setTermsAccepted }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
