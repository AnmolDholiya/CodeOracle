import React, { useState } from 'react';
import { FileText, Trash2, Folder, Code, Layers, AlertCircle, CheckCircle2, Sparkles, Hash, Terminal } from 'lucide-react';
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
    <div className="status-card" style={{ marginBottom: '2.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem', borderBottom: '2.5px solid var(--ink)', paddingBottom: '1.25rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <Folder size={24} style={{ color: 'var(--accent-primary)', filter: 'drop-shadow(1.5px 1.5px 0px var(--ink))' }} />
            <h3 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-heading)' }}>
              {metadata.original_filename}
            </h3>
            <span className="badge-ps" style={{ background: 'var(--accent-cyan)' }}>
              <Hash size={13} /> {metadata.project_id}
            </span>
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginTop: '0.4rem', fontWeight: 500 }}>
            Workspace: <code style={{ color: 'var(--ink)', background: 'var(--bg-secondary)', padding: '0.2rem 0.5rem', borderRadius: '6px', border: '1.5px solid var(--ink)', fontFamily: 'var(--font-mono)' }}>{metadata.extracted_path}</code>
          </p>
        </div>

        <button 
          className="btn-refresh" 
          onClick={handleCleanup}
          disabled={cleaning}
          style={{ background: '#FFF0F0', color: 'var(--accent-error)', border: '2px solid var(--accent-error)', boxShadow: '3px 3px 0px var(--accent-error)' }}
        >
          <Trash2 size={16} />
          {cleaning ? 'Purging Files…' : 'Cleanup Workspace'}
        </button>
      </div>

      {cleanupStatus && (
        <div style={{ marginBottom: '1.5rem', padding: '0.85rem 1.25rem', borderRadius: 'var(--radius-md)', background: '#EBFDF2', color: 'var(--accent-success)', fontSize: '0.92rem', fontWeight: 700, border: '2px solid var(--accent-success)', boxShadow: '3px 3px 0px var(--accent-success)' }}>
          ✨ {cleanupStatus}
        </div>
      )}

      {/* Metrics Summary Grid */}
      <div className="grid-details" style={{ marginBottom: '2rem' }}>
        <div className="detail-item" style={{ background: '#FFF0F6' }}>
          <div className="detail-label" style={{ color: 'var(--accent-primary)' }}>📁 Total Source Files</div>
          <div className="detail-value" style={{ color: 'var(--accent-primary)', fontSize: '1.75rem' }}>{metadata.total_files}</div>
        </div>

        <div className="detail-item" style={{ background: '#FFFBF0' }}>
          <div className="detail-label" style={{ color: 'var(--accent-warning)' }}>📊 Lines of Code (LOC)</div>
          <div className="detail-value" style={{ color: 'var(--accent-warning)', fontSize: '1.75rem' }}>{metadata.total_lines_of_code?.toLocaleString()}</div>
        </div>

        <div className="detail-item" style={{ gridColumn: 'span 2', background: '#F5F3FF' }}>
          <div className="detail-label" style={{ color: 'var(--accent-purple)' }}>🎨 Detected Languages</div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.4rem' }}>
            {metadata.languages && metadata.languages.length > 0 ? (
              metadata.languages.map((lang, idx) => (
                <span 
                  key={idx} 
                  style={{ 
                    padding: '0.35rem 0.85rem', 
                    borderRadius: 'var(--radius-pill)', 
                    background: '#FFFFFF', 
                    color: 'var(--ink)', 
                    fontSize: '0.85rem', 
                    fontWeight: 700, 
                    border: '2px solid var(--ink)',
                    boxShadow: '2px 2px 0px var(--ink)',
                    fontFamily: 'var(--font-heading)'
                  }}
                >
                  ⚡ {lang}
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
        <h4 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)' }}>
          <FileText size={18} style={{ color: 'var(--accent-primary)' }} />
          <span>Extracted Project Source Files ({metadata.files?.length || 0})</span>
        </h4>

        <div style={{ maxHeight: '280px', overflowY: 'auto', borderRadius: 'var(--radius-md)', border: '2.5px solid var(--ink)', background: '#FFFFFF', boxShadow: '3px 3px 0px var(--ink)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)', borderBottom: '2.5px solid var(--ink)', color: 'var(--ink)' }}>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 800 }}>Relative File Path</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 800 }}>Language</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 800 }}>Lines of Code</th>
                <th style={{ padding: '0.75rem 1rem', fontWeight: 800 }}>File Size</th>
              </tr>
            </thead>
            <tbody>
              {metadata.files && metadata.files.length > 0 ? (
                metadata.files.map((file, idx) => (
                  <tr key={idx} style={{ borderBottom: '1.5px solid var(--ink)' }}>
                    <td style={{ padding: '0.65rem 1rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      📄 {file.relative_path}
                    </td>
                    <td style={{ padding: '0.65rem 1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                      {file.language}
                    </td>
                    <td style={{ padding: '0.65rem 1rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-primary)' }}>
                      {file.lines_of_code} LOC
                    </td>
                    <td style={{ padding: '0.65rem 1rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {(file.size_bytes / 1024).toFixed(1)} KB
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontWeight: 600 }}>
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
