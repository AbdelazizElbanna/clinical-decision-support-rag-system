import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { Sparkles, AlertCircle } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="auth-container">
      <form onSubmit={handleSubmit} className="auth-card glass fade-up">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
          <div style={{ background: 'linear-gradient(135deg, var(--primary), var(--accent))', padding: '12px', borderRadius: '16px', display: 'flex' }}>
            <Sparkles size={32} color="#fff" />
          </div>
          <h2 style={{ fontSize: '1.8rem', fontWeight: '700' }}>Welcome Back</h2>
          <p style={{ color: 'var(--text-muted)' }}>Login to MedLens AI</p>
        </div>

        {error && (
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', padding: '12px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem' }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <input type="email" placeholder="Email Address" value={email} onChange={e => setEmail(e.target.value)} className="auth-input" required />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} className="auth-input" required />
        </div>

        <button type="submit" className="auth-button">Sign In</button>
        
        <div style={{ textAlign: 'center', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          Don't have an account? <Link to="/register" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: '600' }}>Create one</Link>
        </div>
      </form>
    </div>
  );
}
