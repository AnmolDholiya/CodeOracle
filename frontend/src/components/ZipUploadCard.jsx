import React, { useState, useRef } from 'react';
import { UploadCloud, FileArchive, CheckCircle2, AlertCircle, Loader2, Cpu, Github, ArrowRight, Server, FileCode, GitBranch } from 'lucide-react';
import { uploadProjectZip, uploadGithubRepo, getProjectStatus, getProjectInfo, formatApiError, wakeUpBackend } from '../services/api';

// Stage labels for UX progress display
const STAGE_LABELS = {
  queued: 'Queued for processing…',
  extracting: 'Extracting files safely…',
  discovering_files: 'Discovering files & calculating line counts…',
  analyzing_python: 'Analyzing Python AST symbols…',
  analyzing_javascript: 'Analyzing JavaScript/TypeScript…',
  building_dependencies: 'Building dependency graph…',
  completed: 'Complete ✓',
  failed: 'Processing failed.',
};

export default function ZipUploadCard({ onUploadSuccess }) {
  const [activeTab, setActiveTab] = useState('zip'); // 'zip' | 'github'
  const [githubUrl, setGithubUrl] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle'); // idle | waking | uploading | processing | success | error
  const [stageMessage, setStageMessage] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef(null);

  // ─── Cold-Start Wake-Up ───────────────────────────────────────────

  const wakeAndProceed = async (proceedFn) => {
    setStatus('waking');
    setProgress(0);
    setErrorMsg('');
    setStageMessage('Starting backend server…');

    try {
      await wakeUpBackend((stage, attempt, maxAttempts) => {
        if (stage === 'connecting') {
          setStageMessage('Connecting to CodeOracle backend…');
          setProgress(5);
        } else if (stage === 'waking' || stage === 'retrying') {
          setStageMessage(`Backend is waking up… (attempt ${attempt}/${maxAttempts})`);
          setProgress(Math.min(10 + attempt * 8, 40));
        } else if (stage === 'ready') {
          setStageMessage('Backend ready.');
          setProgress(45);
        }
      });

      // Backend is alive — proceed with the actual upload
      await proceedFn();
    } catch (err) {
      if (err.message === 'BACKEND_WAKE_FAILED') {
        setErrorMsg('CodeOracle backend is temporarily unavailable. Please try again in a moment.');
      } else {
        const { message } = formatApiError(err, 'Failed to connect to backend.');
        setErrorMsg(message);
      }
      setStatus('error');
    }
  };

  // ─── File Selection ───────────────────────────────────────────────

  const handleFileChange = (selectedFile) => {
    if (!selectedFile) return;

    if (!selectedFile.name.toLowerCase().endsWith('.zip')) {
      setErrorMsg('Please select a valid .zip codebase archive.');
      setStatus('error');
      return;
    }

    setFile(selectedFile);
    setErrorMsg('');

    // Wake backend first, then upload
    wakeAndProceed(() => startUpload(selectedFile));
  };

  // ─── Status Polling (progressive backoff: 1s → 2s → 3s → 5s) ─────

  const pollProcessingStatus = async (projectId) => {
    setStatus('processing');
    let pollCount = 0;

    const getDelay = (count) => {
      if (count === 0) return 600;
      if (count === 1) return 1200;
      if (count === 2) return 2000;
      return 3000; // all subsequent polls
    };

    const MAX_POLLS = 150; // safety cap: ~10 minutes max

    const checkStatus = async () => {
      try {
        const statusData = await getProjectStatus(projectId);
        const stageLabel = STAGE_LABELS[statusData.stage] || statusData.message || 'Processing codebase…';
        setProgress(statusData.progress || 20);
        setStageMessage(stageLabel);

        if (statusData.status === 'completed') {
          // Fetch final processed metadata
          const metadata = await getProjectInfo(projectId);
          setStatus('success');
          setProgress(100);
          setStageMessage('Complete ✓');
          if (onUploadSuccess) {
            onUploadSuccess(metadata);
          }
        } else if (statusData.status === 'failed') {
          setErrorMsg(statusData.error || statusData.message || 'Processing failed.');
          setStatus('error');
        } else if (pollCount >= MAX_POLLS) {
          setErrorMsg('Processing is taking longer than expected. Please check back later.');
          setStatus('error');
        } else {
          pollCount++;
          setTimeout(checkStatus, getDelay(pollCount));
        }
      } catch (err) {
        console.error('Status check error:', err);
        const { message } = formatApiError(err, 'Failed to check project processing status.');
        setErrorMsg(message);
        setStatus('error');
      }
    };

    checkStatus();
  };

  // ─── ZIP Upload ───────────────────────────────────────────────────

  const startUpload = async (fileToUpload) => {
    setStatus('uploading');
    setProgress(0);
    setStageMessage('Uploading ZIP… 0%');

    try {
      const data = await uploadProjectZip(fileToUpload, (percent) => {
        setProgress(percent);
        setStageMessage(`Uploading ZIP… ${percent}%`);
      });

      if (data.project_id) {
        setProgress(100);
        setStageMessage('Upload complete ✓');
        // Brief pause for visual confirmation then poll
        setTimeout(() => {
          pollProcessingStatus(data.project_id);
        }, 350);
      } else {
        throw new Error('Upload response missing project ID');
      }
    } catch (err) {
      console.error('Upload Error:', err);
      const { message } = formatApiError(err, 'Failed to upload zip file.');
      setErrorMsg(message);
      setStatus('error');
    }
  };

  // ─── GitHub Upload ────────────────────────────────────────────────

  const handleGithubSubmit = async (e) => {
    e.preventDefault();
    if (!githubUrl.trim()) {
      setErrorMsg('Please enter a GitHub repository URL.');
      setStatus('error');
      return;
    }
    if (status === 'waking' || status === 'uploading' || status === 'processing') return;

    // Wake backend first, then submit GitHub URL
    wakeAndProceed(async () => {
      setStatus('uploading');
      setProgress(15);
      setErrorMsg('');
      setStageMessage('Fetching repository archive from GitHub…');

      try {
        const data = await uploadGithubRepo(githubUrl.trim());
        if (data.project_id) {
          setStageMessage('Repository queued. Analysis started.');
          pollProcessingStatus(data.project_id);
        } else {
          throw new Error('GitHub upload response missing project ID');
        }
      } catch (err) {
        console.error('GitHub Upload Error:', err);
        const { message } = formatApiError(err, 'GitHub repository URL could not be processed. Please check the repository URL.');
        setErrorMsg(message);
        setStatus('error');
      }
    });
  };

  // ─── Drag & Drop ──────────────────────────────────────────────────

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  // ─── Reset / Retry ────────────────────────────────────────────────

  const handleReset = () => {
    setStatus('idle');
    setProgress(0);
    setStageMessage('');
    setErrorMsg('');
  };

  const handleRetryWithFile = () => {
    if (file) {
      setErrorMsg('');
      wakeAndProceed(() => startUpload(file));
    } else {
      handleReset();
    }
  };

  const isBlocked = status === 'waking' || status === 'uploading' || status === 'processing';

  // ─── Wake-Up / Progress Stage Icon ────────────────────────────────

  const getStatusIcon = () => {
    if (status === 'waking') return <Server size={16} className="spin" style={{ color: 'var(--accent-secondary)' }} />;
    if (status === 'uploading') return <Loader2 size={16} className="spin" style={{ color: 'var(--accent-primary)' }} />;
    if (status === 'processing') return <Cpu size={16} style={{ color: 'var(--accent-secondary)' }} />;
    if (status === 'success') return <CheckCircle2 size={16} style={{ color: 'var(--accent-success)' }} />;
    return null;
  };

  return (
    <div className="status-card" style={{ marginBottom: '2rem' }}>
      {/* Tab Selectors */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.85rem' }}>
        <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <UploadCloud size={20} style={{ color: 'var(--accent-primary)' }} />
          <span>Analyze Legacy Codebase</span>
        </h3>

        <div style={{ display: 'flex', gap: '0.35rem', background: 'var(--bg-secondary)', padding: '0.25rem', borderRadius: '9999px', border: '1px solid var(--border-color)' }}>
          <button
            type="button"
            onClick={() => setActiveTab('zip')}
            style={{
              padding: '0.4rem 1rem',
              borderRadius: '9999px',
              border: 'none',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
              background: activeTab === 'zip' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'zip' ? '#fff' : 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              transition: 'all 0.2s ease',
              boxShadow: activeTab === 'zip' ? '0 2px 8px rgba(244, 63, 94, 0.25)' : 'none'
            }}
          >
            <UploadCloud size={14} /> ZIP Archive
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('github')}
            style={{
              padding: '0.4rem 1rem',
              borderRadius: '9999px',
              border: 'none',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
              background: activeTab === 'github' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'github' ? '#fff' : 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              transition: 'all 0.2s ease',
              boxShadow: activeTab === 'github' ? '0 2px 8px rgba(244, 63, 94, 0.25)' : 'none'
            }}
          >
            <Github size={14} /> GitHub Repository URL
          </button>
        </div>
      </div>

      {/* ZIP Upload Tab Content */}
      {activeTab === 'zip' ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isBlocked && (status === 'idle' || status === 'error') ? fileInputRef.current?.click() : null}
          style={{
            border: `2px dashed ${isDragging ? 'var(--accent-primary)' : 'var(--border-color)'}`,
            borderRadius: 'var(--radius-lg)',
            padding: '3rem 2rem',
            textAlign: 'center',
            background: isDragging ? 'rgba(244, 63, 94, 0.04)' : 'var(--bg-primary)',
            cursor: isBlocked ? 'default' : 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            accept=".zip"
            style={{ display: 'none' }}
            onChange={(e) => handleFileChange(e.target.files[0])}
            disabled={isBlocked}
          />

          <UploadCloud size={48} style={{ color: 'var(--accent-primary)', marginBottom: '0.85rem', opacity: 0.85 }} />

          {file && (status === 'error' || status === 'idle') ? (
            <>
              <p style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-primary)', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                <FileArchive size={18} style={{ color: 'var(--accent-secondary)' }} />
                {file.name}
              </p>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                {file.size >= 1024 * 1024 ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : `${(file.size / 1024).toFixed(1)} KB`} — Click to select a different file, or{' '}
                <span
                  onClick={(e) => { e.stopPropagation(); handleRetryWithFile(); }}
                  style={{ color: 'var(--accent-primary)', textDecoration: 'underline', cursor: 'pointer', fontWeight: 600 }}
                >
                  retry upload
                </span>
              </p>
            </>
          ) : (
            <>
              <p style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                Drop a ZIP archive here or <span style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}>browse</span>
              </p>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Supports Python (.py), JavaScript (.js, .jsx) and TypeScript (.ts, .tsx) codebases up to 350,000 LOC
              </p>
            </>
          )}
        </div>
      ) : (
        /* GitHub Repository Input Tab Content */
        <form onSubmit={handleGithubSubmit} style={{ background: 'var(--bg-primary)', padding: '2rem', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block', marginBottom: '0.6rem' }}>
              Public GitHub Repository URL:
            </label>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <input
                type="url"
                placeholder="https://github.com/owner/repository"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                disabled={isBlocked}
                style={{
                  flex: 1,
                  padding: '0.75rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background: '#ffffff',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.9rem',
                  fontFamily: 'var(--font-mono)',
                  boxShadow: 'var(--shadow-sm)'
                }}
              />
              <button
                type="submit"
                disabled={!githubUrl.trim() || isBlocked}
                className="btn-refresh"
                style={{
                  padding: '0.75rem 1.5rem',
                  fontSize: '0.875rem',
                  opacity: !githubUrl.trim() || isBlocked ? 0.6 : 1
                }}
              >
                {isBlocked ? (
                  <>
                    <Loader2 size={16} className="spin" /> {status === 'waking' ? 'Connecting…' : 'Fetching…'}
                  </>
                ) : (
                  <>
                    <ArrowRight size={16} /> Analyze Repository
                  </>
                )}
              </button>
            </div>
          </div>

          <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Github size={14} /> Downloads public repository archive directly into local AST indexer pipeline.
          </p>
        </form>
      )}

      {/* Wake-Up / Upload / Processing Progress */}
      {(status === 'waking' || status === 'uploading' || status === 'processing') && (
        <div style={{ marginTop: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}>
              {getStatusIcon()}
              {stageMessage || `Processing ${file?.name || 'repository'}…`}
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-primary)' }}>{progress}%</span>
          </div>
          <div style={{ width: '100%', height: '8px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{
              width: `${progress}%`,
              height: '100%',
              background: status === 'waking'
                ? 'linear-gradient(90deg, var(--accent-secondary), var(--accent-warning))'
                : 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </div>
      )}

      {/* Error State */}
      {status === 'error' && (
        <div style={{ marginTop: '1.25rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.85rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <AlertCircle size={18} style={{ color: 'var(--accent-error)', flexShrink: 0 }} />
          <span style={{ fontSize: '0.875rem', color: 'var(--accent-error)', flex: 1 }}>{errorMsg}</span>
          {file && (
            <button
              onClick={handleRetryWithFile}
              style={{
                background: 'none',
                border: '1px solid var(--accent-error)',
                color: 'var(--accent-error)',
                padding: '0.35rem 0.85rem',
                borderRadius: '9999px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                flexShrink: 0,
                transition: 'all 0.2s ease'
              }}
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Success Notification */}
      {status === 'success' && (
        <div style={{ marginTop: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-success)', fontWeight: 600 }}>
          <CheckCircle2 size={18} />
          <span>Codebase Metadata & AST Graph Generated Successfully!</span>
        </div>
      )}
    </div>
  );
}
