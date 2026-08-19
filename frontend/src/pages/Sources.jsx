import React from 'react';
import { Database, BookOpen, ExternalLink, Code2 } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function Sources() {
  const { t, language } = useLanguage();
  const isRTL = language === 'ar';

  const sources = [
    {
      category: t('cat_gov'),
      name: t('src_eda_name'),
      desc: t('src_eda_desc'),
      url: 'https://www.edaegypt.gov.eg/',
      icon: <Database size={24} />,
      color: 'var(--success)',
      glow: 'rgba(16, 185, 129, 0.12)',
      badge: t('badge_official')
    },
    {
      category: t('cat_community'),
      name: t('src_karem_name'),
      desc: t('src_karem_desc'),
      url: 'https://github.com/karem505/egyptian-drug-database',
      icon: <Code2 size={24} />,
      color: 'var(--primary)',
      glow: 'var(--primary-glow)',
      badge: t('badge_community')
    },
    {
      category: t('cat_community'),
      name: t('src_falous_name'),
      desc: t('src_falous_desc'),
      url: 'https://github.com/mahmoudfalous/eg-drugs',
      icon: <Code2 size={24} />,
      color: 'var(--primary)',
      glow: 'var(--primary-glow)',
      badge: t('badge_community')
    },
    {
      category: t('cat_clinical'),
      name: t('src_ada_name'),
      desc: t('src_ada_desc'),
      url: 'https://www.americandermatology.com/',
      icon: <BookOpen size={24} />,
      color: 'var(--accent)',
      glow: 'rgba(6, 182, 212, 0.12)',
      badge: t('badge_disease_src')
    },
    {
      category: t('cat_clinical'),
      name: t('src_guidelines_name'),
      desc: t('src_guidelines_desc'),
      url: null,
      icon: <BookOpen size={24} />,
      color: 'var(--accent)',
      glow: 'rgba(6, 182, 212, 0.12)',
      badge: t('badge_internal')
    },
    {
      category: t('cat_infra'),
      name: t('src_chroma_name'),
      desc: t('src_chroma_desc'),
      url: 'https://www.trychroma.com/',
      icon: <Database size={24} />,
      color: 'var(--warning)',
      glow: 'rgba(251, 191, 36, 0.12)',
      badge: t('badge_vector')
    },
  ];

  const grouped = sources.reduce((acc, s) => {
    if (!acc[s.category]) acc[s.category] = [];
    acc[s.category].push(s);
    return acc;
  }, {});

  return (
    <div style={{ padding: '32px 24px', overflowY: 'auto', height: '100%', direction: isRTL ? 'rtl' : 'ltr' }}>
      <div style={{ maxWidth: '760px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>

        <div style={{ textAlign: isRTL ? 'right' : 'left' }}>
          <h1 style={{ fontSize: '2rem', fontWeight: '800', color: 'var(--text)', margin: 0 }}>{t('sources_page_title')}</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '8px', lineHeight: '1.7' }}>
            {t('sources_page_subtitle')}
            <strong style={{ color: 'var(--warning)' }}> {t('sources_page_subtitle_bold')}</strong>.
          </p>
        </div>

        {Object.entries(grouped).map(([category, items]) => (
          <div key={category} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', paddingBottom: '8px', borderBottom: '1px solid var(--border)', textAlign: isRTL ? 'right' : 'left' }}>
              {category}
            </div>
            {items.map((s, i) => (
              <div key={i} className="glass" style={{
                padding: '20px', borderRadius: '16px',
                display: 'flex', gap: '16px', alignItems: 'flex-start',
                flexDirection: 'row',
                border: `1px solid ${s.color}30`, transition: 'transform 0.2s, box-shadow 0.2s',
                textAlign: isRTL ? 'right' : 'left'
              }}
              onMouseOver={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = `0 8px 24px ${s.glow}`; }}
              onMouseOut={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
              >
                <div style={{ color: s.color, background: s.glow, padding: '10px', borderRadius: '12px', flexShrink: 0 }}>
                  {s.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '6px' }}>
                    <span style={{ fontWeight: '700', fontSize: '1rem', color: 'var(--text)' }}>{s.name}</span>
                    <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '6px', background: s.glow, color: s.color, fontWeight: '600', whiteSpace: 'nowrap', border: `1px solid ${s.color}40` }}>{s.badge}</span>
                  </div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', lineHeight: '1.65', margin: 0 }}>{s.desc}</p>
                  {s.url && (
                    <a href={s.url} target="_blank" rel="noopener noreferrer"
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', marginTop: '12px', color: s.color, fontWeight: '600', fontSize: '0.82rem', textDecoration: 'none', padding: '4px 10px', background: s.glow, borderRadius: '8px', border: `1px solid ${s.color}40` }}
                    >
                      <ExternalLink size={13} /> {s.url.includes('github') ? t('view_on_github') : t('visit_source')}
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        ))}

        <div style={{ padding: '16px', borderRadius: '12px', background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.3)', fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.7', textAlign: isRTL ? 'right' : 'left' }}>
          <strong style={{ color: 'var(--warning)' }}>{t('sources_disclaimer_prefix')}</strong> {t('sources_disclaimer')}
          <a href="https://www.edaegypt.gov.eg/" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', fontWeight: '600' }}>{t('sources_disclaimer_link')}</a>{t('sources_disclaimer_suffix')}
        </div>
      </div>
    </div>
  );
}
