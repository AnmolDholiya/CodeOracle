import React, { useState, useEffect } from 'react';
import { 
  Wand2, 
  Code, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Loader2, 
  FileCode, 
  Sparkles, 
  ShieldAlert, 
  GitCompare, 
  Save, 
  Check, 
  Layers, 
  Info,
  Package,
  Activity,
  ArrowRight
} from 'lucide-react';
import api, { formatApiErrorMessage } from '../services/api';

export default function RefactorCard({ projectId, projectFiles = [] }) {
  const refactorableFiles = projectFiles.filter(f => f.relative_path.toLowerCase().match(/\.(py|js|jsx|ts|tsx)$/));
  const [selectedFile, setSelectedFile] = useState(refactorableFiles[0]?.relative_path || '');
  const [functionName, setFunctionName] = useState('');

  useEffect(() => {
    if (refactorableFiles.length > 0 && (!selectedFile || !refactorableFiles.some(f => f.relative_path === selectedFile))) {
      setSelectedFile(refactorableFiles[0].relative_path);
    }
  }, [projectFiles]);
  const [isFunction, setIsFunction] = useState(false);
  
  const [refactorData, setRefactorData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [activeCodeTab, setActiveCodeTab] = useState('refactored'); // 'refactored' | 'original' | 'diff'
  const [errorMsg, setErrorMsg] = useState(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState(null);

  // Trigger AI Refactoring
  const handleRefactor = async (isFunctionCall = false, forceRefresh = false) => {
    if (!selectedFile || loading) return;
    setLoading(true);
    setErrorMsg(null);
    setSaveSuccessMsg(null);

    try {
      let endpoint = `/api/projects/${projectId}/refactor/file`;
      let payload = { file_path: selectedFile, force_refresh: forceRefresh };

      if (isFunctionCall && functionName.trim()) {
        endpoint = `/api/projects/${projectId}/refactor/function`;
        payload = { 
          file_path: selectedFile, 
          function_name: functionName.trim(), 
          force_refresh: forceRefresh 
        };
      }

      const res = await api.post(endpoint, payload);
      setRefactorData(res.data);
      setActiveCodeTab('refactored');
    } catch (err) {
      console.error('Refactoring error:', err);
      setErrorMsg(formatApiErrorMessage(err, 'AI Code Refactoring failed.'));
    } finally {
      setLoading(false);
    }
  };

  // Save Refactored Code to Project Workspace
  const handleSaveCode = async () => {
    if (!refactorData || !refactorData.refactored_code || saving) return;
    setSaving(true);
    setSaveSuccessMsg(null);
    setErrorMsg(null);

    try {
      const res = await api.post(`/api/projects/${projectId}/refactor/save`, {
        file_path: refactorData.file_path,
        refactored_code: refactorData.refactored_code
      });
      setSaveSuccessMsg(res.data.message || 'Refactored code saved successfully!');
    } catch (err) {
      console.error('Save refactored code error:', err);
      setErrorMsg(formatApiErrorMessage(err, 'Failed to save refactored code.'));
    } finally {
      setSaving(false);
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'high':
        return <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.2)', color: 'var(--accent-error)', border: '1px solid rgba(239, 68, 68, 0.4)' }}>HIGH</span>;
      case 'low':
        return <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '4px', background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.4)' }}>LOW</span>;
      default:
        return <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '4px', background: 'rgba(245, 158, 11, 0.2)', color: 'var(--accent-warning)', border: '1px solid rgba(245, 158, 11, 0.4)' }}>MEDIUM</span>;
    }
  };

  return (
    <div className="status-card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
      {/* Section Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Wand2 size={22} style={{ color: 'var(--accent-primary)' }} />
            <span>AI-Powered Code Refactoring</span>
          </h2>
        </div>
      </div>

      {/* Target Selector Bar */}
      <div style={{ background: 'var(--bg-secondary)', padding: '1.25rem 1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', alignItems: 'end' }}>
          {/* Target File */}
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.45rem', display: 'block' }}>
              Target Source File (Python / JS / TS)
            </label>
            <select
              value={selectedFile}
              disabled={refactorableFiles.length === 0}
              onChange={(e) => {
                setSelectedFile(e.target.value);
                setRefactorData(null);
                setErrorMsg(null);
                setSaveSuccessMsg(null);
              }}
              style={{
                width: '100%',
                padding: '0.65rem 0.9rem',
                borderRadius: 'var(--radius-md)',
                background: refactorableFiles.length === 0 ? 'var(--bg-tertiary)' : '#ffffff',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '0.875rem',
                fontFamily: 'var(--font-mono)',
                boxShadow: 'var(--shadow-sm)'
              }}
            >
              {refactorableFiles.length === 0 ? (
                <option value="" disabled>No Python / JS / TS files found in project</option>
              ) : (
                refactorableFiles.map((f) => (
                  <option key={f.relative_path} value={f.relative_path}>
                    {f.relative_path} ({f.lines_of_code || 0} LOC)
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Target Function (Optional) */}
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.45rem', display: 'block' }}>
              Target Function (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. calculate_total (Optional)"
              value={functionName}
              onChange={(e) => setFunctionName(e.target.value)}
              style={{
                width: '100%',
                padding: '0.65rem 0.9rem',
                borderRadius: 'var(--radius-md)',
                background: '#ffffff',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '0.875rem',
                fontFamily: 'var(--font-mono)',
                boxShadow: 'var(--shadow-sm)'
              }}
            />
          </div>

          {/* Buttons */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              disabled={loading || !selectedFile}
              onClick={() => handleRefactor(false, true)}
              className="btn-refresh"
              style={{
                flex: 1,
                justifyContent: 'center',
                opacity: loading ? 0.6 : 1
              }}
            >
              {loading && !functionName ? (
                <>
                  <Loader2 size={16} className="spin" /> Refactoring...
                </>
              ) : (
                <>
                  <Wand2 size={16} /> Refactor Code
                </>
              )}
            </button>

            {functionName.trim() && (
              <button
                disabled={loading}
                onClick={() => handleRefactor(true, true)}
                className="btn-refresh"
                style={{
                  background: 'var(--text-primary)',
                  flex: 1,
                  justifyContent: 'center',
                  opacity: loading ? 0.6 : 1
                }}
              >
                {loading && functionName ? (
                  <>
                    <Loader2 size={16} className="spin" /> Refactoring...
                  </>
                ) : (
                  <>
                    <Sparkles size={16} /> Refactor Function
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Error & Success Toasts */}
      {errorMsg && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', color: 'var(--accent-error)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {saveSuccessMsg && (
        <div style={{ padding: '1rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', color: 'var(--accent-success)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle2 size={18} />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      {/* Refactoring Response Details */}
      {refactorData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Static Fallback Banner */}
          {refactorData.is_fallback && (
            <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-warning)', fontSize: '0.85rem' }}>
              <Info size={16} />
              <span>AI refactoring temporarily unavailable. Static analysis is still available.</span>
            </div>
          )}

          {/* Validation Metrics Banner */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
            {/* Syntax Status */}
            <div style={{ padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {refactorData.validation.syntax_valid ? (
                <CheckCircle2 size={24} style={{ color: 'var(--accent-success)' }} />
              ) : (
                <XCircle size={24} style={{ color: 'var(--accent-error)' }} />
              )}
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>SYNTAX VALIDATION</span>
                <strong style={{ fontSize: '0.95rem', color: refactorData.validation.syntax_valid ? 'var(--accent-success)' : 'var(--accent-error)' }}>
                  {refactorData.validation.syntax_valid ? "Syntax Valid ✅" : "Syntax Error ❌"}
                </strong>
              </div>
            </div>

            {/* Test Execution Validation */}
            <div style={{ padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {refactorData.validation.tests_passed ? (
                <CheckCircle2 size={24} style={{ color: 'var(--accent-success)' }} />
              ) : (
                <XCircle size={24} style={{ color: 'var(--accent-error)' }} />
              )}
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>TEST SUITE VALIDATION</span>
                <strong style={{ fontSize: '0.95rem', color: refactorData.validation.tests_passed ? 'var(--accent-success)' : 'var(--accent-error)' }}>
                  {refactorData.validation.tests_passed ? "All Tests Passed ✅" : "Tests Failed ❌"}
                </strong>
              </div>
            </div>

            {/* Coverage Metric */}
            <div style={{ padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Activity size={24} style={{ color: 'var(--accent-primary)' }} />
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>STATEMENT COVERAGE</span>
                <strong style={{ fontSize: '0.95rem', color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>
                  {refactorData.validation.before_tests?.coverage || 0}% → {refactorData.validation.coverage}%
                </strong>
              </div>
            </div>
          </div>

          {/* Refactoring Summary Card */}
          <div style={{ padding: '1.25rem 1.5rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '0.5rem', fontSize: '1rem', fontWeight: 800 }}>Refactoring Summary</h4>
            <p style={{ fontSize: '0.925rem', color: 'var(--text-primary)', margin: 0, lineHeight: 1.6 }}>{refactorData.summary}</p>

            {/* Issues Found & Improvements Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginTop: '1.25rem' }}>
              {/* Code Smells / Issues Found */}
              <div style={{ padding: '1.15rem 1.25rem', borderRadius: 'var(--radius-md)', background: '#ffffff', border: '1px solid var(--border-color)' }}>
                <h5 style={{ fontSize: '0.875rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <AlertTriangle size={16} style={{ color: 'var(--accent-warning)' }} />
                  <span>Issues Identified ({refactorData.issues_found.length})</span>
                </h5>

                {refactorData.issues_found.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {refactorData.issues_found.map((issue, idx) => (
                      <div key={idx} style={{ padding: '0.6rem 0.75rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', fontSize: '0.825rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                          <strong style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{issue.type.replace('_', ' ')}</strong>
                          {getSeverityBadge(issue.severity)}
                        </div>
                        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{issue.description}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No major code smells detected.</span>
                )}
              </div>

              {/* Improvements Made */}
              <div style={{ padding: '1.15rem 1.25rem', borderRadius: 'var(--radius-md)', background: '#ffffff', border: '1px solid var(--border-color)' }}>
                <h5 style={{ fontSize: '0.875rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Sparkles size={16} style={{ color: 'var(--accent-success)' }} />
                  <span>Improvements Applied ({refactorData.improvements.length})</span>
                </h5>

                {refactorData.improvements.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {refactorData.improvements.map((imp, idx) => (
                      <div key={idx} style={{ padding: '0.6rem 0.75rem', background: 'rgba(16, 185, 129, 0.06)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16, 185, 129, 0.2)', fontSize: '0.825rem' }}>
                        <strong style={{ color: 'var(--accent-success)', textTransform: 'capitalize', display: 'block', marginBottom: '0.2rem' }}>{imp.type.replace('_', ' ')}</strong>
                        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{imp.description}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Baseline formatting applied.</span>
                )}
              </div>
            </div>

            {/* New Dependencies Alert */}
            {refactorData.new_dependencies && refactorData.new_dependencies.length > 0 && (
              <div style={{ marginTop: '1rem', padding: '0.85rem 1rem', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 'var(--radius-md)' }}>
                <h5 style={{ color: 'var(--accent-warning)', fontSize: '0.85rem', fontWeight: 700, margin: '0 0 0.3rem 0', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Package size={16} /> New Dependencies Introduced
                </h5>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-primary)', margin: '0 0 0.4rem 0' }}>
                  The AI refactoring introduced external packages that are not automatically installed:
                </p>
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  {refactorData.new_dependencies.map((pkg, idx) => (
                    <span key={idx} style={{ padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(0,0,0,0.3)', fontFamily: 'var(--font-mono)', fontSize: '0.775rem', color: 'var(--accent-warning)', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
                      pip install {pkg}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Code Tabs & Diff Viewer Header */}
          <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-color)', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => setActiveCodeTab('refactored')}
                  style={{
                    background: activeCodeTab === 'refactored' ? '#a855f7' : 'transparent',
                    color: '#fff',
                    border: 'none',
                    padding: '0.35rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem'
                  }}
                >
                  <Wand2 size={14} /> Refactored Code
                </button>

                <button
                  onClick={() => setActiveCodeTab('original')}
                  style={{
                    background: activeCodeTab === 'original' ? 'var(--accent-primary)' : 'transparent',
                    color: '#fff',
                    border: 'none',
                    padding: '0.35rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem'
                  }}
                >
                  <Code size={14} /> Original Code
                </button>

                <button
                  onClick={() => setActiveCodeTab('diff')}
                  style={{
                    background: activeCodeTab === 'diff' ? 'var(--accent-secondary)' : 'transparent',
                    color: '#fff',
                    border: 'none',
                    padding: '0.35rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem'
                  }}
                >
                  <GitCompare size={14} /> View Diff
                </button>
              </div>

              {/* Save Refactored Code Button */}
              <button
                disabled={saving || !refactorData.validation.syntax_valid}
                onClick={handleSaveCode}
                className="btn-refresh"
                style={{
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  padding: '0.4rem 1rem',
                  fontSize: '0.825rem',
                  opacity: saving || !refactorData.validation.syntax_valid ? 0.5 : 1
                }}
              >
                {saving ? (
                  <>
                    <Loader2 size={15} className="spin" /> Saving...
                  </>
                ) : (
                  <>
                    <Save size={15} /> Save Refactored Code
                  </>
                )}
              </button>
            </div>

            {/* Code Content Pane */}
            <pre style={{ padding: '1rem', margin: 0, fontSize: '0.825rem', color: '#e5e7eb', fontFamily: 'var(--font-mono)', overflowX: 'auto', maxHeight: '350px', lineHeight: '1.45' }}>
              {activeCodeTab === 'refactored' && refactorData.refactored_code}
              {activeCodeTab === 'original' && refactorData.original_code}
              {activeCodeTab === 'diff' && refactorData.diff}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
