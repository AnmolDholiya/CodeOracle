import React, { useState, useEffect } from 'react';
import { Bot, Play, CheckCircle2, AlertCircle, Sparkles, RefreshCw } from 'lucide-react';
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
    <div className="status-card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Sparkles size={22} style={{ color: 'var(--accent-primary)' }} />
            <span>AI Provider Integration</span>
          </h3>
        </div>

        {aiStatus && (
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', fontSize: '0.825rem' }}>
            <span style={{ padding: '0.2rem 0.6rem', borderRadius: '9999px', background: aiStatus.configured ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)', color: aiStatus.configured ? 'var(--accent-success)' : 'var(--accent-warning)', border: `1px solid ${aiStatus.configured ? 'rgba(16, 185, 129, 0.25)' : 'rgba(245, 158, 11, 0.25)'}`, fontWeight: 700 }}>
              {aiStatus.configured ? 'AI Active' : 'Fallback Mode'}
            </span>
          </div>
        )}
      </div>

      <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Structured AI LLM Provider layer.
      </p>

      {/* Code Snippet Test Input */}
      <div style={{ marginBottom: '1rem' }}>
        <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.4rem' }}>
          Test Code Snippet:
        </label>
        <textarea
          value={testCode}
          onChange={(e) => setTestCode(e.target.value)}
          rows={3}
          style={{
            width: '100%',
            padding: '0.75rem 1rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            background: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem',
            outline: 'none',
            resize: 'vertical'
          }}
        />
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
        <button
          className="btn-refresh"
          onClick={handleRunAiTest}
          disabled={runningTest}
        >
          {runningTest ? <RefreshCw size={15} className="spin" /> : <Play size={15} />}
          <span>{runningTest ? 'Calling AI Service...' : 'Run AI Service Test'}</span>
        </button>
      </div>

      {/* Test Results Output */}
      {testResult && (
        <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'rgba(168, 85, 247, 0.1)', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 700, color: '#c084fc', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Bot size={16} /> AI Explanation Output:
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {testResult.is_mock ? 'Mock Mode' : `Model: ${testResult.model_used}`}
            </span>
          </div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', margin: 0, lineHeight: 1.5 }}>
            {testResult.response}
          </p>
        </div>
      )}

      {errorMsg && (
        <div style={{ padding: '0.85rem', borderRadius: 'var(--radius-md)', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: 'var(--accent-error)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}
