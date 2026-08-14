import React, { useState, useRef } from 'react';
import { UploadCloud, FileArchive, CheckCircle2, AlertCircle, Loader2, Cpu, Github, ArrowRight } from 'lucide-react';
import { uploadProjectZip, uploadGithubRepo, getProjectStatus, getProjectInfo, formatApiError } from '../services/api';

export default function ZipUploadCard({ onUploadSuccess }) {
  const [activeTab, setActiveTab] = useState('zip'); // 'zip' | 'github'
  const [githubUrl, setGithubUrl] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle'); // idle | uploading | processing | success | error
  const [stageMessage, setStageMessage] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (selectedFile) => {
    if (!selectedFile) return;
    
    if (!selectedFile.name.toLowerCase().endsWith('.zip')) {
      setErrorMsg('Please select a valid .zip codebase archive.');
      setStatus('error');
      return;
    }

    setFile(selectedFile);
    setErrorMsg('');
    startUpload(selectedFile);
  };

  const pollProcessingStatus = async (projectId) => {
    setStatus('processing');

    const checkStatus = async () => {
      try {
        const statusData = await getProjectStatus(projectId);
        setProgress(statusData.progress || 20);
        setStageMessage(statusData.message || 'Processing codebase...');

        if (statusData.status === 'completed') {
          // Fetch final processed metadata
          const metadata = await getProjectInfo(projectId);
          setStatus('success');
          if (onUploadSuccess) {
            onUploadSuccess(metadata);
          }
        } else if (statusData.status === 'failed') {
          setErrorMsg(statusData.error || statusData.message || 'Processing failed.');
          setStatus('error');
        } else {
          // Continue polling after 800ms
          setTimeout(checkStatus, 800);
        }
      } catch (err) {
        console.error('Status check error:', err);
        setErrorMsg(formatApiError(err, 'Failed to check project processing status.'));
        setStatus('error');
      }
    };

    checkStatus();
  };

  const startUpload = async (fileToUpload) => {
    setStatus('uploading');
    setProgress(0);
    setStageMessage('Uploading zip archive...');

    try {
      const data = await uploadProjectZip(fileToUpload, (percent) => {
        setProgress(Math.min(percent, 90));
      });

      if (data.project_id) {
        pollProcessingStatus(data.project_id);
      } else {
        throw new Error('Upload response missing project ID');
      }
    } catch (err) {
      console.error('Upload Error:', err);
      setErrorMsg(formatApiError(err, 'Failed to upload zip file.'));
      setStatus('error');
    }
  };

  const handleGithubSubmit = async (e) => {
    e.preventDefault();
    if (!githubUrl.trim()) {
      setErrorMsg('Please enter a GitHub repository URL.');
      setStatus('error');
      return;
    }
    if (status === 'uploading' || status === 'processing') return;

    setStatus('uploading');
    setProgress(15);
    setErrorMsg('');
    setStageMessage('Fetching repository ZIP archive from GitHub...');

    try {
      const data = await uploadGithubRepo(githubUrl.trim());
      if (data.project_id) {
        pollProcessingStatus(data.project_id);
      } else {
        throw new Error('GitHub upload response missing project ID');
      }
    } catch (err) {
      console.error('GitHub Upload Error:', err);
      setErrorMsg(formatApiError(err, 'GitHub repository URL could not be processed. Please check the repository URL.'));
      setStatus('error');
    }
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
          onClick={() => status === 'idle' || status === 'error' ? fileInputRef.current?.click() : null}
          style={{
            border: `2px dashed ${isDragging ? 'var(--accent-primary)' : 'var(--border-color)'}`,
            borderRadius: 'var(--radius-lg)',
            padding: '3rem 2rem',
            textAlign: 'center',
            background: isDragging ? 'rgba(244, 63, 94, 0.04)' : 'var(--bg-primary)',
            cursor: status === 'processing' || status === 'uploading' ? 'default' : 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            accept=".zip"
            style={{ display: 'none' }}
            onChange={(e) => handleFileChange(e.target.files[0])}
            disabled={status === 'uploading' || status === 'processing'}
          />

          <UploadCloud size={48} style={{ color: isDragging ? 'var(--accent-primary)' : 'var(--accent-primary)', marginBottom: '0.85rem', opacity: 0.85 }} />
          
          <p style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
            Drop a ZIP archive here or <span style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}>browse</span>
          </p>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Supports Python (.py), JavaScript (.js, .jsx) and TypeScript (.ts, .tsx) codebases up to 350,000 LOC
          </p>
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
                disabled={status === 'uploading' || status === 'processing'}
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
                disabled={!githubUrl.trim() || status === 'uploading' || status === 'processing'}
                className="btn-refresh"
                style={{
                  padding: '0.75rem 1.5rem',
                  fontSize: '0.875rem',
                  opacity: !githubUrl.trim() || status === 'uploading' || status === 'processing' ? 0.6 : 1
                }}
              >
                {status === 'uploading' || status === 'processing' ? (
                  <>
                    <Loader2 size={16} className="spin" /> Fetching...
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

      {/* Upload & Async Processing Progress State */}
      {(status === 'uploading' || status === 'processing') && (
        <div style={{ marginTop: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}>
              {status === 'uploading' ? <Loader2 size={16} className="spin" /> : <Cpu size={16} style={{ color: 'var(--accent-secondary)' }} />}
              {stageMessage || `Processing ${file?.name || 'repository'}...`}
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-primary)' }}>{progress}%</span>
          </div>
          <div style={{ width: '100%', height: '8px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${progress}%`, height: '100%', background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))', transition: 'width 0.3s ease' }} />
          </div>
        </div>
      )}

      {/* Error State */}
      {status === 'error' && (
        <div style={{ marginTop: '1.25rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.85rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <AlertCircle size={18} style={{ color: 'var(--accent-error)', flexShrink: 0 }} />
          <span style={{ fontSize: '0.875rem', color: 'var(--accent-error)' }}>{errorMsg}</span>
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
