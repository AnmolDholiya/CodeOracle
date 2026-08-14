import React, { useState, useEffect } from 'react';
import { checkHealth, wakeUpBackend } from './services/api';
import ZipUploadCard from './components/ZipUploadCard';
import ProjectMetadataCard from './components/ProjectMetadataCard';
import DependencyGraph from './components/DependencyGraph';
import AITestCard from './components/AITestCard';
import Explanation from './components/Explanation';
import UnitTestCard from './components/UnitTestCard';
import RefactorCard from './components/RefactorCard';
import BreakingChangeCard from './components/BreakingChangeCard';
import { 
  Sparkles, 
  RefreshCw,
  FileText,
  GitFork,
  FlaskConical,
  Zap
} from 'lucide-react';

function App() {
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState(null);
  const [healthStage, setHealthStage] = useState(''); // waking stage message
  
  // Project Metadata
  const [projectData, setProjectData] = useState(null);

  // Active Feature Navigation Tab: 'explanation' | 'dependency_graph' | 'unit_tests' | 'refactor_breaking'
  const [activeFeatureTab, setActiveFeatureTab] = useState('explanation');

  // On-demand health check
  const fetchHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    setHealthStage('');
    try {
      const data = await checkHealth();
      setHealth(data);
    } catch (err) {
      setHealthError(err.message || 'Failed to connect to backend server');
    } finally {
      setHealthLoading(false);
    }
  };

  // Initial mount: use wake-up with retries
  const initialWakeUp = async () => {
    setHealthLoading(true);
    setHealthError(null);
    setHealthStage('Connecting to backend…');
    try {
      const data = await wakeUpBackend((stage, attempt, maxAttempts) => {
        if (stage === 'connecting') setHealthStage('Connecting to backend…');
        else if (stage === 'waking' || stage === 'retrying') setHealthStage(`Backend is waking up… (${attempt}/${maxAttempts})`);
        else if (stage === 'ready') setHealthStage('');
      });
      setHealth(data);
    } catch (err) {
      setHealthError('Backend is temporarily unavailable. Click "API Health" to retry.');
    } finally {
      setHealthLoading(false);
      setHealthStage('');
    }
  };

  useEffect(() => {
    initialWakeUp();
  }, []);

  const handleUploadSuccess = (metadata) => {
    setProjectData(metadata);
    setActiveFeatureTab('explanation');
  };

  const handleCleanupSuccess = () => {
    setProjectData(null);
    setActiveFeatureTab('explanation');
  };

  return (
    <div className="app-container">
      {/* Navbar */}
      <nav className="navbar">
        <div className="brand">
          <Sparkles className="brand-icon" size={26} />
          <span>CodeOracle</span>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {healthStage && (
            <span style={{ fontSize: '0.85rem', color: 'var(--accent-warning)', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
              {healthStage}
            </span>
          )}
          <button 
            className="btn-refresh" 
            onClick={fetchHealth}
            disabled={healthLoading}
          >
            <RefreshCw size={15} className={healthLoading ? 'spin' : ''} />
            {healthLoading ? (healthStage ? 'Waking…' : 'Checking…') : 'API Health'}
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {!projectData && (
          <div className="hero">
            <h1 className="hero-title">Understand your legacy code.<br />Modernize it with confidence.</h1>
            <p className="hero-subtitle">
              Analyze legacy Python, JavaScript and TypeScript codebases, generate unit tests, refactor safely, and detect breaking changes with AI.
            </p>
          </div>
        )}

        {/* Upload Card or Workspace Overview */}
        {!projectData ? (
          <ZipUploadCard onUploadSuccess={handleUploadSuccess} />
        ) : (
          <>
            <ProjectMetadataCard metadata={projectData} onCleanup={handleCleanupSuccess} />

            {/* Feature Navigation Tabs Bar */}
            <div style={{
              background: '#FFFFFF',
              border: '2.5px solid var(--ink)',
              borderRadius: 'var(--radius-pill)',
              boxShadow: '4px 4px 0px var(--ink)',
              padding: '0.4rem 0.5rem',
              marginBottom: '2.5rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.5rem',
              overflowX: 'auto',
              flexWrap: 'wrap'
            }}>
              <button
                type="button"
                onClick={() => setActiveFeatureTab('explanation')}
                style={{
                  flex: '1 1 auto',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.65rem 1.25rem',
                  borderRadius: 'var(--radius-pill)',
                  border: activeFeatureTab === 'explanation' ? '2px solid var(--ink)' : '2px solid transparent',
                  background: activeFeatureTab === 'explanation' ? '#FFD000' : 'transparent',
                  color: 'var(--ink)',
                  fontSize: '0.92rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-heading)',
                  cursor: 'pointer',
                  boxShadow: activeFeatureTab === 'explanation' ? '2px 2px 0px var(--ink)' : 'none',
                  transform: activeFeatureTab === 'explanation' ? 'translate(-1px, -1px)' : 'none',
                  transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
                  whiteSpace: 'nowrap'
                }}
              >
                <FileText size={17} style={{ color: activeFeatureTab === 'explanation' ? 'var(--ink)' : 'var(--text-secondary)' }} />
                <span>1. Explanation</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveFeatureTab('dependency_graph')}
                style={{
                  flex: '1 1 auto',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.65rem 1.25rem',
                  borderRadius: 'var(--radius-pill)',
                  border: activeFeatureTab === 'dependency_graph' ? '2px solid var(--ink)' : '2px solid transparent',
                  background: activeFeatureTab === 'dependency_graph' ? '#FFD000' : 'transparent',
                  color: 'var(--ink)',
                  fontSize: '0.92rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-heading)',
                  cursor: 'pointer',
                  boxShadow: activeFeatureTab === 'dependency_graph' ? '2px 2px 0px var(--ink)' : 'none',
                  transform: activeFeatureTab === 'dependency_graph' ? 'translate(-1px, -1px)' : 'none',
                  transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
                  whiteSpace: 'nowrap'
                }}
              >
                <GitFork size={17} style={{ color: activeFeatureTab === 'dependency_graph' ? 'var(--ink)' : 'var(--text-secondary)' }} />
                <span>2. Dependency Graph</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveFeatureTab('unit_tests')}
                style={{
                  flex: '1 1 auto',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.65rem 1.25rem',
                  borderRadius: 'var(--radius-pill)',
                  border: activeFeatureTab === 'unit_tests' ? '2px solid var(--ink)' : '2px solid transparent',
                  background: activeFeatureTab === 'unit_tests' ? '#FFD000' : 'transparent',
                  color: 'var(--ink)',
                  fontSize: '0.92rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-heading)',
                  cursor: 'pointer',
                  boxShadow: activeFeatureTab === 'unit_tests' ? '2px 2px 0px var(--ink)' : 'none',
                  transform: activeFeatureTab === 'unit_tests' ? 'translate(-1px, -1px)' : 'none',
                  transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
                  whiteSpace: 'nowrap'
                }}
              >
                <FlaskConical size={17} style={{ color: activeFeatureTab === 'unit_tests' ? 'var(--ink)' : 'var(--text-secondary)' }} />
                <span>3. Generated Tests</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveFeatureTab('refactor_breaking')}
                style={{
                  flex: '1 1 auto',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.65rem 1.25rem',
                  borderRadius: 'var(--radius-pill)',
                  border: activeFeatureTab === 'refactor_breaking' ? '2px solid var(--ink)' : '2px solid transparent',
                  background: activeFeatureTab === 'refactor_breaking' ? '#FFD000' : 'transparent',
                  color: 'var(--ink)',
                  fontSize: '0.92rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-heading)',
                  cursor: 'pointer',
                  boxShadow: activeFeatureTab === 'refactor_breaking' ? '2px 2px 0px var(--ink)' : 'none',
                  transform: activeFeatureTab === 'refactor_breaking' ? 'translate(-1px, -1px)' : 'none',
                  transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
                  whiteSpace: 'nowrap'
                }}
              >
                <Zap size={17} style={{ color: activeFeatureTab === 'refactor_breaking' ? 'var(--ink)' : 'var(--text-secondary)' }} />
                <span>4. Refactored Code & Breaking Changes</span>
              </button>
            </div>

            {/* Active Tab View */}
            {activeFeatureTab === 'explanation' && (
              <Explanation projectId={projectData.project_id} projectFiles={projectData.files} />
            )}

            {activeFeatureTab === 'dependency_graph' && (
              <DependencyGraph projectId={projectData.project_id} />
            )}

            {activeFeatureTab === 'unit_tests' && (
              <UnitTestCard projectId={projectData.project_id} projectFiles={projectData.files} />
            )}

            {activeFeatureTab === 'refactor_breaking' && (
              <>
                <RefactorCard projectId={projectData.project_id} projectFiles={projectData.files} />
                <BreakingChangeCard projectId={projectData.project_id} projectFiles={projectData.files} />
              </>
            )}
          </>
        )}

        {/* AI Provider Indicator */}
        <AITestCard />
      </main>

      {/* Footer */}
      <footer className="footer">
        CodeOracle &copy; 2026 — AI-Powered Legacy Codebase Explainer & Modernizer
      </footer>
    </div>
  );
}

export default App;
