import React, { useState } from 'react';
import { BookOpen, Database, CheckCircle, Clock, ExternalLink, Copy } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const SourceCard = function({ source, id }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const { t } = useLanguage();

  if (!source) return null;

  const isMedical = source.type === 'diseases';
  const isSelected = source.is_selected !== false; 
  
  const accentColor = isMedical ? 'var(--primary)' : 'var(--success)';
  const glowColor = isMedical ? 'var(--primary-glow)' : 'rgba(16, 185, 129, 0.15)';

  return (
    <div 
      id={id}
      className="glass"
      style={{
        display: 'flex',
        flexDirection: 'column',
        padding: '16px',
        borderRadius: 'var(--radius)',
        color: 'var(--text)',
        marginBottom: '12px',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        cursor: 'pointer',
        border: isSelected 
          ? `1px solid ${accentColor}`
          : '1px solid var(--border)',
        opacity: isSelected ? 1 : 0.65,
        boxShadow: isSelected ? `0 4px 20px ${glowColor}` : 'none',
        background: isSelected ? 'var(--surface)' : 'var(--surface-2)'
      }}
      onClick={() => setIsExpanded(!isExpanded)}
      onMouseOver={(e) => {
        if (!isSelected) {
            e.currentTarget.style.borderColor = accentColor;
            e.currentTarget.style.opacity = '1';
        }
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
      onMouseOut={(e) => {
        if (!isSelected) {
            e.currentTarget.style.borderColor = 'var(--border)';
            e.currentTarget.style.opacity = '0.65';
        }
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
          <div style={{ 
            color: accentColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: glowColor,
            padding: '10px',
            borderRadius: '12px',
            flexShrink: 0
          }}>
            {isMedical ? <BookOpen size={20} /> : <Database size={20} />}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text)' }}>
                {isMedical ? 'Medical Guidelines' : 'Drug Database'}
              </span>
              <span style={{
                fontSize: '0.7rem',
                padding: '3px 8px',
                borderRadius: '6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: isSelected ? glowColor : 'var(--surface-2)',
                color: isSelected ? accentColor : 'var(--text-muted)',
                border: `1px solid ${isSelected ? accentColor : 'var(--border)'}`,
                fontWeight: '600'
              }}>
                {isSelected ? <CheckCircle size={12} /> : <Clock size={12} />}
                {isSelected ? 'Injected' : 'Candidate'}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {source.section || 'General Reference'}
            </div>
          </div>
        </div>
        
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text)', fontWeight: '600' }}>
            {Math.round((source.score || 0) * 100)}%
          </div>
          <div style={{ 
            width: '40px', 
            height: '6px', 
            background: 'var(--surface-2)',
            borderRadius: '3px',
            marginTop: '6px',
            overflow: 'hidden'
          }}>
            <div style={{ 
              width: `${Math.max(10, (source.score || 0) * 100)}%`, 
              height: '100%', 
              background: accentColor,
              borderRadius: '3px'
            }} />
          </div>
        </div>
      </div>

      {isExpanded && source.content && (
        <div 
          className="fade-up"
          style={{ 
            marginTop: '16px', 
            paddingTop: '16px', 
            borderTop: '1px dashed var(--border)',
            fontSize: '0.85rem',
            color: 'var(--text)'
          }}
        >
          {(() => {
            if (!source.metadata) return null;
            let meta = { ...source.metadata };
            if (typeof meta.source === 'string' && meta.source.startsWith('{')) {
              try {
                const parsed = JSON.parse(meta.source);
                meta = { ...meta, ...parsed };
              } catch (e) {
                console.error('Failed to parse metadata source', e);
              }
            }
            return (
              <div style={{
                marginBottom: '16px',
                padding: '12px 16px',
                borderRadius: '10px',
                background: 'var(--surface-2)',
                border: '1px solid var(--border)',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                gap: '8px',
                lineHeight: '1.5'
              }}>
                <div style={{ gridColumn: '1 / -1', fontWeight: '700', color: accentColor, marginBottom: '4px' }}>Metadata:</div>
                {meta.page_title && <div><span style={{color:'var(--text-muted)'}}>Page:</span> <strong style={{color:'var(--text)'}}>{meta.page_title}</strong></div>}
                {meta.name_en && <div><span style={{color:'var(--text-muted)'}}>Name:</span> <strong style={{color:'var(--text)'}}>{meta.name_en}</strong></div>}
                {meta.active_ingredients && <div><span style={{color:'var(--text-muted)'}}>Active Ingredient:</span> <strong style={{color:'var(--text)'}}>{meta.active_ingredients}</strong></div>}
                {meta.drug_class && <div><span style={{color:'var(--text-muted)'}}>Class:</span> <strong style={{color:'var(--text)'}}>{meta.drug_class}</strong></div>}
                {meta.manufacturer && <div><span style={{color:'var(--text-muted)'}}>Manufacturer:</span> <strong style={{color:'var(--text)'}}>{meta.manufacturer}</strong></div>}
                {meta.route && <div><span style={{color:'var(--text-muted)'}}>Route:</span> <strong style={{color:'var(--text)'}}>{meta.route}</strong></div>}
              </div>
            );
          })()}
          
          <div style={{ 
            marginBottom: '16px', 
            lineHeight: '1.6', 
            background: 'var(--surface-2)', 
            padding: '16px', 
            borderRadius: '10px', 
            border: '1px solid var(--border)',
            whiteSpace: 'pre-wrap',
            maxHeight: '250px',
            overflowY: 'auto',
            color: 'var(--text)'
          }}>
            <div style={{ fontWeight: '700', color: accentColor, marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
              <span>Raw Vector Content</span>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  navigator.clipboard.writeText(source.content);
                  setIsCopied(true);
                  setTimeout(() => setIsCopied(false), 2000);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: isCopied ? 'var(--success)' : 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.75rem',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  transition: 'all 0.2s',
                  backgroundColor: isCopied ? 'rgba(16, 185, 129, 0.1)' : 'transparent'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = 'var(--surface)'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = isCopied ? 'rgba(16, 185, 129, 0.1)' : 'transparent'}
              >
                {isCopied ? <CheckCircle size={14} /> : <Copy size={14} />}
                {isCopied ? 'Copied' : 'Copy'}
              </button>
            </div>
            {source.content}
          </div>
          {source.url && source.type !== 'drugs' && (
            <a 
              href={source.url} 
              target="_blank" 
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                color: accentColor,
                textDecoration: 'none',
                fontWeight: '600',
                fontSize: '0.8rem',
                padding: '8px 16px',
                background: glowColor,
                borderRadius: '8px',
                transition: 'all 0.2s',
                border: `1px solid ${accentColor}`
              }}
              onMouseOver={(e) => e.currentTarget.style.filter = 'brightness(1.1)'}
              onMouseOut={(e) => e.currentTarget.style.filter = 'none'}
            >
              <ExternalLink size={14} /> View Document
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export default React.memo(SourceCard);
