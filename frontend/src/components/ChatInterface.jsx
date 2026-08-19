import React, { useState, useRef, useEffect } from 'react';
import { Send, AlertCircle, Info, Sparkles, Menu, X, Layers, Activity, Trash2 } from 'lucide-react';
import MessageBubble from './MessageBubble';
import WeatherCard from './WeatherCard';
import SourceCard from './SourceCard';
import ConditionBadge from './ConditionBadge';
import PipelineTrace from './PipelineTrace';
import { sendQuery, sendQueryStream } from '../api/client';
import { useLanguage } from '../contexts/LanguageContext';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function ChatInterface() {
  const { user } = useAuth();
  const navigate = useNavigate();



  const { t } = useLanguage();
  const [messages, setMessages] = useState(() => {
    try {
      const saved = sessionStorage.getItem('chatMessages');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return [{ role: 'assistant', content: t('welcome') }];
  });
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentResult, setCurrentResult] = useState(() => {
    try {
      const saved = sessionStorage.getItem('chatCurrentResult');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return null;
  });
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('context'); // 'context' | 'trace'
  const [sourceFilter, setSourceFilter] = useState('all'); // 'all' | 'selected' | 'candidate'
  const [isClearExpanded, setIsClearExpanded] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  
  // Working memory - persisted in localStorage
  const [chatSummary, setChatSummary] = useState(() => {
    try {
      const saved = localStorage.getItem('chatSummary');
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  });

  const filteredSources = currentResult?.sources ? currentResult.sources.filter(s => {
    if (sourceFilter === 'selected') return s.is_selected;
    if (sourceFilter === 'candidate') return !s.is_selected;
    return true;
  }) : [];

  const selectedCount = currentResult?.sources?.filter(s => s.is_selected).length || 0;
  const candidateCount = (currentResult?.sources?.length || 0) - selectedCount;



  // Listen for clear-chat events (e.g. on logout)
  useEffect(() => {
    const handleClear = () => {
      setMessages([{ role: 'assistant', content: t('welcome') }]);
      setChatSummary(null);
      setCurrentResult(null);
      sessionStorage.removeItem('chatMessages');
      sessionStorage.removeItem('chatCurrentResult');
    };
    window.addEventListener('clear-chat', handleClear);
    return () => window.removeEventListener('clear-chat', handleClear);
  }, [t]);

  const handleManualClear = (e) => {
    if (!isClearExpanded) {
      e.preventDefault();
      setIsClearExpanded(true);
    } else {
      e.preventDefault();
      setShowClearConfirm(true);
    }
  };

  const confirmClearChat = () => {
    setMessages([{ role: 'assistant', content: t('welcome') }]);
    setChatSummary(null);
    setCurrentResult(null);
    sessionStorage.removeItem('chatMessages');
    sessionStorage.removeItem('chatCurrentResult');
    setIsClearExpanded(false);
    setShowClearConfirm(false);
  };

  // Persist messages
  useEffect(() => {
    try {
      if (messages.length > 1) {
        sessionStorage.setItem('chatMessages', JSON.stringify(messages));
      } else {
        sessionStorage.removeItem('chatMessages');
      }
    } catch (e) {}
  }, [messages]);

  // Persist currentResult
  useEffect(() => {
    try {
      if (currentResult) {
        sessionStorage.setItem('chatCurrentResult', JSON.stringify(currentResult));
      } else {
        sessionStorage.removeItem('chatCurrentResult');
      }
    } catch (e) {}
  }, [currentResult]);

  const messagesEndRef = useRef(null);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const textareaRef = useRef(null);
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      // Adjust height based on scrollHeight, max out at 150px
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  useEffect(() => {
    const handleToggle = () => setIsSidebarOpen(true);
    window.addEventListener('toggle-sidebar', handleToggle);
    return () => window.removeEventListener('toggle-sidebar', handleToggle);
  }, []);


  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    // Guard: must be logged in and accepted terms
    if (!user) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '**Please [sign in](/login) to use MedLens AI.** Create a free account to get personalized clinical recommendations.'
      }]);
      return;
    }
    if (!user.terms_accepted) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '**Please accept the [Terms of Use](/terms) before sending queries.** This is required to use MedLens AI.'
      }]);
      return;
    }

    const userQuery = input.trim();
    setInput('');
    
    setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
    setIsLoading(true);
    setCurrentResult(null);

    try {
      let latestSources = [];
      await sendQueryStream(
        userQuery, 
        chatSummary,
        (metadata) => {
          latestSources = metadata.sources;
          setCurrentResult({
            weather: metadata.weather,
            sources: metadata.sources,
            intent: metadata.intent,
            trace: metadata.pipeline_trace,
            chunksUsed: metadata.chunks_used,
            usingMockData: metadata.using_mock_data
          });
          
          // Add empty message for streaming
          setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: '',
            sources: latestSources
          }]);
        },
        (chunkText) => {
          setMessages(prev => {
            const newArray = [...prev];
            const last = newArray[newArray.length - 1];
            if (last && last.role === 'assistant') {
              last.content += chunkText;
            }
            return newArray;
          });
        },
        (doneData) => {
          // Make sure final answer is exact
          setMessages(prev => {
            const newArray = [...prev];
            const last = newArray[newArray.length - 1];
            if (last && last.role === 'assistant') {
              last.content = doneData.answer;
              last.sources = latestSources;
            }
            return newArray;
          });
          
          if (doneData.updated_summary) {
            setChatSummary(doneData.updated_summary);
            try {
              localStorage.setItem('chatSummary', JSON.stringify(doneData.updated_summary));
            } catch(e) {
              console.error('Failed to save working memory', e);
            }
          }
          setIsLoading(false);
        },
        (error) => {
          console.error('Query error:', error);
          if (error.message === "terms_required") {
             setMessages(prev => [...prev, { role: 'assistant', content: '**Action Required:** Please accept the [Terms of Use](/terms) to continue.' }]);
          } else {
             setMessages(prev => [...prev, { role: 'assistant', content: 'An error occurred while connecting to MedLens AI. Please check your connection and try again.' }]);
          }
          setIsLoading(false);
        }
      );
    } catch (err) {
      console.error('Stream error:', err);
      setIsLoading(false);
    }
  };

  return (
    <div className="layout-container" style={{ height: "100%", minHeight: 0 }}>
      
      {/* Mobile Overlay */}
      <div 
        className={`sidebar-overlay ${isSidebarOpen ? 'open' : ''}`} 
        onClick={() => setIsSidebarOpen(false)}
      />

      {/* Left Sidebar for Context & Trace */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        
        {/* Sleek Sidebar Header */}
        <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontWeight: '600', fontSize: '1.1rem', color: 'var(--text)' }}>
            {t('sources_tab')}
          </div>
          <button
            className="mobile-close-btn"
            onClick={() => setIsSidebarOpen(false)}
            style={{
              background: 'var(--surface-2)',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.2s'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Tabs for Context & Trace */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
          <button
            onClick={() => setActiveTab('context')}
            style={{
              flex: 1,
              padding: '12px',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'context' ? '2px solid var(--primary)' : '2px solid transparent',
              color: activeTab === 'context' ? 'var(--text)' : 'var(--text-muted)',
              fontWeight: activeTab === 'context' ? '600' : '400',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <Layers size={16} />
            Sources & Context
          </button>
          <button
            onClick={() => setActiveTab('trace')}
            style={{
              flex: 1,
              padding: '12px',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'trace' ? '2px solid var(--primary)' : '2px solid transparent',
              color: activeTab === 'trace' ? 'var(--text)' : 'var(--text-muted)',
              fontWeight: activeTab === 'trace' ? '600' : '400',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <Activity size={16} />
            RAG Trace
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {activeTab === 'trace' ? (
            <PipelineTrace trace={currentResult?.trace} intent={currentResult?.intent} weather={currentResult?.weather} sources={currentResult?.sources} />
          ) : (
            <div>
              {!currentResult && (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                  <Info size={32} style={{ opacity: 0.5 }} />
                  <p>{t('sidebar_empty')}</p>
                </div>
              )}
              
              {currentResult?.intent?.condition && (
                <div style={{ marginBottom: '24px' }}>
                  <ConditionBadge condition={currentResult.intent.condition} />
                </div>
              )}
              
              {currentResult?.weather && (
                <div style={{ marginBottom: '24px' }}>
                  <WeatherCard weatherData={currentResult.weather} />
                </div>
              )}
              
              {currentResult?.sources?.length > 0 && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      <Info size={14} /> Retrieved Chunks ({currentResult.sources.length})
                    </div>
                  </div>

                  {/* Filter Pills */}
                  <div style={{ display: 'flex', gap: '6px', marginBottom: '12px', overflowX: 'auto', paddingBottom: '4px' }}>
                    <button
                      onClick={() => setSourceFilter('all')}
                      style={{
                        fontSize: '0.7rem',
                        padding: '3px 8px',
                        borderRadius: '6px',
                        border: 'none',
                        cursor: 'pointer',
                        background: sourceFilter === 'all' ? 'var(--primary)' : 'var(--surface-2)',
                        color: sourceFilter === 'all' ? '#fff' : 'var(--text-muted)',
                        fontWeight: sourceFilter === 'all' ? '600' : '400'
                      }}
                    >
                      All ({currentResult.sources.length})
                    </button>
                    <button
                      onClick={() => setSourceFilter('selected')}
                      style={{
                        fontSize: '0.7rem',
                        padding: '3px 8px',
                        borderRadius: '6px',
                        border: 'none',
                        cursor: 'pointer',
                        background: sourceFilter === 'selected' ? 'var(--success)' : 'var(--surface-2)',
                        color: sourceFilter === 'selected' ? '#fff' : 'var(--text-muted)',
                        fontWeight: sourceFilter === 'selected' ? '600' : '400'
                      }}
                    >
                      In Context ({selectedCount})
                    </button>
                    <button
                      onClick={() => setSourceFilter('candidate')}
                      style={{
                        fontSize: '0.7rem',
                        padding: '3px 8px',
                        borderRadius: '6px',
                        border: 'none',
                        cursor: 'pointer',
                        background: sourceFilter === 'candidate' ? 'var(--surface-3, rgba(255,255,255,0.15))' : 'var(--surface-2)',
                        color: sourceFilter === 'candidate' ? 'var(--text)' : 'var(--text-muted)',
                        fontWeight: sourceFilter === 'candidate' ? '600' : '400'
                      }}
                    >
                      Candidates ({candidateCount})
                    </button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {filteredSources.map((src, i) => (
                       <SourceCard key={src.id || i} source={src} id={src.is_selected ? `chunk-card-${currentResult.sources.filter(s => s.is_selected).indexOf(src)}` : undefined} />
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}
        </div>
      </aside>


      {/* Main Chat Area */}
      <main className="main-chat" style={{ position: 'relative' }}>
        
        {/* Floating Clear Button */}
        {messages.length > 1 && (
          <button
            onClick={handleManualClear}
            onMouseEnter={() => setIsClearExpanded(true)}
            onMouseLeave={() => setIsClearExpanded(false)}
            title={t('clear_chat')}
            style={{
              position: 'absolute',
              top: '20px',
              right: '0',
              zIndex: 10,
              background: 'var(--surface-2)',
              border: '1px solid var(--border)',
              borderRight: 'none',
              color: isClearExpanded ? 'var(--error)' : 'var(--text-muted)',
              padding: '8px 12px',
              borderRadius: '20px 0 0 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: '500',
              boxShadow: '-4px 4px 12px rgba(0,0,0,0.1)',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              backdropFilter: 'blur(8px)',
              transform: isClearExpanded ? 'translateX(0)' : 'translateX(calc(100% - 32px))',
            }}
          >
            <Trash2 size={16} />
            <span className="hide-on-mobile">{t('clear_chat')}</span>
          </button>
        )}

        {/* Custom Confirmation Modal */}
        {showClearConfirm && (
          <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.6)',
            backdropFilter: 'blur(4px)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            animation: 'fadeIn 0.2s ease'
          }}>
            <div className="glass" style={{
              background: 'var(--surface-1)',
              padding: '24px',
              borderRadius: '24px',
              maxWidth: '320px',
              width: '100%',
              boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
              textAlign: 'center',
              border: '1px solid var(--border)',
              animation: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
            }}>
              <div style={{
                background: 'rgba(239, 68, 68, 0.1)',
                width: '64px', height: '64px',
                borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 16px auto'
              }}>
                <Trash2 size={32} color="var(--error)" />
              </div>
              <h3 style={{ marginBottom: '12px', color: 'var(--text)', fontSize: '1.2rem' }}>{t('clear_chat')}</h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '24px', fontSize: '0.95rem', lineHeight: '1.5' }}>
                {t('confirm_clear')}
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => setShowClearConfirm(false)}
                  style={{
                    flex: 1,
                    padding: '12px',
                    borderRadius: '12px',
                    border: '1px solid var(--border)',
                    background: 'var(--surface-2)',
                    color: 'var(--text)',
                    cursor: 'pointer',
                    fontWeight: '600',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseOver={(e) => e.target.style.background = 'var(--surface-3)'}
                  onMouseOut={(e) => e.target.style.background = 'var(--surface-2)'}
                >
                  {t('cancel') || 'Cancel'}
                </button>
                <button
                  onClick={confirmClearChat}
                  style={{
                    flex: 1,
                    padding: '12px',
                    borderRadius: '12px',
                    border: 'none',
                    background: 'var(--error)',
                    color: '#fff',
                    cursor: 'pointer',
                    fontWeight: '600',
                    transition: 'all 0.2s ease',
                    boxShadow: '0 4px 12px rgba(239, 68, 68, 0.2)'
                  }}
                  onMouseOver={(e) => { e.target.style.transform = 'translateY(-1px)'; e.target.style.boxShadow = '0 6px 16px rgba(239, 68, 68, 0.3)'; }}
                  onMouseOut={(e) => { e.target.style.transform = 'translateY(0)'; e.target.style.boxShadow = '0 4px 12px rgba(239, 68, 68, 0.2)'; }}
                >
                  {t('clear') || 'Clear'}
                </button>
              </div>
            </div>
          </div>
        )}


        <div className="chat-padding" style={{ flex: 1, overflowY: 'auto', padding: '32px 40px', display: 'flex', flexDirection: 'column' }}>
          {messages.map((msg, i) => (
            <MessageBubble 
              key={i} 
              role={msg.role} 
              content={msg.content} 
              sources={msg.sources}
              onCitationClick={(chunkIdx) => {
                // Switch to sources tab
                setActiveTab('sources');
                // Open sidebar on mobile
                setIsSidebarOpen(true);
                // After render, scroll to and highlight the chunk card
                setTimeout(() => {
                  const card = document.getElementById(`chunk-card-${chunkIdx}`);
                  if (card) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    card.style.boxShadow = '0 0 0 2px var(--accent), 0 0 20px rgba(129,140,248,0.5)';
                    card.style.transition = 'box-shadow 0.3s ease';
                    setTimeout(() => {
                      card.style.boxShadow = '';
                    }, 2500);
                  }
                }, 300);
              }}
            />
          ))}
          {isLoading && <MessageBubble role="assistant" isTyping={true} />}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="input-padding" style={{ padding: '16px 40px 24px' }}>
          <form className="glass" onSubmit={handleSend} style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', position: 'relative', borderRadius: '24px', padding: '6px 8px' }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('input_placeholder')}
                rows={1}
                style={{
                  width: '100%',
                  padding: '16px 20px',
                  paddingRight: '60px',
                  borderRadius: '20px',
                  border: 'none',
                  background: 'transparent',
                  color: 'var(--text)',
                  fontSize: '1rem',
                  outline: 'none',
                  resize: 'none',
                  maxHeight: '150px',
                  overflowY: 'auto',
                  fontFamily: 'inherit',
                  lineHeight: '1.5',
                  boxSizing: 'border-box'
                }}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                style={{
                  position: 'absolute',
                  right: '4px',
                  bottom: '4px',
                  background: input.trim() && !isLoading ? 'linear-gradient(135deg, var(--primary), var(--accent))' : 'var(--surface-2)',
                  color: input.trim() && !isLoading ? '#fff' : 'var(--text-muted)',
                  border: 'none',
                  padding: '12px',
                  borderRadius: '16px',
                  cursor: input.trim() && !isLoading ? 'pointer' : 'default',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.3s ease',
                  boxShadow: input.trim() && !isLoading ? '0 4px 12px rgba(129, 140, 248, 0.3)' : 'none'
                }}
              >
                <Send size={18} />
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
