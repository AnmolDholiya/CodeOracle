import React, { useState } from 'react';
import { FileText, Trash2, Folder, Code, Layers, AlertCircle, CheckCircle2 } from 'lucide-react';
import { deleteProject } from '../services/api';

export default function ProjectMetadataCard({ metadata, onCleanup }) {
  const [cleaning, setCleaning] = useState(false);
  const [cleanupStatus, setCleanupStatus] = useState(null);

  const handleCleanup = async () => {
    if (!metadata?.project_id) return;
    setCleaning(true);
    try {
      await deleteProject(metadata.project_id);
      setCleanupStatus('Workspace files purged successfully');
      setTimeout(() => {
        if (onCleanup) onCleanup();
      }, 1000);
    } catch (err) {
      console.error('Cleanup error:', err);
      setCleanupStatus('Failed to delete workspace files');
    } finally {
      setCleaning(false);
    }
  };

  if (!metadata) return null;

  return (
    <div className="status-card" style={{ marginBottom: '2rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1.25rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Folder size={22} style={{ color: 'var(--accent-primary)' }} />
            <h3 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-primary)' }}>{metadata.original_filename}</h3>
            <span className="badge-ps">ID: {metadata.project_id}</span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
            Extracted workspace: <code style={{ color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>{metadata.extracted_path}</code>
          </p>
        </div>

        <button 
          className="btn-refresh" 
          onClick={handleCleanup}
          disabled={cleaning}
          style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--accent-error)', border: '1px solid rgba(239, 68, 68, 0.25)', boxShadow: 'none' }}
        >
          <Trash2 size={16} />
          {cleaning ? 'Purging Temp Files...' : 'Cleanup Workspace'}
        </button>
      </div>

      {cleanupStatus && (
        <div style={{ marginBottom: '1.25rem', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-success)', fontSize: '0.875rem', fontWeight: 600 }}>
          {cleanupStatus}
        </div>
      )}

      {/* Metrics Summary Grid */}
      <div className="grid-details" style={{ marginBottom: '2rem' }}>
        <div className="detail-item">
          <div className="detail-label">Total Source Files</div>
          <div className="detail-value" style={{ color: 'var(--accent-primary)', fontSize: '1.5rem' }}>{metadata.total_files}</div>
        </div>

        <div className="detail-item">
          <div className="detail-label">Total Lines of Code (LOC)</div>
          <div className="detail-value" style={{ color: 'var(--accent-secondary)', fontSize: '1.5rem' }}>{metadata.total_lines_of_code}</div>
        </div>

        <div className="detail-item" style={{ gridColumn: 'span 2' }}>
          <div className="detail-label">Detected Languages</div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.4rem' }}>
            {metadata.languages && metadata.languages.length > 0 ? (
              metadata.languages.map((lang, idx) => (
                <span key={idx} style={{ padding: '0.3rem 0.75rem', borderRadius: '9999px', background: 'rgba(244, 63, 94, 0.08)', color: 'var(--accent-primary)', fontSize: '0.8rem', fontWeight: 700, border: '1px solid rgba(244, 63, 94, 0.2)' }}>
                  {lang}
                </span>
              ))
            ) : (
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No source languages detected</span>
            )}
          </div>
        </div>
      </div>

      {/* Scanned Files List Table */}
      <div>
        <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileText size={16} style={{ color: 'var(--text-secondary)' }} />
          <span>Extracted Project Source Files ({metadata.files?.length || 0})</span>
        </h4>

        <div style={{ maxHeight: '250px', overflowY: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', background: '#ffffff' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.65rem 1rem', fontWeight: 700 }}>Relative File Path</th>
                <th style={{ padding: '0.65rem 1rem', fontWeight: 700 }}>Language</th>
                <th style={{ padding: '0.65rem 1rem', fontWeight: 700 }}>Lines of Code</th>
                <th style={{ padding: '0.65rem 1rem', fontWeight: 700 }}>File Size</th>
              </tr>
            </thead>
            <tbody>
              {metadata.files && metadata.files.length > 0 ? (
                metadata.files.map((file, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '0.65rem 1rem', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                      {file.relative_path}
                    </td>
                    <td style={{ padding: '0.65rem 1rem', color: 'var(--text-secondary)' }}>
                      {file.language}
                    </td>
                    <td style={{ padding: '0.65rem 1rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-secondary)' }}>
                      {file.lines_of_code} LOC
                    </td>
                    <td style={{ padding: '0.65rem 1rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {(file.size_bytes / 1024).toFixed(1)} KB
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No source files found in archive.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
