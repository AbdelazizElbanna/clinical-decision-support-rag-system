import React, { useState } from 'react';
import { Shield, Check, FileText, AlertTriangle, Database, Brain, Lock } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Terms() {
  const [loading, setLoading] = useState(false);
  const { user, setTermsAccepted } = useAuth();
  const navigate = useNavigate();
  const { t, language } = useLanguage();
  const isRTL = language === 'ar';

  const handleAccept = async () => {
    if (!user) { navigate('/login'); return; }
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${BASE_URL}/api/accept-terms`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
      });
      if (res.ok) {
        setTermsAccepted(true);
        navigate('/');
      }
    } catch (error) {
      console.error('Error accepting terms:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '40px 24px', overflowY: 'auto', height: '100%', direction: isRTL ? 'rtl' : 'ltr', textAlign: isRTL ? 'right' : 'left' }}>
      <div style={{ maxWidth: '680px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <div style={{ width: '80px', height: '80px', borderRadius: '24px', background: 'linear-gradient(135deg, var(--primary), var(--accent))', margin: '0 auto 24px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 32px rgba(129,140,248,0.3)' }}>
            <Shield size={40} color="#fff" />
          </div>
          <h1 style={{ fontSize: '2.5rem', fontWeight: '800', color: 'var(--text)', margin: '0 0 12px 0' }}>{t('terms_page_title')}</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem', margin: 0 }}>{t('terms_page_subtitle')}</p>
        </div>

        {/* 1. Medical Disclaimer */}
        <div className="glass" style={{ padding: '28px', borderRadius: '16px', border: '1px solid rgba(251,191,36,0.3)', background: 'linear-gradient(180deg, rgba(251,191,36,0.05) 0%, transparent 100%)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', color: 'var(--warning)' }}>
            <AlertTriangle size={24} />
            <h2 style={{ fontSize: '1.3rem', fontWeight: '700', margin: 0 }}>{t('terms_disclaimer_title')}</h2>
          </div>
          <p style={{ color: 'var(--text-muted)', lineHeight: '1.6', fontSize: '0.95rem', marginBottom: '16px' }} dangerouslySetInnerHTML={{ __html: t('terms_disclaimer_desc') }}></p>
          <ul style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: '1.7', margin: 0, paddingLeft: isRTL ? '0' : '20px', paddingRight: isRTL ? '20px' : '0' }}>
            <li>{t('terms_disclaimer_li1')}</li>
            <li>{t('terms_disclaimer_li2')}</li>
            <li>{t('terms_disclaimer_li3')}</li>
          </ul>
        </div>

        {/* 2. AI Processing */}
        <div className="glass" style={{ padding: '28px', borderRadius: '16px', border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', color: 'var(--primary)' }}>
            <Brain size={24} />
            <h2 style={{ fontSize: '1.3rem', fontWeight: '700', margin: 0, color: 'var(--text)' }}>{t('terms_ai_title')}</h2>
          </div>
          <p style={{ color: 'var(--text-muted)', lineHeight: '1.6', fontSize: '0.95rem', marginBottom: '16px' }} dangerouslySetInnerHTML={{ __html: t('terms_ai_desc') }}></p>
          <ul style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: '1.7', margin: 0, paddingLeft: isRTL ? '0' : '20px', paddingRight: isRTL ? '20px' : '0' }}>
            <li dangerouslySetInnerHTML={{ __html: t('terms_ai_li1') }}></li>
            <li>{t('terms_ai_li2')}</li>
            <li dangerouslySetInnerHTML={{ __html: t('terms_ai_li3') }}></li>
          </ul>
        </div>

        {/* 3. Data Usage */}
        <div className="glass" style={{ padding: '28px', borderRadius: '16px', border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', color: 'var(--accent)' }}>
            <Database size={24} />
            <h2 style={{ fontSize: '1.3rem', fontWeight: '700', margin: 0, color: 'var(--text)' }}>{t('terms_data_title')}</h2>
          </div>
          <p style={{ color: 'var(--text-muted)', lineHeight: '1.6', fontSize: '0.95rem', marginBottom: '16px' }} dangerouslySetInnerHTML={{ __html: t('terms_data_desc') }}></p>
          <ul style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: '1.7', margin: 0, paddingLeft: isRTL ? '0' : '20px', paddingRight: isRTL ? '20px' : '0', marginBottom: '16px' }}>
            <li dangerouslySetInnerHTML={{ __html: t('terms_data_li1') }}></li>
            <li dangerouslySetInnerHTML={{ __html: t('terms_data_li2') }}></li>
            <li dangerouslySetInnerHTML={{ __html: t('terms_data_li3') }}></li>
          </ul>
          <div style={{ padding: '12px 16px', background: 'var(--surface-2)', borderRadius: '8px', fontSize: '0.85rem', color: 'var(--text-muted)' }} dangerouslySetInnerHTML={{ __html: t('terms_data_footer') }}>
          </div>
        </div>

        {/* 4. Privacy & Local Storage */}
        <div className="glass" style={{ padding: '28px', borderRadius: '16px', border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', color: 'var(--success)' }}>
            <Lock size={24} />
            <h2 style={{ fontSize: '1.3rem', fontWeight: '700', margin: 0, color: 'var(--text)' }}>{t('terms_privacy_title')}</h2>
          </div>
          <ul style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: '1.7', margin: 0, paddingLeft: isRTL ? '0' : '20px', paddingRight: isRTL ? '20px' : '0' }}>
            <li>{t('terms_privacy_li1')}</li>
            <li>{t('terms_privacy_li2')}</li>
            <li>{t('terms_privacy_li3')}</li>
          </ul>
        </div>

        {/* Action Area */}
        <div style={{ marginTop: '16px', padding: '32px', background: 'var(--surface-2)', borderRadius: '20px', textAlign: 'center', border: '1px solid var(--border)' }}>
          {user ? (
            user.terms_accepted ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.15)', color: 'var(--success)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Check size={28} />
                </div>
                <h3 style={{ color: 'var(--success)', margin: 0, fontSize: '1.2rem' }}>{t('agreed_already') || 'You have already agreed to these terms'}</h3>
              </div>
            ) : (
              <>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', marginBottom: '24px' }}>
                  {t('terms_confirm')}
                </p>
                <button
                  onClick={handleAccept}
                  disabled={loading}
                  style={{
                    width: '100%', maxWidth: '400px', padding: '16px',
                    background: 'linear-gradient(135deg, var(--primary), var(--accent))',
                    color: '#fff', border: 'none', borderRadius: '12px',
                    fontSize: '1.05rem', fontWeight: '700', cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
                    boxShadow: '0 4px 15px rgba(129,140,248,0.3)', transition: 'transform 0.2s, box-shadow 0.2s',
                    opacity: loading ? 0.7 : 1
                  }}
                >
                  {loading ? t('terms_processing') : <>{t('terms_understood')} <Check size={20} /></>}
                </button>
              </>
            )
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '1rem', margin: 0 }} dangerouslySetInnerHTML={{ __html: t('terms_login_prompt') }}></p>
          )}
        </div>

        <div style={{ height: '40px' }} />
      </div>
    </div>
  );
}
