import React, { useState, useEffect } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Volume2, StopCircle } from 'lucide-react';

// Shared across all instances — only one TTS audio plays at a time
let sharedAudio = null;
let sharedSetSpeaking = null; // to reset the previous bubble's state when a new one starts

const MessageBubble = function({ role, content, isTyping, sources, onCitationClick }) {
  const isUser = role === 'user';
  const { t } = useLanguage();
  const [loadingStep, setLoadingStep] = useState(1);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [ttsWords, setTtsWords] = useState([]);
  const [currentWordIdx, setCurrentWordIdx] = useState(-1);

  useEffect(() => {
    if (isTyping) {
      const interval = setInterval(() => {
        setLoadingStep(prev => (prev < 4 ? prev + 1 : 1));
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [isTyping]);

  // Cleanup if component unmounts while speaking
  useEffect(() => {
    return () => {
      if (sharedSetSpeaking === setIsSpeaking) {
        sharedSetSpeaking = null;
      }
    };
  }, []);

  const stopSpeaking = () => {
    if (sharedAudio) {
      sharedAudio.pause();
      sharedAudio.src = '';   // triggers audio.onerror → resolves the awaited Promise
      sharedAudio = null;
    }
    // MUST go through sharedSetSpeaking so cancel() inside handleSpeak gets called
    if (sharedSetSpeaking) {
      sharedSetSpeaking(false);  // calls cancel() + setIsSpeaking(false)
      sharedSetSpeaking = null;
    } else {
      setIsSpeaking(false);
    }
    setCurrentWordIdx(-1);
  };

  const handleSpeak = async () => {
    if (!content) return;

    // Toggle off if already speaking
    if (isSpeaking) {
      stopSpeaking();
      return;
    }

    // Stop globally
    if (sharedAudio) {
      sharedAudio.pause();
      sharedAudio.src = '';
      sharedAudio = null;
    }
    if (sharedSetSpeaking) {
      sharedSetSpeaking(false);
      sharedSetSpeaking = null;
    }

    setIsSpeaking(true);
    setCurrentWordIdx(-1);
    setTtsWords([]);

    // 1. Chunk the text
    const words = content.replace(/[\*\#\_]/g, '').split(/\s+/);
    const chunks = [];
    let cur = "";
    for (const w of words) {
      if (!w) continue;
      cur += (cur ? " " : "") + w;
      const isPunctuation = /[.؟!،:]$/.test(w);
      // Larger chunks = better prosody. Break on sentence-end (≥120 chars) or hard cap at 250.
      if ((isPunctuation && cur.length > 200) || cur.length > 450) {
        chunks.push(cur);
        cur = "";
      }
    }
    if (cur) chunks.push(cur);

    if (chunks.length === 0) {
      setIsSpeaking(false);
      return;
    }

    // Cancellation flag — set to true when user presses Stop
    let cancelled = false;

    // Store cancel function so Stop button can trigger it
    const cancel = () => { cancelled = true; };
    // Attach to the shared speaking setter so stopSpeaking() also cancels
    sharedSetSpeaking = (val) => {
      if (val === false) cancel();
      setIsSpeaking(val);
    };

    const token = localStorage.getItem('access_token');

    // 2. Kick off all fetches in parallel immediately
    const audioPromises = chunks.map(async (chunkText) => {
      try {
        const res = await fetch('/api/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ text: chunkText }),
        });
        if (!res.ok) return { empty: true };
        const data = await res.json();
        const raw = atob(data.audio);
        const bytes = new Uint8Array(raw.length);
        for (let j = 0; j < raw.length; j++) bytes[j] = raw.charCodeAt(j);
        const blob = new Blob([bytes], { type: 'audio/mpeg' });
        return { url: URL.createObjectURL(blob), words: data.words || [] };
      } catch (e) {
        console.error('TTS fetch error:', e);
        return { error: true };
      }
    });

    // 3. Play chunks sequentially, awaiting each fetch as needed
    const playAll = async () => {
      for (let i = 0; i < chunks.length; i++) {
        if (cancelled) break;

        const chunkData = await audioPromises[i];

        if (cancelled || chunkData.error) break;
        if (chunkData.empty) continue;

        const { url, words: chunkWords } = chunkData;

        await new Promise((resolve) => {
          if (cancelled) { URL.revokeObjectURL(url); return resolve(); }

          const audio = new Audio(url);
          sharedAudio = audio;
          setTtsWords(chunkWords);
          setCurrentWordIdx(-1);

          audio.onended = resolve;
          audio.onerror = resolve;
          audio.ontimeupdate = () => {
            if (cancelled) { audio.pause(); resolve(); return; }
            const ms = audio.currentTime * 1000;
            let found = -1;
            for (let k = 0; k < chunkWords.length; k++) {
              if (ms >= chunkWords[k].start_ms && ms < chunkWords[k].end_ms) { found = k; break; }
            }
            setCurrentWordIdx(found);
          };

          audio.play().catch((e) => {
            console.error("Playback failed:", e);
            resolve();
          });
        });

        URL.revokeObjectURL(url);
        sharedAudio = null;
      }

      // Cleanup on finish or cancel
      setIsSpeaking(false);
      setTtsWords([]);
      setCurrentWordIdx(-1);
      if (sharedSetSpeaking === sharedSetSpeaking) sharedSetSpeaking = null;
    };

    playAll();
  };

  const selectedSources = (!isUser && sources?.length > 0)
    ? sources.filter(s => s.is_selected)
    : [];

  let formattedContent = content || '';
  if (selectedSources.length > 0) {
    formattedContent = formattedContent.replace(/[\(\[\u3010]Sources?\s+([^\]\)\u3011]+)[\)\]\u3011]/gi, (match, numsStr) => {
      const digitMatches = [...numsStr.matchAll(/\d+/g)];
      if (digitMatches.length === 0) return match;
      const links = digitMatches.map(m => `[Source ${m[0]}](#citation-${m[0]})`);
      return links.join(' ');
    });
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
        boxShadow: isUser ? '0 4px 15px rgba(129,140,248,0.3)' : '0 4px 15px rgba(0,0,0,0.1)',
        outline: isSpeaking ? '2px solid rgba(129,140,248,0.4)' : 'none',
        transition: 'outline 0.3s ease',
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

            {/* TTS controls — only on non-empty AI messages */}
            {!isUser && content && (
              <div style={{ marginTop: '10px' }}>
                {/* Play/Stop button */}
                <button
                  onClick={handleSpeak}
                  title={isSpeaking ? (t('stop') || 'Stop') : (t('listen') || 'Listen')}
                  style={{
                    background: isSpeaking ? 'rgba(129,140,248,0.15)' : 'transparent',
                    border: '1px solid',
                    borderColor: isSpeaking ? 'var(--accent)' : 'transparent',
                    color: isSpeaking ? 'var(--accent)' : 'var(--text-muted)',
                    padding: '4px 10px',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    fontSize: '0.75rem',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => { if (!isSpeaking) { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text)'; } }}
                  onMouseLeave={(e) => { if (!isSpeaking) { e.currentTarget.style.borderColor = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; } }}
                >
                  {isSpeaking ? <StopCircle size={14} /> : <Volume2 size={14} />}
                  <span>{isSpeaking ? (t('stop') || 'Stop') : (t('listen') || 'Listen')}</span>
                </button>

                {/* Word karaoke strip — only visible while speaking */}
                {isSpeaking && ttsWords.length > 0 && (
                  <div style={{
                    marginTop: '8px',
                    padding: '8px 12px',
                    background: 'rgba(129,140,248,0.07)',
                    borderRadius: '10px',
                    border: '1px solid rgba(129,140,248,0.15)',
                    fontSize: '0.88rem',
                    lineHeight: '2',
                    userSelect: 'none',
                  }}>
                    {ttsWords.map((w, i) => (
                      <span
                        key={i}
                        style={{
                          display: 'inline-block',
                          margin: '0 3px',
                          padding: '1px 4px',
                          borderRadius: '4px',
                          background: i === currentWordIdx
                            ? 'linear-gradient(135deg, var(--primary), var(--accent))'
                            : 'transparent',
                          color: i === currentWordIdx ? '#fff' : 'var(--text-muted)',
                          fontWeight: i === currentWordIdx ? '700' : '400',
                          transform: i === currentWordIdx ? 'scale(1.08)' : 'scale(1)',
                          transition: 'all 0.1s ease',
                        }}
                      >
                        {w.word}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
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
