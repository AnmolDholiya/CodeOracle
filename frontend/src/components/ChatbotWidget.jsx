import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, 
  X, 
  Send, 
  RotateCcw, 
  MessageSquare, 
  Bot, 
  User, 
  FileCode, 
  ChevronRight, 
  CheckCircle2,
  ExternalLink,
  Layers,
  HelpCircle
} from 'lucide-react';
import { sendChatMessage, formatApiErrorMessage } from '../services/api';

const QUICK_ACTIONS = [
  { label: '✨ Explain this project', query: 'Can you give me a high-level explanation of this project and its core architecture?' },
  { label: '📁 Explain important files', query: 'What are the most important source files in this codebase and what do they do?' },
  { label: '🔗 Explain dependencies', query: 'Which modules are the main dependency hubs in this project?' },
  { label: '🧪 What tests are missing?', query: 'What is the current test coverage status and which files have testing gaps?' },
  { label: '🚀 What should I improve?', query: 'What are the top evidence-backed improvement opportunities in this codebase?' },
  { label: '⚠️ Explain breaking changes', query: 'Are there any potential breaking change risks or architectural coupling issues in this project?' },
];

export default function ChatbotWidget({ projectId, currentFile = null }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 'welcome-msg',
      sender: 'ai',
      text: "Hi! I'm CodeOracle AI 👋\n\nI can answer questions about your analyzed project, dependencies, code structure, tests, breaking changes, and improvement opportunities.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      sources: []
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(() => 'conv_' + Math.random().toString(36).substring(2, 9));
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen, messages]);

  const handleSend = async (messageText = null) => {
    const textToSend = (messageText || inputMessage).trim();
    if (!textToSend || loading) return;

    const userMessageId = 'msg_' + Date.now();
    const newMsg = {
      id: userMessageId,
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, newMsg]);
    if (!messageText) setInputMessage('');
    setLoading(true);

    try {
      const res = await sendChatMessage(projectId, textToSend, conversationId, currentFile);
      if (res.conversation_id) {
        setConversationId(res.conversation_id);
      }

      const aiMsg = {
        id: 'ai_' + Date.now(),
        sender: 'ai',
        text: res.answer,
        sources: res.sources || [],
        verified_facts: res.verified_facts || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        modelUsed: res.model_used
      };

      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      console.error('Chat error:', err);
      const errorMsg = {
        id: 'err_' + Date.now(),
        sender: 'ai',
        text: "⚠️ " + formatApiErrorMessage(err, "I encountered an error connecting to the AI service. If the cloud server is waking up, please try again in a few seconds."),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: 'welcome-msg',
        sender: 'ai',
        text: "Conversation cleared. Ask me anything about your analyzed codebase!",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: []
      }
    ]);
    setConversationId('conv_' + Math.random().toString(36).substring(2, 9));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Basic Markdown Renderer for AI responses
  const renderMessageContent = (text = '') => {
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      // Headers
      if (line.startsWith('### ')) {
        return <h5 key={idx} style={{ margin: '0.6rem 0 0.3rem', fontSize: '1rem', fontWeight: 800, fontFamily: 'var(--font-heading)' }}>{line.replace('### ', '')}</h5>;
      }
      if (line.startsWith('## ')) {
        return <h4 key={idx} style={{ margin: '0.8rem 0 0.4rem', fontSize: '1.08rem', fontWeight: 800, fontFamily: 'var(--font-heading)' }}>{line.replace('## ', '')}</h4>;
      }
      if (line.startsWith('# ')) {
        return <h3 key={idx} style={{ margin: '1rem 0 0.5rem', fontSize: '1.2rem', fontWeight: 800, fontFamily: 'var(--font-heading)' }}>{line.replace('# ', '')}</h3>;
      }
      // Blockquotes
      if (line.startsWith('> ')) {
        return (
          <div key={idx} style={{ borderLeft: '3px solid var(--accent-primary)', paddingLeft: '0.6rem', margin: '0.4rem 0', color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.86rem' }}>
            {line.replace('> ', '')}
          </div>
        );
      }
      // Bullet list items
      if (line.startsWith('- ') || line.startsWith('• ') || line.startsWith('* ')) {
        const bulletText = line.substring(2);
        return (
          <div key={idx} style={{ display: 'flex', gap: '0.4rem', marginLeft: '0.4rem', marginY: '0.2rem', fontSize: '0.88rem' }}>
            <span>•</span>
            <span>{parseInlineCode(bulletText)}</span>
          </div>
        );
      }
      // Empty line
      if (!line.trim()) {
        return <div key={idx} style={{ height: '0.4rem' }} />;
      }
      // Normal paragraph
      return <p key={idx} style={{ margin: '0.25rem 0', fontSize: '0.88rem', lineHeight: 1.45 }}>{parseInlineCode(line)}</p>;
    });
  };

  const parseInlineCode = (str = '') => {
    const parts = str.split(/(`[^`]+`)/g);
    return parts.map((part, pIdx) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={pIdx} style={{ background: 'var(--bg-secondary)', padding: '0.1rem 0.35rem', borderRadius: '4px', border: '1px solid var(--ink)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <>
      {/* ── Floating Launcher Button ──────────────────────────────── */}
      {!isOpen && (
        <div style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 999 }}>
          <button
            type="button"
            onClick={() => setIsOpen(true)}
            aria-label="Open CodeOracle AI assistant"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              background: '#FF3385',
              color: '#FFFFFF',
              border: '2.5px solid var(--ink)',
              borderRadius: 'var(--radius-pill)',
              padding: '0.75rem 1.35rem',
              boxShadow: '4px 4px 0px var(--ink)',
              fontWeight: 800,
              fontSize: '0.95rem',
              cursor: 'pointer',
              fontFamily: 'var(--font-heading)',
              transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translate(-2px, -2px)';
              e.currentTarget.style.boxShadow = '6px 6px 0px var(--ink)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.boxShadow = '4px 4px 0px var(--ink)';
            }}
          >
            <Sparkles size={20} className="spin-slow" />
            <span>✨ CodeOracle AI</span>
          </button>
        </div>
      )}

      {/* ── Floating Chat Panel ──────────────────────────────────── */}
      {isOpen && (
        <div 
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            width: '410px',
            maxWidth: 'calc(100vw - 32px)',
            height: '620px',
            maxHeight: 'calc(100vh - 48px)',
            background: '#FFFFFF',
            border: '3px solid var(--ink)',
            borderRadius: '18px',
            boxShadow: '6px 6px 0px var(--ink)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            zIndex: 999,
            animation: 'slideUp 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)'
          }}
        >
          {/* Chat Header */}
          <div style={{
            background: '#FF3385',
            color: '#FFFFFF',
            padding: '0.85rem 1.15rem',
            borderBottom: '2.5px solid var(--ink)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
              <div style={{ background: '#FFFFFF', color: '#FF3385', width: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1.5px solid var(--ink)' }}>
                <Sparkles size={16} />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, fontFamily: 'var(--font-heading)', letterSpacing: '-0.01em' }}>
                  CodeOracle AI
                </h4>
                <div style={{ fontSize: '0.75rem', opacity: 0.92, fontWeight: 600 }}>
                  Ask anything about your analyzed project
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <button
                type="button"
                onClick={handleClearChat}
                title="Clear conversation"
                style={{
                  background: 'rgba(0,0,0,0.15)',
                  border: '1.5px solid #FFFFFF',
                  borderRadius: '50%',
                  width: '28px',
                  height: '28px',
                  color: '#FFFFFF',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.15s ease'
                }}
              >
                <RotateCcw size={14} />
              </button>

              <button
                type="button"
                onClick={() => setIsOpen(false)}
                title="Close chat"
                style={{
                  background: 'rgba(0,0,0,0.15)',
                  border: '1.5px solid #FFFFFF',
                  borderRadius: '50%',
                  width: '28px',
                  height: '28px',
                  color: '#FFFFFF',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '1rem',
                  transition: 'all 0.15s ease'
                }}
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Chat Messages Body */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1rem',
            background: '#F8FAFC',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem'
          }}>
            {messages.map((msg) => {
              const isUser = msg.sender === 'user';
              return (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '100%'
                  }}
                >
                  <div
                    style={{
                      maxWidth: '85%',
                      padding: '0.75rem 1rem',
                      borderRadius: isUser ? '14px 14px 3px 14px' : '14px 14px 14px 3px',
                      background: isUser ? '#FFF0F6' : '#FFFFFF',
                      color: 'var(--text-primary)',
                      border: '2px solid var(--ink)',
                      boxShadow: '2.5px 2.5px 0px var(--ink)',
                      wordBreak: 'break-word'
                    }}
                  >
                    {isUser ? (
                      <p style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: '#FF3385' }}>
                        {msg.text}
                      </p>
                    ) : (
                      <div>
                        {renderMessageContent(msg.text)}

                        {/* Verified Sources references drawer */}
                        {msg.sources && msg.sources.length > 0 && (
                          <div style={{ marginTop: '0.65rem', borderTop: '1.5px solid var(--bg-secondary)', paddingTop: '0.5rem' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', marginBottom: '0.3rem', fontFamily: 'var(--font-heading)' }}>
                              🔍 Verified Sources:
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                              {msg.sources.map((src, sIdx) => (
                                <div key={sIdx} style={{ fontSize: '0.78rem', background: 'var(--bg-secondary)', padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid var(--ink)', fontFamily: 'var(--font-mono)' }}>
                                  📄 <strong>{src.file}</strong> {src.lines ? `(Lines ${src.lines})` : ''}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem', paddingX: '0.3rem', fontWeight: 600 }}>
                    {msg.timestamp}
                  </span>
                </div>
              );
            })}

            {/* Quick Action Buttons (shown if 1-2 messages in history) */}
            {messages.length <= 2 && (
              <div style={{ marginTop: '0.5rem' }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-muted)', marginBottom: '0.5rem', fontFamily: 'var(--font-heading)' }}>
                  💡 Suggested Questions:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {QUICK_ACTIONS.map((qa, qIdx) => (
                    <button
                      key={qIdx}
                      type="button"
                      onClick={() => handleSend(qa.query)}
                      disabled={loading}
                      style={{
                        textAlign: 'left',
                        padding: '0.45rem 0.75rem',
                        background: '#FFFFFF',
                        border: '1.5px solid var(--ink)',
                        borderRadius: '8px',
                        fontSize: '0.8rem',
                        fontWeight: 700,
                        color: 'var(--text-primary)',
                        cursor: 'pointer',
                        boxShadow: '1.5px 1.5px 0px var(--ink)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontFamily: 'var(--font-heading)'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#FFF0F6'}
                      onMouseLeave={(e) => e.currentTarget.style.background = '#FFFFFF'}
                    >
                      <span>{qa.label}</span>
                      <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Loading Indicator */}
            {loading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#FFFFFF', padding: '0.6rem 0.9rem', borderRadius: '12px', border: '2px solid var(--ink)', boxShadow: '2px 2px 0px var(--ink)', maxWidth: '75%' }}>
                <Sparkles size={16} className="spin" style={{ color: '#FF3385' }} />
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-heading)' }}>
                  CodeOracle AI is thinking…
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div style={{
            padding: '0.75rem 1rem',
            background: '#FFFFFF',
            borderTop: '2.5px solid var(--ink)',
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center'
          }}>
            <input
              ref={inputRef}
              type="text"
              placeholder={projectId ? "Ask about your project..." : "Upload a ZIP to ask project questions..."}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              style={{
                flex: 1,
                padding: '0.6rem 0.85rem',
                borderRadius: 'var(--radius-pill)',
                border: '2px solid var(--ink)',
                fontSize: '0.88rem',
                fontFamily: 'var(--font-sans)',
                fontWeight: 600,
                outline: 'none',
                background: '#F8FAFC',
                color: 'var(--text-primary)'
              }}
            />

            <button
              type="button"
              onClick={() => handleSend()}
              disabled={!inputMessage.trim() || loading}
              aria-label="Send message"
              style={{
                background: inputMessage.trim() && !loading ? '#FF3385' : '#E2E8F0',
                color: inputMessage.trim() && !loading ? '#FFFFFF' : '#94A3B8',
                border: '2px solid var(--ink)',
                borderRadius: '50%',
                width: '38px',
                height: '38px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: inputMessage.trim() && !loading ? 'pointer' : 'not-allowed',
                boxShadow: inputMessage.trim() && !loading ? '2px 2px 0px var(--ink)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
