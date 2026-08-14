import React, { useState, useEffect } from 'react';
import { 
  FlaskConical, 
  Play, 
  Code, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Clock, 
  Loader2, 
  FileCode, 
  Check, 
  Percent, 
  CheckSquare, 
  ShieldCheck, 
  Terminal,
  RefreshCw,
  Info,
  Sparkles
} from 'lucide-react';
import api, { formatApiError } from '../services/api';

export default function UnitTestCard({ projectId, projectFiles = [] }) {
  const testableFiles = projectFiles.filter(f => f.relative_path.toLowerCase().match(/\.(py|js|jsx|ts|tsx)$/));
  const [selectedFile, setSelectedFile] = useState(testableFiles[0]?.relative_path || '');
  const [functionName, setFunctionName] = useState('');

  useEffect(() => {
    if (testableFiles.length > 0 && (!selectedFile || !testableFiles.some(f => f.relative_path === selectedFile))) {
      setSelectedFile(testableFiles[0].relative_path);
    }
  }, [projectFiles]);
  
  const [testGenData, setTestGenData] = useState(null);
  const [execResult, setExecResult] = useState(null);
  const [coverageData, setCoverageData] = useState(null);

  const [generating, setGenerating] = useState(false);
  const [running, setRunning] = useState(false);

  const [genError, setGenError] = useState(null);
  const [runError, setRunError] = useState(null);
  const [showLogs, setShowLogs] = useState(false);

  // Generate Unit Tests
  const handleGenerateTests = async (forceRefresh = false) => {
    if (!selectedFile || generating) return;
    setGenerating(true);
    setGenError(null);

    try {
      const res = await api.post(`/api/projects/${projectId}/tests/generate`, {
        file_path: selectedFile,
        function_name: functionName || null,
        force_refresh: forceRefresh
      });
      setTestGenData(res.data);
    } catch (err) {
      console.error('Test generation error:', err);
      setGenError(formatApiError(err, 'Test generation failed.'));
    } finally {
      setGenerating(false);
    }
  };

  // Run Tests & Calculate Coverage
  const handleRunTests = async () => {
    if (!selectedFile || running) return;
    setRunning(true);
    setRunError(null);

    try {
      // 1. Run Pytest execution
      const execRes = await api.post(`/api/projects/${projectId}/tests/run`, {
        file_path: selectedFile,
        timeout_seconds: 30
      });
      setExecResult(execRes.data);

      // 2. Calculate Actual Coverage via coverage.py
      try {
        const covRes = await api.get(`/api/projects/${projectId}/tests/coverage?file_path=${encodeURIComponent(selectedFile)}`);
        setCoverageData(covRes.data);
      } catch (covErr) {
        console.error('Coverage calculation notice:', covErr);
      }
    } catch (err) {
      console.error('Test execution error:', err);
      setRunError(formatApiError(err, 'Test execution failed.'));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="status-card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
      {/* Section Title Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <FlaskConical size={22} style={{ color: 'var(--accent-primary)' }} />
            <span>Automated Unit Test & Coverage Engine</span>
          </h2>
        </div>
        {(testGenData || execResult || coverageData) && (
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', padding: '0.25rem 0.65rem', borderRadius: '9999px', background: 'rgba(96, 165, 250, 0.1)', color: '#3b82f6', border: '1px solid rgba(96, 165, 250, 0.3)', fontWeight: 700, textTransform: 'capitalize' }}>
              Language: {testGenData?.language || execResult?.language || coverageData?.language || 'python'}
            </span>
            <span style={{ fontSize: '0.75rem', padding: '0.25rem 0.65rem', borderRadius: '9999px', background: 'rgba(168, 85, 247, 0.1)', color: '#a855f7', border: '1px solid rgba(168, 85, 247, 0.3)', fontWeight: 700, textTransform: 'capitalize' }}>
              Runner: {testGenData?.framework || execResult?.framework || coverageData?.framework || 'pytest'}
            </span>
          </div>
        )}
      </div>

      {/* Target Selector & Actions */}
      <div style={{ background: 'var(--bg-secondary)', padding: '1.25rem 1.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', alignItems: 'end' }}>
          {/* File Picker */}
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.45rem', display: 'block' }}>
              Target Source File (Python / JS / TS)
            </label>
            <select
              value={selectedFile}
              disabled={testableFiles.length === 0}
              onChange={(e) => {
                setSelectedFile(e.target.value);
                setTestGenData(null);
                setExecResult(null);
                setCoverageData(null);
              }}
              style={{
                width: '100%',
                padding: '0.65rem 0.9rem',
                borderRadius: 'var(--radius-md)',
                background: testableFiles.length === 0 ? 'var(--bg-tertiary)' : '#ffffff',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                fontSize: '0.875rem',
                fontFamily: 'var(--font-mono)',
                boxShadow: 'var(--shadow-sm)'
              }}
            >
              {testableFiles.length === 0 ? (
                <option value="" disabled>No testable files (.py, .js, .ts, .jsx, .tsx) found in project</option>
              ) : (
                testableFiles.map((f) => (
                  <option key={f.relative_path} value={f.relative_path}>
                    {f.relative_path} ({f.lines_of_code || 0} LOC)
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Optional Function Target */}
          <div>
            <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.45rem', display: 'block' }}>
              Optional Target Function
            </label>
            <input
              type="text"
              placeholder="e.g. main, process_data (Optional)"
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

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              disabled={generating || !selectedFile}
              onClick={() => handleGenerateTests(true)}
              className="btn-refresh"
              style={{
                flex: 1,
                justifyContent: 'center',
                opacity: generating ? 0.6 : 1
              }}
            >
              {generating ? (
                <>
                  <Loader2 size={16} className="spin" /> Generating...
                </>
              ) : (
                <>
                  <Sparkles size={16} /> Generate Unit Tests
                </>
              )}
            </button>

            {testGenData && (
              <button
                disabled={running}
                onClick={handleRunTests}
                className="btn-refresh"
                style={{
                  background: 'var(--text-primary)',
                  flex: 1,
                  justifyContent: 'center',
                  opacity: running ? 0.6 : 1
                }}
              >
                {running ? (
                  <>
                    <Loader2 size={16} className="spin" /> Running pytest...
                  </>
                ) : (
                  <>
                    <Play size={16} /> Run Tests & Coverage
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {genError && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', color: 'var(--accent-error)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertTriangle size={18} />
          <span>{genError}</span>
        </div>
      )}

      {/* Generated Test Code Display */}
      {testGenData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '1.5rem' }}>
          <div style={{ background: '#ffffff', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-success)' }}>
                <FileCode size={16} />
                <span>{testGenData.test_file_path}</span>
              </div>
              {testGenData.is_cached && (
                <span style={{ fontSize: '0.75rem', padding: '0.15rem 0.55rem', borderRadius: '9999px', background: 'rgba(244, 63, 94, 0.08)', color: 'var(--accent-primary)', fontWeight: 700, border: '1px solid rgba(244, 63, 94, 0.2)' }}>
                  CACHED
                </span>
              )}
            </div>

            <pre style={{ padding: '1rem', margin: 0, fontSize: '0.825rem', color: '#f8fafc', fontFamily: 'var(--font-mono)', overflowX: 'auto', maxHeight: '280px', lineHeight: '1.45', background: '#0f172a' }}>
              {testGenData.test_code}
            </pre>
          </div>
        </div>
      )}

      {/* Execution Results & Coverage Dashboard */}
      {execResult && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.25rem' }}>
          {/* Pytest Execution Stats Card */}
          <div style={{ background: 'var(--bg-secondary)', padding: '1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckSquare size={18} style={{ color: 'var(--accent-primary)' }} />
                <span>Pytest Execution Results</span>
              </div>
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '0.2rem 0.6rem',
                borderRadius: '9999px',
                background: execResult.status === 'passed' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                color: execResult.status === 'passed' ? 'var(--accent-success)' : 'var(--accent-error)',
                border: execResult.status === 'passed' ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(239, 68, 68, 0.25)'
              }}>
                {execResult.status.toUpperCase()}
              </span>
            </h4>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem', textAlign: 'center', marginBottom: '1rem' }}>
              <div style={{ background: '#ffffff', padding: '0.6rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>TOTAL</span>
                <strong style={{ fontSize: '1.1rem', color: 'var(--text-primary)' }}>{execResult.total}</strong>
              </div>
              <div style={{ background: 'rgba(16, 185, 129, 0.08)', padding: '0.6rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--accent-success)', display: 'block', fontWeight: 600 }}>PASSED</span>
                <strong style={{ fontSize: '1.1rem', color: 'var(--accent-success)' }}>{execResult.passed}</strong>
              </div>
              <div style={{ background: 'rgba(239, 68, 68, 0.08)', padding: '0.6rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--accent-error)', display: 'block', fontWeight: 600 }}>FAILED</span>
                <strong style={{ fontSize: '1.1rem', color: 'var(--accent-error)' }}>{execResult.failed}</strong>
              </div>
              <div style={{ background: 'rgba(245, 158, 11, 0.08)', padding: '0.6rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--accent-warning)', display: 'block', fontWeight: 600 }}>SKIPPED</span>
                <strong style={{ fontSize: '1.1rem', color: 'var(--accent-warning)' }}>{execResult.skipped}</strong>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span>Duration: <strong>{execResult.duration_seconds}s</strong></span>
              {(execResult.stdout || execResult.stderr) && (
                <button
                  onClick={() => setShowLogs(!showLogs)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--accent-primary)', fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.3rem', fontWeight: 600 }}
                >
                  <Terminal size={14} /> {showLogs ? "Hide Logs" : "View Test Logs"}
                </button>
              )}
            </div>

            {showLogs && (
              <pre style={{ marginTop: '0.75rem', padding: '0.75rem', background: '#0f172a', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem', color: '#f8fafc', fontFamily: 'var(--font-mono)', maxHeight: '180px', overflowY: 'auto' }}>
                {execResult.stdout || execResult.stderr}
              </pre>
            )}
          </div>

          {/* Actual Code Coverage Card */}
          {coverageData && (
            <div style={{ background: 'var(--bg-secondary)', padding: '1.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={18} style={{ color: 'var(--accent-success)' }} />
                <span>Actual Code Coverage (coverage.py)</span>
              </h4>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', marginBottom: '1rem' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: coverageData.overall_coverage >= 70 ? 'var(--accent-success)' : 'var(--accent-warning)', fontFamily: 'var(--font-mono)' }}>
                  {coverageData.overall_coverage}%
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ height: '8px', width: '100%', background: 'rgba(0,0,0,0.06)', borderRadius: '4px', overflow: 'hidden', marginBottom: '0.4rem' }}>
                    <div style={{ height: '100%', width: `${Math.min(100, coverageData.overall_coverage)}%`, background: coverageData.overall_coverage >= 70 ? 'var(--accent-success)' : 'var(--accent-warning)', borderRadius: '4px', transition: 'width 0.5s ease' }} />
                  </div>
                  <span style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                    Statements: {coverageData.total_statements} | Missed: {coverageData.total_missed}
                  </span>
                </div>
              </div>

              {/* File Breakdown List */}
              {coverageData.files.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {coverageData.files.map((fileCov) => (
                    <div key={fileCov.file_path} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.45rem 0.75rem', background: '#ffffff', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', border: '1px solid var(--border-color)' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{fileCov.file_path}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                        <span style={{ fontWeight: 700, color: fileCov.coverage_percentage >= 70 ? 'var(--accent-success)' : 'var(--accent-warning)' }}>
                          {fileCov.coverage_percentage}%
                        </span>
                        {fileCov.missing_lines.length > 0 && (
                          <span style={{ fontSize: '0.725rem', color: 'var(--accent-warning)' }}>
                            Missed: {fileCov.missing_lines.join(', ')}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
