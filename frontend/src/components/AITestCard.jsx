import React, { useState, useEffect } from 'react';
import { Bot, Play, CheckCircle2, AlertCircle, Sparkles, RefreshCw, Zap, MessageSquare } from 'lucide-react';
import api, { formatApiErrorMessage } from '../services/api';

export default function AITestCard() {
  const [aiStatus, setAiStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [runningTest, setRunningTest] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const [testCode, setTestCode] = useState(
    'def calculate_total(items):\n    """Legacy total calculator with missing type hints and edge cases."""\n    total = 0\n    for item in items:\n        total += item["price"]\n    return total'
  );

  const fetchAiStatus = async () => {
    setLoadingStatus(true);
    try {
      const res = await api.get('/api/ai/status');
      setAiStatus(res.data);
    } catch (err) {
      console.error('Failed to fetch AI Status:', err);
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    fetchAiStatus();
  }, []);

  const handleRunAiTest = async () => {
    if (!testCode || runningTest) return;
    setRunningTest(true);
    setErrorMsg(null);
    setTestResult(null);

    try {
      const res = await api.post('/api/ai/test', { code: testCode });
      setTestResult(res.data);
    } catch (err) {
      console.error('AI Test error:', err);
      setErrorMsg(formatApiErrorMessage(err, 'AI test request failed'));
    } finally {
      setRunningTest(false);
    }
  };

  return (
    <div className="status-card" style={{ marginBottom: '2.5rem', padding: '1.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem', fontFamily: 'var(--font-heading)' }}>
            <Sparkles size={24} style={{ color: 'var(--accent-primary)', filter: 'drop-shadow(1.5px 1.5px 0px var(--ink))' }} />
            <span>AI Brain Provider</span>
          </h3>
        </div>

        {aiStatus && (
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', fontSize: '0.85rem' }}>
            <span style={{ 
              padding: '0.35rem 0.85rem', 
              borderRadius: 'var(--radius-pill)', 
              background: aiStatus.configured ? 'var(--accent-success)' : 'var(--accent-warning)', 
              color: '#FFFFFF', 
              border: '2px solid var(--ink)', 
              boxShadow: '2px 2px 0px var(--ink)', 
              fontWeight: 800,
              fontFamily: 'var(--font-heading)'
            }}>
              {aiStatus.configured ? '⚡ Groq Llama 3.3 Active' : 'Fallback Engine'}
            </span>
          </div>
        )}
      </div>

      <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', fontWeight: 500 }}>
        Structured AI LLM layer with fast caching and zero token waste during file indexing!
      </p>

      {/* Code Snippet Test Input */}
      <div style={{ marginBottom: '1.25rem' }}>
        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.5rem', fontFamily: 'var(--font-heading)' }}>
          🧪 Test Code Snippet for AI Engine:
        </label>
        <textarea
          value={testCode}
          onChange={(e) => setTestCode(e.target.value)}
          rows={3}
          style={{
            width: '100%',
            padding: '0.85rem 1.15rem',
            background: '#FFFFFF',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.9rem',
            resize: 'vertical'
          }}
        />
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1.25rem' }}>
        <button
          className="btn-refresh"
          onClick={handleRunAiTest}
          disabled={runningTest}
          style={{ background: 'var(--accent-purple)' }}
        >
          {runningTest ? <RefreshCw size={16} className="spin" /> : <Play size={16} />}
          <span>{runningTest ? 'Asking AI Brain…' : 'Run AI Test'}</span>
        </button>
      </div>

      {/* Test Results Output Comic Bubble */}
      {testResult && (
        <div className="comic-speech-bubble" style={{ background: '#F5F3FF', borderColor: 'var(--accent-purple)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
            <span style={{ fontWeight: 800, color: 'var(--accent-purple)', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)' }}>
              <Bot size={18} /> AI Response:
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
              {testResult.is_mock ? 'Mock Mode' : `Model: ${testResult.model_used}`}
            </span>
          </div>
          <p style={{ fontSize: '0.92rem', color: 'var(--text-primary)', margin: 0, lineHeight: 1.6, fontWeight: 500 }}>
            {testResult.response}
          </p>
        </div>
      )}

      {errorMsg && (
        <div style={{ padding: '0.85rem 1.15rem', borderRadius: 'var(--radius-md)', background: '#FFF0F0', border: '2px solid var(--accent-error)', color: 'var(--accent-error)', fontSize: '0.9rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1rem', boxShadow: '3px 3px 0px var(--accent-error)' }}>
          <AlertCircle size={20} />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}
