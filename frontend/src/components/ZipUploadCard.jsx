import React, { useState, useRef } from 'react';
import { UploadCloud, FileArchive, CheckCircle2, AlertCircle, Loader2, Cpu, Github, ArrowRight, Server, Sparkles, Zap, PackageOpen } from 'lucide-react';
import { uploadProjectZip, uploadGithubRepo, getProjectStatus, getProjectInfo, formatApiError, wakeUpBackend } from '../services/api';

// Stage labels for UX progress display
const STAGE_LABELS = {
  queued: '🚀 Queued for processing…',
  extracting: '📦 Unpacking & filtering files…',
  discovering_files: '🔍 Scanning codebase files…',
  analyzing_python: '🐍 Parsing Python AST symbols…',
  analyzing_javascript: '⚡ Indexing JavaScript/TypeScript…',
  building_dependencies: '🕸️ Connecting dependency graph…',
  completed: '🎉 Mission Complete! Codebase ready.',
  failed: '💥 Oops! Processing failed.',
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
    setStageMessage('⚡ Waking up backend engine…');

    try {
      await wakeUpBackend((stage, attempt, maxAttempts) => {
        if (stage === 'connecting') {
          setStageMessage('📡 Connecting to CodeOracle backend…');
          setProgress(5);
        } else if (stage === 'waking' || stage === 'retrying') {
          setStageMessage(`☕ Backend is brewing… (attempt ${attempt}/${maxAttempts})`);
          setProgress(Math.min(10 + attempt * 8, 40));
        } else if (stage === 'ready') {
          setStageMessage('✨ Backend engine is wide awake!');
          setProgress(45);
        }
      });

      await proceedFn();
    } catch (err) {
      if (err.message === 'BACKEND_WAKE_FAILED') {
        setErrorMsg('CodeOracle backend is temporarily sleeping. Give it another poke in a moment!');
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
    wakeAndProceed(() => startUpload(selectedFile));
  };

  // ─── Status Polling ───────────────────────────────────────────────

  const pollProcessingStatus = async (projectId) => {
    setStatus('processing');
    let pollCount = 0;

    const getDelay = (count) => {
      if (count === 0) return 500;
      if (count === 1) return 1000;
      if (count === 2) return 1800;
      return 2500;
    };

    const MAX_POLLS = 150;

    const checkStatus = async () => {
      try {
        const statusData = await getProjectStatus(projectId);
        const stageLabel = STAGE_LABELS[statusData.stage] || statusData.message || '⚡ Crunching code…';
        setProgress(statusData.progress || 20);
        setStageMessage(stageLabel);

        if (statusData.status === 'completed') {
          const metadata = await getProjectInfo(projectId);
          setStatus('success');
          setProgress(100);
          setStageMessage('🎉 Mission Complete! Codebase ready.');
          if (onUploadSuccess) {
            onUploadSuccess(metadata);
          }
        } else if (statusData.status === 'failed') {
          setErrorMsg(statusData.error || statusData.message || 'Processing failed.');
          setStatus('error');
        } else if (pollCount >= MAX_POLLS) {
          setErrorMsg('Processing took a bit too long. Please try again!');
          setStatus('error');
        } else {
          pollCount++;
          setTimeout(checkStatus, getDelay(pollCount));
        }
      } catch (err) {
        console.error('Status check error:', err);
        const { message } = formatApiError(err, 'Failed to check processing status.');
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
    setStageMessage('🚀 Flying ZIP to server… 0%');

    try {
      const data = await uploadProjectZip(fileToUpload, (percent) => {
        setProgress(percent);
        setStageMessage(`🚀 Flying ZIP to server… ${percent}%`);
      });

      if (data.project_id) {
        setProgress(100);
        setStageMessage('📦 ZIP landed safely! Unpacking…');
        setTimeout(() => {
          pollProcessingStatus(data.project_id);
        }, 300);
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
      setErrorMsg('Please enter a valid GitHub repository URL.');
      setStatus('error');
      return;
    }
    if (status === 'waking' || status === 'uploading' || status === 'processing') return;

    wakeAndProceed(async () => {
      setStatus('uploading');
      setProgress(15);
      setErrorMsg('');
      setStageMessage('🐙 Grabbing archive from GitHub…');

      try {
        const data = await uploadGithubRepo(githubUrl.trim());
        if (data.project_id) {
          setStageMessage('🚀 Repository queued! Launching analysis…');
          pollProcessingStatus(data.project_id);
        } else {
          throw new Error('GitHub upload response missing project ID');
        }
      } catch (err) {
        console.error('GitHub Upload Error:', err);
        const { message } = formatApiError(err, 'GitHub repository could not be fetched. Make sure it is public!');
        setErrorMsg(message);
        setStatus('error');
      }
    });
  };

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

  const getStatusIcon = () => {
    if (status === 'waking') return <Server size={18} className="spin" style={{ color: 'var(--accent-secondary)' }} />;
    if (status === 'uploading') return <Loader2 size={18} className="spin" style={{ color: 'var(--accent-primary)' }} />;
    if (status === 'processing') return <Cpu size={18} style={{ color: 'var(--accent-purple)' }} />;
    if (status === 'success') return <CheckCircle2 size={18} style={{ color: 'var(--accent-success)' }} />;
    return null;
  };

  return (
    <div className="status-card" style={{ marginBottom: '2.5rem' }}>
      {/* Decorative cartoon chip in corner */}
      <div style={{
        position: 'absolute',
        top: '12px',
        right: '16px',
        background: 'var(--accent-secondary)',
        color: 'var(--ink)',
        fontSize: '0.72rem',
        fontWeight: 800,
        padding: '0.2rem 0.6rem',
        borderRadius: 'var(--radius-pill)',
        border: '2px solid var(--ink)',
        boxShadow: '2px 2px 0px var(--ink)',
        transform: 'rotate(4deg)',
        pointerEvents: 'none'
      }}>
        ⚡ SUPER FAST
      </div>

      {/* Tab Selectors */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '2.5px solid var(--ink)', paddingBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <PackageOpen size={24} style={{ color: 'var(--accent-primary)', filter: 'drop-shadow(1.5px 1.5px 0px var(--ink))' }} />
          <span>Upload Legacy Codebase</span>
        </h3>

        <div style={{ display: 'flex', gap: '0.5rem', background: 'var(--bg-secondary)', padding: '0.35rem', borderRadius: 'var(--radius-pill)', border: '2px solid var(--ink)', boxShadow: '2px 2px 0px var(--ink)' }}>
          <button
            type="button"
            onClick={() => setActiveTab('zip')}
            style={{
              padding: '0.45rem 1.15rem',
              borderRadius: 'var(--radius-pill)',
              border: activeTab === 'zip' ? '2px solid var(--ink)' : '2px solid transparent',
              fontSize: '0.85rem',
              fontWeight: 700,
              cursor: 'pointer',
              background: activeTab === 'zip' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'zip' ? '#FFF' : 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
              boxShadow: activeTab === 'zip' ? '2px 2px 0px var(--ink)' : 'none',
              transform: activeTab === 'zip' ? 'translate(-1px, -1px)' : 'none'
            }}
          >
            <UploadCloud size={16} /> ZIP Archive
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('github')}
            style={{
              padding: '0.45rem 1.15rem',
              borderRadius: 'var(--radius-pill)',
              border: activeTab === 'github' ? '2px solid var(--ink)' : '2px solid transparent',
              fontSize: '0.85rem',
              fontWeight: 700,
              cursor: 'pointer',
              background: activeTab === 'github' ? 'var(--accent-purple)' : 'transparent',
              color: activeTab === 'github' ? '#FFF' : 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
              boxShadow: activeTab === 'github' ? '2px 2px 0px var(--ink)' : 'none',
              transform: activeTab === 'github' ? 'translate(-1px, -1px)' : 'none'
            }}
          >
            <Github size={16} /> GitHub Repo URL
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
            border: `3px dashed ${isDragging ? 'var(--accent-primary)' : 'var(--ink)'}`,
            borderRadius: 'var(--radius-lg)',
            padding: '3rem 2rem',
            textAlign: 'center',
            background: isDragging ? '#FFF0F6' : 'var(--bg-secondary)',
            cursor: isBlocked ? 'default' : 'pointer',
            transition: 'all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)',
            boxShadow: isDragging ? '6px 6px 0px var(--accent-primary)' : '4px 4px 0px var(--ink)',
            transform: isDragging ? 'scale(1.01)' : 'none'
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

          <div style={{ display: 'inline-block', padding: '1rem', background: '#FFFFFF', borderRadius: '50%', border: '2.5px solid var(--ink)', boxShadow: '3px 3px 0px var(--ink)', marginBottom: '1rem' }}>
            <UploadCloud size={46} style={{ color: 'var(--accent-primary)', display: 'block' }} />
          </div>

          {file && (status === 'error' || status === 'idle') ? (
            <>
              <p style={{ fontWeight: 700, fontSize: '1.2rem', color: 'var(--text-primary)', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                <FileArchive size={20} style={{ color: 'var(--accent-secondary)' }} />
                {file.name}
              </p>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                {file.size >= 1024 * 1024 ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : `${(file.size / 1024).toFixed(1)} KB`} — Click to choose another file, or{' '}
                <span
                  onClick={(e) => { e.stopPropagation(); handleRetryWithFile(); }}
                  style={{ color: 'var(--accent-primary)', textDecoration: 'underline', cursor: 'pointer', fontWeight: 800 }}
                >
                  retry upload 🔄
                </span>
              </p>
            </>
          ) : (
            <>
              <p style={{ fontWeight: 700, fontSize: '1.3rem', color: 'var(--text-primary)', marginBottom: '0.4rem', fontFamily: 'var(--font-heading)' }}>
                Drop your ZIP archive here or <span style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}>browse</span> 📁
              </p>
              <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                Supports Python (.py), JavaScript (.js, .jsx) and TypeScript (.ts, .tsx) up to <strong style={{ color: 'var(--accent-primary)', fontWeight: 800 }}>350,000 LOC</strong>!
              </p>
            </>
          )}
        </div>
      ) : (
        /* GitHub Repository Input Tab Content */
        <form onSubmit={handleGithubSubmit} style={{ background: 'var(--bg-secondary)', padding: '2rem', borderRadius: 'var(--radius-lg)', border: '2.5px solid var(--ink)', boxShadow: '4px 4px 0px var(--ink)' }}>
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block', marginBottom: '0.6rem', fontFamily: 'var(--font-heading)' }}>
              🐙 Public GitHub Repository URL:
            </label>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <input
                type="url"
                placeholder="https://github.com/owner/repository"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                disabled={isBlocked}
                style={{
                  flex: 1,
                  minWidth: '240px',
                  padding: '0.85rem 1.15rem',
                  background: '#FFFFFF',
                  color: 'var(--text-primary)',
                  fontSize: '0.92rem',
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono)'
                }}
              />
              <button
                type="submit"
                disabled={!githubUrl.trim() || isBlocked}
                className="btn-refresh"
                style={{
                  background: 'var(--accent-purple)',
                  padding: '0.85rem 1.6rem',
                  fontSize: '0.92rem',
                  opacity: !githubUrl.trim() || isBlocked ? 0.6 : 1
                }}
              >
                {isBlocked ? (
                  <>
                    <Loader2 size={18} className="spin" /> {status === 'waking' ? 'Connecting…' : 'Fetching…'}
                  </>
                ) : (
                  <>
                    <Zap size={18} /> Analyze Repository
                  </>
                )}
              </button>
            </div>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 500 }}>
            <Github size={15} /> Automatically downloads and feeds public repository archive into the local static AST indexer!
          </p>
        </form>
      )}

      {/* Wake-Up / Upload / Processing Progress */}
      {(status === 'waking' || status === 'uploading' || status === 'processing') && (
        <div style={{ marginTop: '1.5rem', background: '#FFFFFF', padding: '1.25rem', borderRadius: 'var(--radius-md)', border: '2.5px solid var(--ink)', boxShadow: '3px 3px 0px var(--ink)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.92rem', marginBottom: '0.65rem' }}>
            <span style={{ color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
              {getStatusIcon()}
              {stageMessage || `Processing ${file?.name || 'codebase'}…`}
            </span>
            <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, color: 'var(--accent-primary)', fontSize: '1.1rem' }}>{progress}%</span>
          </div>
          
          <div style={{ width: '100%', height: '14px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-pill)', border: '2px solid var(--ink)', overflow: 'hidden', position: 'relative' }}>
            <div style={{
              width: `${progress}%`,
              height: '100%',
              background: status === 'waking'
                ? 'linear-gradient(90deg, var(--accent-secondary), var(--accent-warning))'
                : 'linear-gradient(90deg, var(--accent-primary), var(--accent-purple))',
              transition: 'width 0.25s cubic-bezier(0.34, 1.56, 0.64, 1)'
            }} />
          </div>
        </div>
      )}

      {/* Error State */}
      {status === 'error' && (
        <div style={{ marginTop: '1.5rem', background: '#FFF0F0', border: '2.5px solid var(--accent-error)', padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', boxShadow: '3px 3px 0px var(--accent-error)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <AlertCircle size={22} style={{ color: 'var(--accent-error)', flexShrink: 0 }} />
          <span style={{ fontSize: '0.92rem', color: 'var(--accent-error)', fontWeight: 700, flex: 1 }}>{errorMsg}</span>
          {file && (
            <button
              onClick={handleRetryWithFile}
              className="btn-refresh"
              style={{
                background: 'var(--accent-error)',
                padding: '0.4rem 1rem',
                fontSize: '0.85rem'
              }}
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Success Notification */}
      {status === 'success' && (
        <div style={{ marginTop: '1.5rem', background: '#EBFDF2', border: '2.5px solid var(--accent-success)', padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', boxShadow: '3px 3px 0px var(--accent-success)', display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--ink)', fontWeight: 700 }}>
          <CheckCircle2 size={22} style={{ color: 'var(--accent-success)' }} />
          <span>🎉 Codebase Metadata & AST Dependency Graph Generated Successfully!</span>
        </div>
      )}
    </div>
  );
}
