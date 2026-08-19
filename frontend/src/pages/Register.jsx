import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { Sparkles, AlertCircle, User, Mail, Lock, ChevronDown } from 'lucide-react';

export default function Register() {
  const [step, setStep] = useState(1); // 1: account info, 2: profile info
  const [formData, setFormData] = useState({
    username: '', email: '', password: '', confirmPassword: '',
    age: '', gender: '', notes: ''
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));

  const handleStep1 = (e) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    setError('');
    setStep(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await register({
        username: formData.username,
        email: formData.email || null,
        password: formData.password,
        age: formData.age ? parseInt(formData.age) : null,
        gender: formData.gender || null,
        notes: formData.notes || null
      });
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card glass fade-up">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
          <div style={{ background: 'linear-gradient(135deg, var(--primary), var(--accent))', padding: '12px', borderRadius: '16px', display: 'flex' }}>
            <Sparkles size={32} color="#fff" />
          </div>
          <h2 style={{ fontSize: '1.8rem', fontWeight: '700', color: 'var(--text)' }}>Create Account</h2>
          <p style={{ color: 'var(--text-muted)' }}>Join MedLens AI</p>
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            {[1, 2].map(s => (
              <div key={s} style={{
                width: '40px', height: '4px', borderRadius: '2px',
                background: s <= step ? 'var(--primary)' : 'var(--surface-2)',
                transition: 'background 0.3s'
              }} />
            ))}
          </div>
        </div>

        {error && (
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', padding: '12px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem' }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {step === 1 && (
          <form onSubmit={handleStep1} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Step 1 — Account Info</p>
            <input name="username" type="text" placeholder="Full Name" value={formData.username} onChange={handleChange} className="auth-input" required />
            <input name="email" type="email" placeholder="Email" value={formData.email} onChange={handleChange} className="auth-input" required />
            <input name="password" type="password" placeholder="Password (min 6 chars)" value={formData.password} onChange={handleChange} className="auth-input" required />
            <input name="confirmPassword" type="password" placeholder="Confirm Password" value={formData.confirmPassword} onChange={handleChange} className="auth-input" required />
            <button type="submit" className="auth-button" style={{ marginTop: '4px' }}>Continue →</button>
          </form>
        )}

        {step === 2 && (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Step 2 — Patient Profile</p>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>This helps personalize medical recommendations. All fields are optional.</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <input name="age" type="number" placeholder="Age" min="1" max="120" value={formData.age} onChange={handleChange} className="auth-input" />
              <select name="gender" value={formData.gender} onChange={handleChange} className="auth-input" style={{ cursor: 'pointer' }}>
                <option value="">Gender...</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <textarea
              name="notes"
              placeholder="Medical notes (allergies, chronic conditions, etc.) — optional"
              value={formData.notes}
              onChange={handleChange}
              className="auth-input"
              rows={3}
              style={{ resize: 'vertical' }}
            />
            <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
              <button type="button" onClick={() => setStep(1)} style={{ flex: '0 0 auto', background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border)', padding: '14px 20px', borderRadius: '12px', cursor: 'pointer', fontWeight: '600' }}>← Back</button>
              <button type="submit" disabled={isLoading} className="auth-button" style={{ flex: 1 }}>
                {isLoading ? 'Creating Account...' : 'Create Account'}
              </button>
            </div>
          </form>
        )}

        <div style={{ textAlign: 'center', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          Already have an account? <Link to="/login" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: '600' }}>Sign In</Link>
        </div>
      </div>
    </div>
  );
}
