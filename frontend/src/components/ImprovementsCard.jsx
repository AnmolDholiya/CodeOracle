import React, { useState, useEffect, useMemo } from 'react';
import { 
  Wrench, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  Sparkles, 
  RefreshCw, 
  FileCode, 
  Layers, 
  ChevronDown, 
  ChevronUp, 
  Activity, 
  Info, 
  ArrowRight,
  Filter,
  Flame,
  Check
} from 'lucide-react';
import { getProjectImprovements, explainProjectImprovements, formatApiErrorMessage } from '../services/api';

const SEVERITY_CONFIG = {
  high: {
    label: 'HIGH',
    bg: '#FFF0F0',
    color: '#FF4D4D',
    border: '2px solid #FF4D4D',
    badgeBg: '#FF4D4D',
    badgeColor: '#FFFFFF'
  },
  medium: {
    label: 'MEDIUM',
    bg: '#FFFBF0',
    color: '#FF9F1C',
    border: '2px solid #FF9F1C',
    badgeBg: '#FFB800',
    badgeColor: '#1E1E2F'
  },
  low: {
    label: 'LOW',
    bg: '#F0F9FF',
    color: '#00D8F6',
    border: '2px solid #00D8F6',
    badgeBg: '#00D8F6',
    badgeColor: '#1E1E2F'
  },
  info: {
    label: 'INFO',
    bg: '#F5F3FF',
    color: '#8B5CF6',
    border: '2px solid #8B5CF6',
    badgeBg: '#8B5CF6',
    badgeColor: '#FFFFFF'
  }
};

export default function ImprovementsCard({ projectId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // AI Generation State
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);

  // Filter State: 'all' | 'high' | 'medium' | 'low' | category
  const [selectedFilter, setSelectedFilter] = useState('all');

  // Expanded evidence accordion map
  const [expandedEvidence, setExpandedEvidence] = useState({});

  const fetchImprovements = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getProjectImprovements(projectId);
      setData(res);
    } catch (err) {
      console.error('Failed to load project improvements:', err);
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      const errCode = (detail && typeof detail === 'object') ? detail.code : '';
      const errMsg = (detail && typeof detail === 'object') ? detail.message : (typeof detail === 'string' ? detail : err.message);

      if (status === 404 && (errCode === 'PROJECT_NOT_FOUND' || errMsg?.toLowerCase().includes('not found') || errMsg?.toLowerCase().includes('cleaned up'))) {
        setError({
          type: 'PROJECT_NOT_FOUND',
          title: 'Project Workspace No Longer Available',
          message: 'This project is no longer available on the backend server. Please upload your ZIP archive again to generate fresh recommendations.'
        });
      } else if (status === 404) {
        setError({
          type: 'ROUTE_NOT_FOUND',
          title: 'Endpoint Not Found',
          message: 'The improvements API route was not found on the backend. Please verify your deployment.'
        });
      } else if (status === 500) {
        setError({
          type: 'ANALYSIS_ERROR',
          title: 'Server Analysis Error',
          message: `Analysis error: ${errMsg || 'Unexpected server error while calculating recommendations.'}`
        });
      } else if (!err.response) {
        setError({
          type: 'NETWORK_ERROR',
          title: 'Backend Unreachable',
          message: 'Could not reach the analysis backend. If hosted on a free tier, it may be waking up.'
        });
      } else {
        setError({
          type: 'UNKNOWN',
          title: 'Request Failed',
          message: formatApiErrorMessage(err, 'Failed to calculate project improvements.')
        });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchImprovements();
  }, [projectId]);

  const handleExplainWithAi = async () => {
    if (!projectId || aiLoading) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await explainProjectImprovements(projectId);
      setData(res);
    } catch (err) {
      console.error('AI Improvements Explanation error:', err);
      setAiError(formatApiErrorMessage(err, 'AI reasoning service is currently unavailable. Deterministic analysis remains active.'));
    } finally {
      setAiLoading(false);
    }
  };

  const toggleEvidence = (recId) => {
    setExpandedEvidence(prev => ({
      ...prev,
      [recId]: !prev[recId]
    }));
  };

  const filteredRecommendations = useMemo(() => {
    if (!data?.recommendations) return [];
    if (selectedFilter === 'all') return data.recommendations;
    if (['high', 'medium', 'low'].includes(selectedFilter)) {
      return data.recommendations.filter(r => r.severity?.toLowerCase() === selectedFilter);
    }
    return data.recommendations.filter(r => r.category === selectedFilter);
  }, [data, selectedFilter]);

  const severityCounts = useMemo(() => {
    if (!data?.recommendations) return { high: 0, medium: 0, low: 0 };
    return {
      high: data.recommendations.filter(r => r.severity?.toLowerCase() === 'high').length,
      medium: data.recommendations.filter(r => r.severity?.toLowerCase() === 'medium').length,
      low: data.recommendations.filter(r => r.severity?.toLowerCase() === 'low').length,
    };
  }, [data]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', marginBottom: '2.5rem' }}>
      
      {/* ── 1. Main Header & Health Overview ──────────────────────────── */}
      <div className="status-card" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem', borderBottom: '2.5px solid var(--ink)', paddingBottom: '1.25rem' }}>
          <div>
            <h3 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem', fontFamily: 'var(--font-heading)' }}>
              <Wrench size={26} style={{ color: 'var(--accent-primary)', filter: 'drop-shadow(1.5px 1.5px 0px var(--ink))' }} />
              <span>Project Improvements & Recommendations</span>
            </h3>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', marginTop: '0.35rem', fontWeight: 500 }}>
              Evidence-backed architecture, code quality, and testing recommendations derived from deterministic local analysis.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              className="btn-refresh"
              onClick={handleExplainWithAi}
              disabled={aiLoading || loading}
              style={{ background: 'var(--accent-purple)' }}
            >
              {aiLoading ? <RefreshCw size={15} className="spin" /> : <Sparkles size={15} />}
              <span>{aiLoading ? 'Synthesizing with AI…' : 'Generate AI Recommendations'}</span>
            </button>

            <button 
              className="btn-refresh" 
              onClick={fetchImprovements}
              disabled={loading || aiLoading}
              style={{ background: '#FFFFFF', color: 'var(--ink)' }}
            >
              <RefreshCw size={15} className={loading ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {loading && (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <RefreshCw size={32} className="spin" style={{ color: 'var(--accent-primary)', margin: '0 auto 1rem' }} />
            <p style={{ fontWeight: 700, fontFamily: 'var(--font-heading)', fontSize: '1.1rem' }}>Calculating evidence-backed project recommendations…</p>
          </div>
        )}

        {!loading && error && (
          <div style={{ padding: '1.5rem', background: '#FFF0F0', border: '2.5px solid var(--accent-error)', borderRadius: 'var(--radius-md)', boxShadow: '3px 3px 0px var(--accent-error)', color: 'var(--accent-error)', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontWeight: 800, fontSize: '1.05rem', fontFamily: 'var(--font-heading)' }}>
              <AlertTriangle size={24} />
              <span>{typeof error === 'object' ? error.title : 'Analysis Notice'}</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.92rem', color: 'var(--text-primary)', fontWeight: 500, lineHeight: 1.5 }}>
              {typeof error === 'object' ? error.message : error}
            </p>
          </div>
        )}

        {!loading && !error && data && (
          <>
            {/* AI Summary Banner if present */}
            {data.ai_summary && (
              <div style={{ 
                background: '#F5F3FF', 
                border: '2.5px solid var(--accent-purple)', 
                borderRadius: 'var(--radius-md)', 
                padding: '1.25rem 1.5rem', 
                marginBottom: '1.75rem',
                boxShadow: '3px 3px 0px var(--accent-purple)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--accent-purple)', fontWeight: 800, fontFamily: 'var(--font-heading)' }}>
                  <Sparkles size={18} />
                  <span>AI Architecture Advisory Summary:</span>
                </div>
                <p style={{ fontSize: '0.92rem', color: 'var(--text-primary)', lineHeight: 1.6, margin: 0, fontWeight: 500 }}>
                  {data.ai_summary}
                </p>
              </div>
            )}

            {aiError && (
              <div style={{ background: '#FFF0F0', border: '2px solid var(--accent-error)', borderRadius: 'var(--radius-md)', padding: '0.85rem 1.25rem', marginBottom: '1.5rem', color: 'var(--accent-error)', fontSize: '0.88rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Info size={16} />
                <span>{aiError}</span>
              </div>
            )}

            {/* Health Metrics Grid */}
            <div style={{ marginBottom: '2rem' }}>
              <h4 style={{ fontSize: '1.1rem', fontWeight: 800, marginBottom: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)' }}>
                <Activity size={18} style={{ color: 'var(--accent-primary)' }} />
                <span>Project Health Score (Deterministic Calculation)</span>
              </h4>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                <div className="detail-item" style={{ background: '#FFF0F6' }}>
                  <div className="detail-label" style={{ color: 'var(--accent-primary)' }}>Overall Health</div>
                  <div className="detail-value" style={{ color: 'var(--accent-primary)', fontSize: '1.8rem' }}>
                    {data.health_metrics.overall_health_pct !== null ? `${data.health_metrics.overall_health_pct}%` : 'N/A'}
                  </div>
                </div>

                <div className="detail-item" style={{ background: '#FFFBF0' }}>
                  <div className="detail-label" style={{ color: 'var(--accent-warning)' }}>Code Quality</div>
                  <div className="detail-value" style={{ color: 'var(--accent-warning)', fontSize: '1.8rem' }}>
                    {data.health_metrics.code_quality_pct}%
                  </div>
                </div>

                <div className="detail-item" style={{ background: '#EBFDF2' }}>
                  <div className="detail-label" style={{ color: 'var(--accent-success)' }}>Architecture</div>
                  <div className="detail-value" style={{ color: 'var(--accent-success)', fontSize: '1.8rem' }}>
                    {data.health_metrics.architecture_pct}%
                  </div>
                </div>

                <div className="detail-item" style={{ background: '#F5F3FF' }}>
                  <div className="detail-label" style={{ color: 'var(--accent-purple)' }}>Test Health</div>
                  <div className="detail-value" style={{ color: 'var(--accent-purple)', fontSize: '1.8rem' }}>
                    {data.health_metrics.test_health_pct !== null ? `${data.health_metrics.test_health_pct}%` : 'Not Measured'}
                  </div>
                </div>
              </div>
            </div>

            {/* ── 2. "What's Already Good" (Verified Accomplishments) ── */}
            {data.already_done_well && data.already_done_well.length > 0 && (
              <div style={{ marginBottom: '2.5rem', background: '#F0FDF4', border: '2.5px solid var(--accent-success)', borderRadius: 'var(--radius-md)', padding: '1.5rem', boxShadow: '3px 3px 0px var(--accent-success)' }}>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#166534', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)' }}>
                  <CheckCircle2 size={22} style={{ color: 'var(--accent-success)' }} />
                  <span>What's Already Done Well ({data.already_done_well.length} Verified Items)</span>
                </h4>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.85rem' }}>
                  {data.already_done_well.map((item, idx) => (
                    <div key={idx} style={{ background: '#FFFFFF', border: '2px solid #166534', borderRadius: '10px', padding: '0.85rem 1rem', boxShadow: '2px 2px 0px #166534' }}>
                      <div style={{ fontWeight: 800, color: '#166534', fontSize: '0.95rem', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem', fontFamily: 'var(--font-heading)' }}>
                        <Check size={16} style={{ color: 'var(--accent-success)', strokeWidth: 3 }} />
                        <span>{item.title}</span>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                        {item.detail}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── 3. Filter Toolbar & Top Improvements ── */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                <h4 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)' }}>
                  <Flame size={20} style={{ color: 'var(--accent-primary)' }} />
                  <span>Prioritized Recommendations ({filteredRecommendations.length})</span>
                </h4>

                {/* Filter Chips */}
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    onClick={() => setSelectedFilter('all')}
                    style={{
                      padding: '0.35rem 0.85rem',
                      borderRadius: 'var(--radius-pill)',
                      border: selectedFilter === 'all' ? '2px solid var(--ink)' : '2px solid transparent',
                      background: selectedFilter === 'all' ? 'var(--ink)' : 'var(--bg-secondary)',
                      color: selectedFilter === 'all' ? '#FFFFFF' : 'var(--ink)',
                      fontSize: '0.8rem',
                      fontWeight: 800,
                      cursor: 'pointer',
                      boxShadow: selectedFilter === 'all' ? '2px 2px 0px var(--ink)' : 'none',
                      fontFamily: 'var(--font-heading)'
                    }}
                  >
                    All ({data.total_recommendations})
                  </button>

                  {severityCounts.high > 0 && (
                    <button
                      type="button"
                      onClick={() => setSelectedFilter('high')}
                      style={{
                        padding: '0.35rem 0.85rem',
                        borderRadius: 'var(--radius-pill)',
                        border: selectedFilter === 'high' ? '2px solid var(--ink)' : '2px solid transparent',
                        background: selectedFilter === 'high' ? '#FF4D4D' : '#FFF0F0',
                        color: selectedFilter === 'high' ? '#FFFFFF' : '#FF4D4D',
                        fontSize: '0.8rem',
                        fontWeight: 800,
                        cursor: 'pointer',
                        boxShadow: selectedFilter === 'high' ? '2px 2px 0px var(--ink)' : 'none',
                        fontFamily: 'var(--font-heading)'
                      }}
                    >
                      High ({severityCounts.high})
                    </button>
                  )}

                  {severityCounts.medium > 0 && (
                    <button
                      type="button"
                      onClick={() => setSelectedFilter('medium')}
                      style={{
                        padding: '0.35rem 0.85rem',
                        borderRadius: 'var(--radius-pill)',
                        border: selectedFilter === 'medium' ? '2px solid var(--ink)' : '2px solid transparent',
                        background: selectedFilter === 'medium' ? '#FFB800' : '#FFFBF0',
                        color: selectedFilter === 'medium' ? '#1E1E2F' : '#B45309',
                        fontSize: '0.8rem',
                        fontWeight: 800,
                        cursor: 'pointer',
                        boxShadow: selectedFilter === 'medium' ? '2px 2px 0px var(--ink)' : 'none',
                        fontFamily: 'var(--font-heading)'
                      }}
                    >
                      Medium ({severityCounts.medium})
                    </button>
                  )}

                  {severityCounts.low > 0 && (
                    <button
                      type="button"
                      onClick={() => setSelectedFilter('low')}
                      style={{
                        padding: '0.35rem 0.85rem',
                        borderRadius: 'var(--radius-pill)',
                        border: selectedFilter === 'low' ? '2px solid var(--ink)' : '2px solid transparent',
                        background: selectedFilter === 'low' ? '#00D8F6' : '#F0F9FF',
                        color: selectedFilter === 'low' ? '#1E1E2F' : '#0369A1',
                        fontSize: '0.8rem',
                        fontWeight: 800,
                        cursor: 'pointer',
                        boxShadow: selectedFilter === 'low' ? '2px 2px 0px var(--ink)' : 'none',
                        fontFamily: 'var(--font-heading)'
                      }}
                    >
                      Low ({severityCounts.low})
                    </button>
                  )}
                </div>
              </div>

              {filteredRecommendations.length === 0 ? (
                <div style={{ padding: '2.5rem', textAlign: 'center', background: 'var(--bg-secondary)', border: '2px dashed var(--ink)', borderRadius: 'var(--radius-md)' }}>
                  <ShieldCheck size={36} style={{ color: 'var(--accent-success)', margin: '0 auto 0.75rem' }} />
                  <p style={{ fontWeight: 800, fontSize: '1.05rem', color: 'var(--text-primary)', fontFamily: 'var(--font-heading)' }}>
                    No significant evidence-backed improvements in this category!
                  </p>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                    The codebase satisfies standard metrics for this filter.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  {filteredRecommendations.map((rec) => {
                    const sev = SEVERITY_CONFIG[rec.severity?.toLowerCase()] || SEVERITY_CONFIG.medium;
                    const isExpanded = expandedEvidence[rec.id];

                    return (
                      <div 
                        key={rec.id}
                        style={{
                          background: '#FFFFFF',
                          border: '2.5px solid var(--ink)',
                          borderRadius: 'var(--radius-md)',
                          padding: '1.4rem 1.6rem',
                          boxShadow: '4px 4px 0px var(--ink)',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        {/* Recommendation Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                            <span style={{
                              fontSize: '0.75rem',
                              fontWeight: 800,
                              padding: '0.2rem 0.65rem',
                              borderRadius: 'var(--radius-pill)',
                              background: sev.badgeBg,
                              color: sev.badgeColor,
                              border: '1.5px solid var(--ink)',
                              fontFamily: 'var(--font-heading)',
                              boxShadow: '1.5px 1.5px 0px var(--ink)'
                            }}>
                              {sev.label}
                            </span>

                            <span style={{
                              fontSize: '0.75rem',
                              fontWeight: 800,
                              padding: '0.2rem 0.65rem',
                              borderRadius: 'var(--radius-pill)',
                              background: 'var(--bg-secondary)',
                              color: 'var(--text-secondary)',
                              border: '1.5px solid var(--ink)',
                              fontFamily: 'var(--font-mono)'
                            }}>
                              {rec.category}
                            </span>

                            <h5 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0, fontFamily: 'var(--font-heading)' }}>
                              {rec.title}
                            </h5>
                          </div>

                          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                            Source: {rec.source}
                          </span>
                        </div>

                        {/* Description */}
                        <p style={{ fontSize: '0.92rem', color: 'var(--text-primary)', marginBottom: '0.75rem', lineHeight: 1.5, fontWeight: 500 }}>
                          {rec.description}
                        </p>

                        {/* Why it matters & Suggested Action */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1rem', fontSize: '0.88rem' }}>
                          <div style={{ background: '#FFFBF0', padding: '0.85rem 1rem', borderRadius: '8px', border: '1.5px solid #B45309' }}>
                            <div style={{ fontWeight: 800, color: '#B45309', marginBottom: '0.3rem', fontFamily: 'var(--font-heading)' }}>
                              💡 Why It Matters:
                            </div>
                            <div style={{ color: 'var(--text-primary)', lineHeight: 1.45, fontWeight: 500 }}>
                              {rec.why_it_matters}
                            </div>
                          </div>

                          <div style={{ background: '#F0FDF4', padding: '0.85rem 1rem', borderRadius: '8px', border: '1.5px solid #166534' }}>
                            <div style={{ fontWeight: 800, color: '#166534', marginBottom: '0.3rem', fontFamily: 'var(--font-heading)' }}>
                              🛠️ Suggested Action:
                            </div>
                            <div style={{ color: 'var(--text-primary)', lineHeight: 1.45, fontWeight: 500 }}>
                              {rec.action || rec.recommendation}
                            </div>
                          </div>
                        </div>

                        {/* Affected Files & View Evidence Toggle */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', borderTop: '1.5px solid var(--bg-secondary)', paddingTop: '0.75rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <span style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--text-secondary)', fontFamily: 'var(--font-heading)' }}>
                              Affected Files:
                            </span>
                            {rec.affected_files && rec.affected_files.length > 0 ? (
                              rec.affected_files.map((f, fIdx) => (
                                <code key={fIdx} style={{ fontSize: '0.8rem', background: 'var(--bg-secondary)', padding: '0.15rem 0.5rem', borderRadius: '4px', border: '1px solid var(--ink)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                                  📄 {f}
                                </code>
                              ))
                            ) : (
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Project-wide</span>
                            )}
                          </div>

                          <button
                            type="button"
                            onClick={() => toggleEvidence(rec.id)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.4rem',
                              background: '#FFFFFF',
                              border: '2px solid var(--ink)',
                              padding: '0.35rem 0.85rem',
                              borderRadius: 'var(--radius-pill)',
                              fontSize: '0.8rem',
                              fontWeight: 800,
                              cursor: 'pointer',
                              boxShadow: '2px 2px 0px var(--ink)',
                              fontFamily: 'var(--font-heading)'
                            }}
                          >
                            <span>{isExpanded ? 'Hide Evidence' : `View Evidence (${rec.evidence?.length || 0})`}</span>
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>
                        </div>

                        {/* Expandable Evidence Accordion */}
                        {isExpanded && rec.evidence && rec.evidence.length > 0 && (
                          <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px', border: '2px solid var(--ink)' }}>
                            <div style={{ fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-primary)', marginBottom: '0.5rem', fontFamily: 'var(--font-heading)' }}>
                              🔍 Traceable Evidence Metrics:
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                              {rec.evidence.map((ev, evIdx) => (
                                <div key={evIdx} style={{ background: '#FFFFFF', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1.5px solid var(--ink)', fontSize: '0.82rem' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                                    <span style={{ color: 'var(--accent-primary)' }}>File: {ev.file} {ev.symbol ? `:: ${ev.symbol}` : ''} {ev.line_number ? `(Line ${ev.line_number})` : ''}</span>
                                    <span style={{ color: 'var(--accent-purple)' }}>Metric: {ev.metric} = {String(ev.value)}</span>
                                  </div>
                                  <div style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
                                    {ev.details}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </div>

    </div>
  );
}
