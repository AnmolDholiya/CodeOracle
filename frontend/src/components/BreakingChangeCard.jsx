import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Sparkles, 
  FileCode, 
  Info, 
  GitCompare, 
  ArrowRight, 
  HelpCircle,
  Activity,
  Layers,
  Code2,
  FileText
} from 'lucide-react';
import api, { formatApiErrorMessage } from '../services/api';

export default function BreakingChangeCard({ projectId, projectFiles = [] }) {
  const breakableFiles = projectFiles.filter(f => f.relative_path.toLowerCase().match(/\.(py|js|jsx|ts|tsx)$/));
  const [selectedFile, setSelectedFile] = useState(breakableFiles[0]?.relative_path || '');
  const [modifiedCode, setModifiedCode] = useState('');

  useEffect(() => {
    if (breakableFiles.length > 0 && (!selectedFile || !breakableFiles.some(f => f.relative_path === selectedFile))) {
      setSelectedFile(breakableFiles[0].relative_path);
    }
  }, [projectFiles]);
  
  const [analysisData, setAnalysisData] = useState(null);
  const [explanationData, setExplanationData] = useState(null);

  const [analyzing, setAnalyzing] = useState(false);
  const [explaining, setExplaining] = useState(false);

  const [errorMsg, setErrorMsg] = useState(null);
  const [expErrorMsg, setExpErrorMsg] = useState(null);

  // Analyze Breaking Changes via Local AST Comparison
  const handleAnalyze = async (forceRefresh = false) => {
    if (!selectedFile || analyzing) return;
    setAnalyzing(true);
    setErrorMsg(null);
    setExplanationData(null);

    try {
      const res = await api.post(`/api/projects/${projectId}/breaking-changes/analyze`, {
        file_path: selectedFile,
        modified_code: modifiedCode || "",
        force_refresh: forceRefresh
      });
      setAnalysisData(res.data);
    } catch (err) {
      console.error('Breaking change analysis error:', err);
      setErrorMsg(formatApiErrorMessage(err, 'Breaking change analysis failed.'));
    } finally {
      setAnalyzing(false);
    }
  };

  // Explain Breaking Changes via On-Demand Groq AI
  const handleExplain = async (forceRefresh = false) => {
    if (!analysisData || !analysisData.changes || analysisData.changes.length === 0 || explaining) return;
    setExplaining(true);
    setExpErrorMsg(null);

    try {
      const res = await api.post(`/api/projects/${projectId}/breaking-changes/explain`, {
        file_path: selectedFile,
        changes: analysisData.changes,
        force_refresh: forceRefresh
      });
      setExplanationData(res.data);
    } catch (err) {
      console.error('Breaking change explanation error:', err);
      setExpErrorMsg(formatApiErrorMessage(err, 'AI breaking change explanation failed.'));
    } finally {
      setExplaining(false);
    }
  };

  const renderSeverityBadge = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'HIGH':
        return <span style={{ fontSize: '0.7rem', fontWeight: 800, padding: '0.15rem 0.55rem', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.2)', color: 'var(--accent-error)', border: '1px solid rgba(239, 68, 68, 0.4)' }}>HIGH</span>;
      case 'MEDIUM':
        return <span style={{ fontSize: '0.7rem', fontWeight: 800, padding: '0.15rem 0.55rem', borderRadius: '4px', background: 'rgba(245, 158, 11, 0.2)', color: 'var(--accent-warning)', border: '1px solid rgba(245, 158, 11, 0.4)' }}>MEDIUM</span>;
      case 'LOW':
        return <span style={{ fontSize: '0.7rem', fontWeight: 800, padding: '0.15rem 0.55rem', borderRadius: '4px', background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.4)' }}>LOW</span>;
      default:
        return <span style={{ fontSize: '0.7rem', fontWeight: 800, padding: '0.15rem 0.55rem', borderRadius: '4px', background: 'rgba(156, 163, 175, 0.2)', color: 'var(--text-muted)', border: '1px solid var(--border-color)' }}>INFO</span>;
    }
  };

  return (
    <div className="status-card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
      {/* Section Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <ShieldAlert size={22} style={{ color: 'var(--accent-primary)' }} />
            <span>Breaking-Change Detector & AI Explainer</span>
          </h2>
        </div>
      </div>

      {/* Target Selector & Modified Code Input */}
      <div style={{ background: 'var(--bg-secondary)', padding: '1.25rem 1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', alignItems: 'end', marginBottom: '1rem' }}>
          {/* Target File */}
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.45rem', display: 'block' }}>
              Target Source File (Python / JS / TS)
            </label>
            <select
              value={selectedFile}
              disabled={breakableFiles.length === 0}
              onChange={(e) => {
                setSelectedFile(e.target.value);
                setAnalysisData(null);
                setExplanationData(null);
                setErrorMsg(null);
              }}
              style={{
                width: '100%',
                padding: '0.65rem 0.9rem',
                borderRadius: 'var(--radius-md)',
                background: breakableFiles.length === 0 ? 'var(--bg-tertiary)' : '#ffffff',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '0.875rem',
                fontFamily: 'var(--font-mono)',
                boxShadow: 'var(--shadow-sm)'
              }}
            >
              {breakableFiles.length === 0 ? (
                <option value="" disabled>No Python / JS / TS files found in project</option>
              ) : (
                breakableFiles.map((f) => (
                  <option key={f.relative_path} value={f.relative_path}>
                    {f.relative_path} ({f.lines_of_code || 0} LOC)
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Action Button */}
          <div>
            <button
              disabled={analyzing || !selectedFile}
              onClick={() => handleAnalyze(true)}
              className="btn-refresh"
              style={{
                width: '100%',
                justifyContent: 'center',
                padding: '0.65rem 1rem',
                opacity: analyzing ? 0.6 : 1
              }}
            >
              {analyzing ? (
                <>
                  <Loader2 size={16} className="spin" /> Scanning AST...
                </>
              ) : (
                <>
                  <ShieldAlert size={16} /> Analyze Breaking Changes
                </>
              )}
            </button>
          </div>
        </div>

        {/* Optional Candidate Code Input */}
        <div>
          <label style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.35rem', display: 'block' }}>
            Candidate Modified Code (Optional - leave empty to compare against workspace state):
          </label>
          <textarea
            placeholder="Paste modified Python / JS / TS source code to compare against workspace original..."
            value={modifiedCode}
            onChange={(e) => setModifiedCode(e.target.value)}
            rows={3}
            style={{
              width: '100%',
              padding: '0.6rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              fontSize: '0.8rem',
              fontFamily: 'var(--font-mono)',
              resize: 'vertical'
            }}
          />
        </div>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', color: 'var(--accent-error)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Analysis Results Display */}
      {analysisData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Summary Banner */}
          <div style={{ padding: '1.25rem 1.5rem', borderRadius: 'var(--radius-md)', background: analysisData.has_breaking_changes ? 'rgba(239, 68, 68, 0.06)' : 'rgba(16, 185, 129, 0.06)', border: analysisData.has_breaking_changes ? '1px solid rgba(239, 68, 68, 0.2)' : '1px solid rgba(16, 185, 129, 0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {analysisData.has_breaking_changes ? (
                <ShieldAlert size={28} style={{ color: 'var(--accent-error)' }} />
              ) : (
                <CheckCircle2 size={28} style={{ color: 'var(--accent-success)' }} />
              )}
              <div>
                <h4 style={{ fontSize: '1.05rem', fontWeight: 800, margin: '0 0 0.2rem 0', color: analysisData.has_breaking_changes ? 'var(--accent-error)' : 'var(--accent-success)' }}>
                  {analysisData.has_breaking_changes ? `⚠️ ${analysisData.total_changes} Breaking Changes Detected` : "✅ No Breaking Changes Detected"}
                </h4>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', margin: 0 }}>{analysisData.summary}</p>
              </div>
            </div>

            {/* Severity Counts Pills */}
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '0.3rem 0.75rem', borderRadius: '9999px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--accent-error)', border: '1px solid rgba(239, 68, 68, 0.25)' }}>
                {analysisData.high_severity_count} HIGH
              </span>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '0.3rem 0.75rem', borderRadius: '9999px', background: 'rgba(245, 158, 11, 0.1)', color: 'var(--accent-warning)', border: '1px solid rgba(245, 158, 11, 0.25)' }}>
                {analysisData.medium_severity_count} MEDIUM
              </span>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '0.3rem 0.75rem', borderRadius: '9999px', background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                {analysisData.low_severity_count} LOW
              </span>
            </div>
          </div>

          {/* List of Detected Changes */}
          {analysisData.changes.length > 0 && (
            <div style={{ background: 'var(--bg-secondary)', padding: '1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <AlertTriangle size={18} style={{ color: 'var(--accent-warning)' }} />
                  <span>Detected Change Breakdown</span>
                </h4>

                {/* On-Demand Groq AI Explanation Button */}
                <button
                  disabled={explaining}
                  onClick={() => handleExplain(true)}
                  className="btn-refresh"
                  style={{
                    padding: '0.4rem 0.85rem',
                    fontSize: '0.8rem',
                    opacity: explaining ? 0.6 : 1
                  }}
                >
                  {explaining ? (
                    <>
                      <Loader2 size={15} className="spin" /> Generating AI Analysis...
                    </>
                  ) : (
                    <>
                      <Sparkles size={15} /> Explain Breaking Changes
                    </>
                  )}
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {analysisData.changes.map((item, idx) => (
                  <div key={idx} style={{ padding: '0.85rem 1rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {renderSeverityBadge(item.severity)}
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, fontFamily: 'var(--font-mono)', padding: '0.15rem 0.5rem', borderRadius: '4px', background: 'rgba(99, 102, 241, 0.15)', color: 'var(--accent-primary)' }}>
                          {item.type}
                        </span>
                        <strong style={{ fontFamily: 'var(--font-mono)', fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                          {item.symbol}
                        </strong>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {item.file} {item.line_before ? `:L${item.line_before}` : ''}
                      </span>
                    </div>

                    <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      {item.description}
                    </p>

                    {/* Snippet Comparison if available */}
                    {(item.before_snippet || item.after_snippet) && (
                      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                        {item.before_snippet && (
                          <div style={{ flex: 1, minWidth: '200px', background: 'rgba(239, 68, 68, 0.08)', padding: '0.4rem 0.6rem', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.2)', fontSize: '0.775rem', fontFamily: 'var(--font-mono)', color: '#fca5a5' }}>
                            <span style={{ fontSize: '0.675rem', color: 'var(--accent-error)', display: 'block', fontWeight: 700 }}>BEFORE:</span>
                            {item.before_snippet}
                          </div>
                        )}
                        {item.after_snippet && (
                          <div style={{ flex: 1, minWidth: '200px', background: 'rgba(16, 185, 129, 0.08)', padding: '0.4rem 0.6rem', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.2)', fontSize: '0.775rem', fontFamily: 'var(--font-mono)', color: '#6ee7b7' }}>
                            <span style={{ fontSize: '0.675rem', color: 'var(--accent-success)', display: 'block', fontWeight: 700 }}>AFTER:</span>
                            {item.after_snippet}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Affected Files List */}
                    {item.affected_files && item.affected_files.length > 0 && (
                      <div style={{ marginTop: '0.5rem', fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                        <strong>Affected Callers / Dependencies:</strong> {item.affected_files.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Explanation Result Card */}
          {expErrorMsg && (
            <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 'var(--radius-md)', color: 'var(--accent-error)', fontSize: '0.875rem' }}>
              {expErrorMsg}
            </div>
          )}

          {explanationData && (
            <div style={{ padding: '1.25rem', borderRadius: 'var(--radius-md)', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
              <h4 style={{ color: 'var(--accent-primary)', fontSize: '1rem', fontWeight: 700, marginBottom: '0.6rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={18} />
                <span>AI Technical Explanation & Migration Plan</span>
              </h4>

              <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', lineHeight: 1.6, marginBottom: '1rem' }}>
                {explanationData.explanation}
              </p>

              {/* Why It Breaks */}
              {explanationData.why_it_breaks.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <strong style={{ fontSize: '0.825rem', color: 'var(--accent-error)' }}>Why Code Will Break:</strong>
                  <ul style={{ paddingLeft: '1.2rem', margin: '0.3rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                    {explanationData.why_it_breaks.map((reason, idx) => (
                      <li key={idx} style={{ marginBottom: '0.25rem' }}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommended Developer Fixes */}
              {explanationData.recommended_fixes.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <strong style={{ fontSize: '0.825rem', color: 'var(--accent-success)' }}>Recommended Migration Fixes:</strong>
                  <ul style={{ paddingLeft: '1.2rem', margin: '0.3rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                    {explanationData.recommended_fixes.map((fix, idx) => (
                      <li key={idx} style={{ marginBottom: '0.25rem' }}>{fix}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Backward Compatible Alternatives */}
              {explanationData.backward_compatible_alternatives.length > 0 && (
                <div>
                  <strong style={{ fontSize: '0.825rem', color: 'var(--accent-warning)' }}>Backward-Compatible Alternatives:</strong>
                  <ul style={{ paddingLeft: '1.2rem', margin: '0.3rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                    {explanationData.backward_compatible_alternatives.map((alt, idx) => (
                      <li key={idx} style={{ marginBottom: '0.25rem' }}>{alt}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
