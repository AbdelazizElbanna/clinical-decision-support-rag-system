import React from 'react';
import { ExternalLink, Mail, Code2 } from 'lucide-react';

export default function Team() {
  const team = [
    { name: 'Salah Abdeldaim', role: 'Lead Developer & AI Engineer', note: 'Built the RAG pipeline, ChromaDB integration, and MedLens AI architecture.' },
  ];

  return (
    <div style={{ padding: '32px 24px', overflowY: 'auto', height: '100%' }}>
      <div style={{ maxWidth: '720px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: '800', color: 'var(--text)', margin: 0 }}>The Team</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>The people behind MedLens AI.</p>
        </div>
        {team.map((member, i) => (
          <div key={i} className="glass" style={{ padding: '28px', borderRadius: '16px', display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
            <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: 'linear-gradient(135deg, var(--primary), var(--accent))', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: '1.4rem', fontWeight: '700', color: '#fff' }}>
              {member.name.charAt(0)}
            </div>
            <div>
              <div style={{ fontWeight: '700', fontSize: '1.2rem', color: 'var(--text)' }}>{member.name}</div>
              <div style={{ color: 'var(--primary)', fontWeight: '600', fontSize: '0.9rem', marginTop: '4px' }}>{member.role}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '8px', lineHeight: '1.6' }}>{member.note}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
