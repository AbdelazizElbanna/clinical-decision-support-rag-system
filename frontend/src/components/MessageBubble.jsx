import React, { useState, useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MessageBubble = function({ role, content, isTyping, sources, onCitationClick }) {
  const isUser = role === 'user';
  const { t } = useLanguage();
  const [loadingStep, setLoadingStep] = useState(1);

  useEffect(() => {
    if (isTyping) {
      const interval = setInterval(() => {
        setLoadingStep(prev => (prev < 4 ? prev + 1 : 1));
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [isTyping]);

  const selectedSources = (!isUser && sources?.length > 0)
    ? sources.filter(s => s.is_selected)
    : [];

  let formattedContent = content || '';
  if (selectedSources.length > 0) {
    // 1. Handle flexible "Source(s)" citations: e.g. [Source 1], (Source 2), (Sources 3 & 4), [Sources 1, 2]
    formattedContent = formattedContent.replace(/[\(\[\u3010]Sources?\s+([^\]\)\u3011]+)[\)\]\u3011]/gi, (match, numsStr) => {
      const digitMatches = [...numsStr.matchAll(/\d+/g)];
      if (digitMatches.length === 0) return match;
      const links = digitMatches.map(m => `[Source ${m[0]}](#citation-${m[0]})`);
      return links.join(' ');
    });

    // 2. Legacy fallback for old cached chats with [MEDICAL CONTEXT 1]
    formattedContent = formattedContent.replace(/[\u3010\[](MEDICAL CONTEXT\s*)(\d+)[\u3011\]]/g, (match, prefix, num) => {
      return '[' + match + '](#citation-' + num + ')';
    });
    formattedContent = formattedContent.replace(/[\u3010\[](MEDICAL CONTEXT\s*)(\d+)-(\d+)[\u3011\]]/g, (match, prefix, start, end) => {
      const links = [];
      for (let i = parseInt(start); i <= parseInt(end); i++) {
        links.push(`[Source ${i}](#citation-${i})`);
      }
      return links.join(' ');
    });
  }

  const CitationLink = ({ href, children }) => {
    const citMatch = href && href.match(/^#citation-(\d+)$/);
    if (citMatch) {
      const idx = parseInt(citMatch[1]) - 1;
      const source = selectedSources[idx];
      const rawText = source ? (source.text || source.document || '') : '';
      const tooltip = rawText.substring(0, 300) + (rawText.length > 300 ? '...' : '');
      return React.createElement('button', {
        title: tooltip,
        onClick: (e) => { e.preventDefault(); if (onCitationClick) onCitationClick(idx); },
        style: {
          color: 'var(--accent)',
          background: 'rgba(129,140,248,0.12)',
          padding: '2px 7px',
          borderRadius: '5px',
          border: '1px solid rgba(129,140,248,0.25)',
          fontSize: '0.78em',
          fontWeight: '600',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          display: 'inline-block',
          lineHeight: '1.4',
        },
        onMouseEnter: (e) => { e.currentTarget.style.background = 'rgba(129,140,248,0.28)'; },
        onMouseLeave: (e) => { e.currentTarget.style.background = 'rgba(129,140,248,0.12)'; },
      }, children);
    }
    return React.createElement('a', { href, style: { color: 'var(--primary)', fontWeight: '600', textDecorationColor: 'var(--primary-glow)', textUnderlineOffset: '3px' } }, children);
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      margin: '16px 0',
      width: '100%'
    }} className="fade-up">
      <div style={{
        maxWidth: '85%',
        padding: '14px 18px',
        borderRadius: '20px',
        borderBottomRightRadius: isUser ? '4px' : '20px',
        borderBottomLeftRadius: !isUser ? '4px' : '20px',
        background: isUser ? 'linear-gradient(135deg, var(--primary), var(--accent))' : 'var(--surface)',
        backdropFilter: !isUser ? 'blur(12px)' : 'none',
        WebkitBackdropFilter: !isUser ? 'blur(12px)' : 'none',
        border: !isUser ? '1px solid var(--border)' : 'none',
        color: isUser ? '#fff' : 'var(--text)',
        boxShadow: isUser ? '0 4px 15px rgba(129,140,248,0.3)' : '0 4px 15px rgba(0,0,0,0.1)'
      }}>
        {isTyping ? (
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', height: '24px' }}>
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
              <span style={{ width: '6px', height: '6px', background: 'var(--primary)', borderRadius: '50%', animation: 'pulse 1s infinite alternate' }} />
              <span style={{ width: '6px', height: '6px', background: 'var(--accent)', borderRadius: '50%', animation: 'pulse 1s infinite alternate 0.2s' }} />
              <span style={{ width: '6px', height: '6px', background: 'var(--primary)', borderRadius: '50%', animation: 'pulse 1s infinite alternate 0.4s' }} />
            </div>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: '500', animation: 'fadeIn 0.5s ease' }}>
              {t(`loading_step_${loadingStep}`)}
            </span>
          </div>
        ) : (
          <div className="markdown-body">
            {isUser
              ? formattedContent
              : React.createElement(ReactMarkdown, { remarkPlugins: [remarkGfm], components: { a: CitationLink } }, formattedContent)
            }
          </div>
        )}
      </div>
      <style>{`
        @keyframes pulse {
          0% { transform: scale(0.8); opacity: 0.5; }
          100% { transform: scale(1.2); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

export default React.memo(MessageBubble);

