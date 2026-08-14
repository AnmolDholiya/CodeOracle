import React, { useState, useEffect } from 'react';
import { 
  BookOpen, 
  FileText, 
  Code, 
  Layers, 
  AlertTriangle, 
  CheckCircle2, 
  Loader2, 
  HelpCircle, 
  ChevronRight, 
  ShieldAlert, 
  Cpu, 
  Sparkles,
  Database,
  FileCode,
  FileJson,
  FileBox,
  RefreshCw,
  Info,
  Folder,
  FolderTree
} from 'lucide-react';
import api, { formatApiError } from '../services/api';

export default function Explanation({ projectId, projectFiles = [] }) {
  const [activeTab, setActiveTab] = useState('project'); // 'project' | 'file'
  const [selectedFile, setSelectedFile] = useState(projectFiles[0]?.relative_path || '');
  const [selectedFunction, setSelectedFunction] = useState(null);

  useEffect(() => {
    if (projectFiles.length > 0 && (!selectedFile || !projectFiles.some(f => f.relative_path === selectedFile))) {
      setSelectedFile(projectFiles[0].relative_path);
    }
  }, [projectFiles]);

  const [projectExp, setProjectExp] = useState(null);
  const [moduleExp, setModuleExp] = useState(null);
  const [functionExp, setFunctionExp] = useState(null);

  const [loadingProject, setLoadingProject] = useState(false);
  const [loadingModule, setLoadingModule] = useState(false);
  const [loadingFunction, setLoadingFunction] = useState(false);

  const [errorProject, setErrorProject] = useState(null);
  const [errorModule, setErrorModule] = useState(null);

  // Helper to render file icon based on extension
  const getFileIcon = (path) => {
    if (!path) return <FileText size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />;
    const lower = path.toLowerCase();
    if (lower.endsWith('.py')) return <Code size={14} style={{ color: '#60a5fa', flexShrink: 0 }} />;
    if (lower.endsWith('.md')) return <FileText size={14} style={{ color: 'var(--accent-success)', flexShrink: 0 }} />;
    if (lower.endsWith('.json') || lower.endsWith('.toml') || lower.endsWith('.yaml') || lower.endsWith('.yml')) 
      return <FileJson size={14} style={{ color: 'var(--accent-warning)', flexShrink: 0 }} />;
    if (lower.endsWith('.js') || lower.endsWith('.jsx') || lower.endsWith('.ts') || lower.endsWith('.tsx')) 
      return <FileCode size={14} style={{ color: '#f472b6', flexShrink: 0 }} />;
    return <FileBox size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />;
  };

  // On-Demand Fetch Project Overview
  const fetchProjectExplanation = async (forceRefresh = false) => {
    if (loadingProject) return;
    setLoadingProject(true);
    setErrorProject(null);

    try {
      const url = `/api/projects/${projectId}/explanations/project` + (forceRefresh ? '?force_refresh=true' : '');
      const res = await api.get(url);
      setProjectExp(res.data);
    } catch (err) {
      console.error('Project explanation error:', err);
      setErrorProject(formatApiError(err, 'Failed to fetch project explanation'));
    } finally {
      setLoadingProject(false);
    }
  };

  // On-Demand Fetch Module / File Explanation
  const fetchModuleExplanation = async (filePath, forceRefresh = false) => {
    if (!filePath || loadingModule) return;
    setLoadingModule(true);
    setErrorModule(null);

    try {
      const url = `/api/projects/${projectId}/explanations/module` + (forceRefresh ? '?force_refresh=true' : '');
      const res = await api.post(url, {
        file_path: filePath
      });
      setModuleExp(res.data);
    } catch (err) {
      console.error('Module explanation error:', err);
      setErrorModule(formatApiError(err, 'Failed to fetch file explanation'));
    } finally {
      setLoadingModule(false);
    }
  };

  // Explicit On-Demand Fetch Function Explanation
  const fetchFunctionExplanation = async (filePath, funcName, forceRefresh = false) => {
    if (!filePath || !funcName || loadingFunction) return;
    setLoadingFunction(true);

    try {
      const url = `/api/projects/${projectId}/explanations/function` + (forceRefresh ? '?force_refresh=true' : '');
      const res = await api.post(url, {
        file_path: filePath,
        function_name: funcName
      });
      setFunctionExp(res.data);
    } catch (err) {
      console.error('Function explanation error:', err);
    } finally {
      setLoadingFunction(false);
    }
  };

  // Fetch Project Overview ONLY when Project tab is active and data is not present
  useEffect(() => {
    if (projectId && activeTab === 'project' && !projectExp && !loadingProject) {
      fetchProjectExplanation();
    }
  }, [projectId, activeTab]);

  // Fetch File Explanation ONLY when File tab is active and selected file changes
  useEffect(() => {
    if (projectId && activeTab === 'file' && selectedFile && (!moduleExp || moduleExp.file_path !== selectedFile) && !loadingModule) {
      fetchModuleExplanation(selectedFile);
    }
  }, [projectId, activeTab, selectedFile]);

  // Helper to render file icon/type badge
  const renderFileTypeBadge = (fileType, isBinary) => {
    if (isBinary) {
      return (
        <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.15)', color: 'var(--accent-error)', border: '1px solid rgba(239, 68, 68, 0.3)', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
          <Database size={12} /> Binary / Database
        </span>
      );
    }

    switch (fileType) {
      case 'python':
        return (
          <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.3)', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            <Code size={12} /> Python Source
          </span>
        );
      case 'markdown':
        return (
          <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(16, 185, 129, 0.15)', color: 'var(--accent-success)', border: '1px solid rgba(16, 185, 129, 0.3)', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            <FileText size={12} /> Markdown Document
          </span>
        );
      case 'json':
      case 'config':
        return (
          <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(245, 158, 11, 0.15)', color: 'var(--accent-warning)', border: '1px solid rgba(245, 158, 11, 0.3)', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            <FileJson size={12} /> Configuration / Schema
          </span>
        );
      case 'javascript':
      case 'typescript':
        return (
          <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(236, 72, 153, 0.15)', color: '#f472b6', border: '1px solid rgba(236, 72, 153, 0.3)', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            <FileCode size={12} /> JS / TS Source
          </span>
        );
      default:
        return (
          <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(255, 255, 255, 0.1)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            <FileBox size={12} /> Text / Config
          </span>
        );
    }
  };

  return (
    <div className="status-card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
      {/* Section Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Sparkles size={22} style={{ color: 'var(--accent-primary)' }} />
            <span>AI Code Explanation Engine</span>
          </h2>
        </div>

        {/* View Tabs */}
        <div style={{ display: 'flex', gap: '0.35rem', background: 'var(--bg-secondary)', padding: '0.25rem', borderRadius: '9999px', border: '1px solid var(--border-color)' }}>
          <button
            onClick={() => setActiveTab('project')}
            style={{
              background: activeTab === 'project' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'project' ? '#fff' : 'var(--text-secondary)',
              border: 'none',
              padding: '0.4rem 1rem',
              borderRadius: '9999px',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              transition: 'all 0.2s ease'
            }}
          >
            <FolderTree size={14} /> Project Overview
          </button>
          <button
            onClick={() => setActiveTab('file')}
            style={{
              background: activeTab === 'file' ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === 'file' ? '#fff' : 'var(--text-secondary)',
              border: 'none',
              padding: '0.4rem 1rem',
              borderRadius: '9999px',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              transition: 'all 0.2s ease'
            }}
          >
            <FileText size={14} /> File Explorer
          </button>
        </div>
      </div>

      {/* TAB 1: PROJECT OVERVIEW */}
      {activeTab === 'project' && (
        <div>
          {loadingProject && (
            <div style={{ padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#60a5fa', fontSize: '0.875rem' }}>
              <Loader2 size={18} className="spin" />
              <span>Generating project architectural overview...</span>
            </div>
          )}

          {errorProject && (
            <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--accent-error)', fontSize: '0.875rem' }}>
                <AlertTriangle size={18} />
                <span>{errorProject}</span>
              </div>
              <button 
                className="btn-refresh" 
                disabled={loadingProject}
                onClick={() => fetchProjectExplanation(true)} 
                style={{ padding: '0.35rem 0.85rem', fontSize: '0.8rem', opacity: loadingProject ? 0.6 : 1 }}
              >
                {loadingProject ? "Generating..." : "Retry"}
              </button>
            </div>
          )}

          {projectExp && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Static Fallback Banner */}
              {projectExp.is_static_fallback && (
                <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-warning)', fontSize: '0.85rem' }}>
                    <Info size={16} />
                    <span>{projectExp.fallback_reason || "AI explanation temporarily unavailable. Showing static analysis."}</span>
                  </div>
                  <button 
                    className="btn-refresh" 
                    disabled={loadingProject}
                    onClick={() => fetchProjectExplanation(true)} 
                    style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem', opacity: loadingProject ? 0.6 : 1 }}
                  >
                    {loadingProject ? "Generating..." : "Retry AI Explanation"}
                  </button>
                </div>
              )}

              {/* Purpose Card */}
              <div style={{ padding: '1.25rem 1.5rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <h4 style={{ color: 'var(--accent-primary)', marginBottom: '0.5rem', fontSize: '1rem', fontWeight: 800 }}>Project Purpose</h4>
                <p style={{ fontSize: '0.925rem', color: 'var(--text-primary)', lineHeight: 1.6, margin: 0 }}>{projectExp.purpose}</p>
              </div>

              {/* Architecture Card */}
              <div style={{ padding: '1.25rem 1.5rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <h4 style={{ color: 'var(--accent-secondary)', marginBottom: '0.5rem', fontSize: '1rem', fontWeight: 800 }}>Architecture & Design Pattern</h4>
                <p style={{ fontSize: '0.925rem', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>{projectExp.architecture}</p>
              </div>

              {/* Components & Workflow Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
                <div style={{ padding: '1.15rem 1.25rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.6rem' }}>Main Components</h4>
                  <ul style={{ paddingLeft: '1.2rem', margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {(projectExp.main_components.length > 0 ? projectExp.main_components : projectExp.major_modules).map((m, idx) => (
                      <li key={idx} style={{ marginBottom: '0.35rem' }}>{m}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ padding: '1.15rem 1.25rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.6rem' }}>Main Workflow</h4>
                  <ul style={{ paddingLeft: '1.2rem', margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {(projectExp.main_workflow.length > 0 ? projectExp.main_workflow : projectExp.execution_flow).map((f, idx) => (
                      <li key={idx} style={{ marginBottom: '0.35rem' }}>{f}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Technologies & Key Dependencies */}
              <div style={{ padding: '1.15rem 1.25rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.6rem' }}>Technologies & Key Dependencies</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                  {(projectExp.technologies.length > 0 ? projectExp.technologies : projectExp.important_dependencies).map((dep, idx) => (
                    <span key={idx} style={{ padding: '0.3rem 0.75rem', borderRadius: '9999px', background: 'rgba(244, 63, 94, 0.08)', color: 'var(--accent-primary)', fontSize: '0.8rem', fontWeight: 700, border: '1px solid rgba(244, 63, 94, 0.2)' }}>
                      {dep}
                    </span>
                  ))}
                </div>
              </div>

              {/* Maintenance Concerns */}
              {projectExp.maintenance_concerns.length > 0 && (
                <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                  <h4 style={{ color: 'var(--accent-warning)', fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <ShieldAlert size={16} /> Maintenance Concerns
                  </h4>
                  <ul style={{ paddingLeft: '1.2rem', margin: 0, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                    {projectExp.maintenance_concerns.map((c, idx) => (
                      <li key={idx} style={{ marginBottom: '0.35rem' }}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: FILE & FUNCTION EXPLAINER */}
      {activeTab === 'file' && (
        <div style={{ display: 'grid', gridTemplateColumns: '290px 1fr', gap: '1.5rem' }}>
          {/* File Picker Sidebar */}
          <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', padding: '1rem', display: 'flex', flexDirection: 'column' }}>
            <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.85rem', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Folder size={14} style={{ color: 'var(--accent-primary)' }} />
              <span>Project Files</span>
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', maxHeight: '480px', overflowY: 'auto', paddingRight: '0.35rem' }}>
              {projectFiles.map((f) => (
                <button
                  key={f.relative_path}
                  onClick={() => {
                    if (selectedFile !== f.relative_path) {
                      setSelectedFile(f.relative_path);
                      setSelectedFunction('');
                      setFunctionExp(null);
                    }
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.55rem',
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.55rem 0.75rem',
                    borderRadius: 'var(--radius-md)',
                    background: selectedFile === f.relative_path 
                      ? 'var(--accent-primary)' 
                      : '#ffffff',
                    color: selectedFile === f.relative_path ? '#ffffff' : 'var(--text-primary)',
                    border: selectedFile === f.relative_path 
                      ? '1px solid var(--accent-primary)' 
                      : '1px solid var(--border-color)',
                    fontSize: '0.825rem',
                    lineHeight: '1.4',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: selectedFile === f.relative_path ? 700 : 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    boxShadow: selectedFile === f.relative_path ? '0 2px 8px rgba(244, 63, 94, 0.25)' : 'var(--shadow-sm)'
                  }}
                >
                  {getFileIcon(f.relative_path)}
                  <span style={{
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    flex: 1
                  }}>
                    {f.relative_path}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Explanation Content Area */}
          <div>
            {loadingModule && (
              <div style={{ padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#60a5fa', fontSize: '0.875rem' }}>
                <Loader2 size={18} className="spin" />
                <span>Generating file explanation for {selectedFile}...</span>
              </div>
            )}

            {errorModule && (
              <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--accent-error)', fontSize: '0.875rem' }}>
                  <AlertTriangle size={18} />
                  <span>{errorModule}</span>
                </div>
                <button 
                  className="btn-refresh" 
                  disabled={loadingModule}
                  onClick={() => fetchModuleExplanation(selectedFile, true)} 
                  style={{ padding: '0.35rem 0.85rem', fontSize: '0.8rem', opacity: loadingModule ? 0.6 : 1 }}
                >
                  {loadingModule ? "Generating..." : "Retry"}
                </button>
              </div>
            )}

            {moduleExp && !loadingModule && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {/* Static Fallback Banner */}
                {moduleExp.is_static_fallback && (
                  <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-warning)', fontSize: '0.85rem' }}>
                      <Info size={16} />
                      <span>{moduleExp.fallback_reason || "AI explanation temporarily unavailable. Showing static analysis."}</span>
                    </div>
                    <button 
                      className="btn-refresh" 
                      disabled={loadingModule}
                      onClick={() => fetchModuleExplanation(selectedFile, true)} 
                      style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem', opacity: loadingModule ? 0.6 : 1 }}
                    >
                      {loadingModule ? "Generating..." : "Retry AI Explanation"}
                    </button>
                  </div>
                )}

                {/* File Header */}
                <div style={{ padding: '1.25rem', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{moduleExp.file_path}</span>
                    {renderFileTypeBadge(moduleExp.file_type, moduleExp.is_binary)}
                  </div>

                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0.3rem 0 0.6rem 0' }}>
                    {moduleExp.purpose}
                  </h3>

                  {moduleExp.summary && (
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                      {moduleExp.summary}
                    </p>
                  )}

                  <div style={{ marginTop: '0.75rem' }}>
                    <strong style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>Responsibilities:</strong>
                    <ul style={{ paddingLeft: '1.2rem', margin: '0.3rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      {moduleExp.responsibilities.map((r, idx) => (
                        <li key={idx} style={{ marginBottom: '0.2rem' }}>{r}</li>
                      ))}
                    </ul>
                  </div>

                  {moduleExp.dependencies.length > 0 && (
                    <div style={{ marginTop: '0.75rem' }}>
                      <strong style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>Dependencies:</strong>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.3rem' }}>
                        {moduleExp.dependencies.map((dep, idx) => (
                          <span key={idx} style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', background: 'rgba(255,255,255,0.05)', fontSize: '0.775rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-secondary)' }}>
                            {dep}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {moduleExp.potential_issues.length > 0 && (
                    <div style={{ marginTop: '0.75rem' }}>
                      <strong style={{ fontSize: '0.825rem', color: 'var(--accent-warning)' }}>Potential Issues:</strong>
                      <ul style={{ paddingLeft: '1.2rem', margin: '0.3rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-muted)' }}>
                        {moduleExp.potential_issues.map((issue, idx) => (
                          <li key={idx}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Actions / Function Logic Section */}
                {!moduleExp.is_binary && (
                  <div>
                    {moduleExp.functions && moduleExp.functions.length > 0 ? (
                      <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)' }}>
                        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.6rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <Code size={16} style={{ color: 'var(--accent-secondary)' }} />
                          <span>Inspect Function Logic (Click to Explain)</span>
                        </h4>

                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                          {moduleExp.functions.map((fnName) => (
                            <button
                              key={fnName}
                              disabled={loadingFunction}
                              onClick={() => {
                                setSelectedFunction(fnName);
                                fetchFunctionExplanation(selectedFile, fnName);
                              }}
                              style={{
                                padding: '0.4rem 0.8rem',
                                borderRadius: 'var(--radius-sm)',
                                background: selectedFunction === fnName ? 'var(--accent-secondary)' : 'rgba(255,255,255,0.05)',
                                color: '#fff',
                                border: '1px solid var(--border-color)',
                                fontSize: '0.8rem',
                                fontFamily: 'var(--font-mono)',
                                cursor: loadingFunction ? 'not-allowed' : 'pointer',
                                opacity: loadingFunction && selectedFunction === fnName ? 0.6 : 1
                              }}
                            >
                              {loadingFunction && selectedFunction === fnName ? "Generating..." : `${fnName}()`}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div style={{ padding: '0.85rem 1rem', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', fontSize: '0.825rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <CheckCircle2 size={16} style={{ color: 'var(--accent-success)' }} />
                        <span>
                          {moduleExp.file_type === 'markdown' && "Markdown document structured analysis complete."}
                          {moduleExp.file_type === 'json' && "JSON configuration schema analysis complete."}
                          {moduleExp.file_type === 'config' && "Configuration file analysis complete."}
                          {(moduleExp.file_type === 'text' || moduleExp.file_type === 'unknown') && "Text content file analysis complete."}
                          {moduleExp.file_type === 'python' && "No standalone functions defined in this file."}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Function Specific Explanation */}
                {loadingFunction && (
                  <div style={{ padding: '1rem', background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--accent-primary)', fontSize: '0.875rem' }}>
                    <Loader2 size={18} className="spin" />
                    <span>Analyzing function logic for {selectedFunction}()...</span>
                  </div>
                )}

                {functionExp && selectedFunction && !loadingFunction && (
                  <div style={{ padding: '1.25rem', borderRadius: 'var(--radius-md)', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
                    <h4 style={{ color: 'var(--accent-primary)', fontSize: '1rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                      Function: <span style={{ fontFamily: 'var(--font-mono)' }}>{functionExp.function_name}()</span>
                    </h4>
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '1rem' }}>{functionExp.purpose}</p>

                    <div style={{ marginBottom: '1rem' }}>
                      <strong style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>Parameters:</strong>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.3rem' }}>
                        {functionExp.parameters_explained.map((p, idx) => (
                          <div key={idx} style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
                            <code style={{ color: 'var(--accent-secondary)' }}>{p.name}</code> — {p.explanation}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ marginBottom: '1rem' }}>
                      <strong style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>Step-by-Step Logic:</strong>
                      <ol style={{ paddingLeft: '1.2rem', margin: '0.3rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-muted)' }}>
                        {functionExp.step_by_step_logic.map((step, idx) => (
                          <li key={idx} style={{ marginBottom: '0.25rem' }}>{step}</li>
                        ))}
                      </ol>
                    </div>

                    {functionExp.edge_cases.length > 0 && (
                      <div>
                        <strong style={{ fontSize: '0.825rem', color: 'var(--accent-warning)' }}>Edge Cases:</strong>
                        <ul style={{ paddingLeft: '1.2rem', margin: '0.3rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-muted)' }}>
                          {functionExp.edge_cases.map((ec, idx) => (
                            <li key={idx}>{ec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
