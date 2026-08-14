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
import ImprovementsCard from './components/ImprovementsCard';
import ChatbotWidget from './components/ChatbotWidget';
import { 
  Sparkles, 
  RefreshCw,
  FileText,
  GitFork,
  FlaskConical,
  Zap,
  Wrench
} from 'lucide-react';

function App() {
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState(null);
  const [healthStage, setHealthStage] = useState(''); // waking stage message
  
  // Project Metadata
  const [projectData, setProjectData] = useState(null);

  // Active Feature Navigation Tab: 'explanation' | 'dependency_graph' | 'unit_tests' | 'refactor_breaking' | 'improvements'
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
      console.error('Health check failed:', err);
      setHealthError('API is waking up or offline. Please wait…');
      // Automatic retry/wake-up
      wakeBackendUp();
    } finally {
      setHealthLoading(false);
    }
  };

  const wakeBackendUp = async () => {
    setHealthStage('Connecting to backend…');
    const ok = await wakeUpBackend((msg) => setHealthStage(msg));
    if (ok) {
      const data = await checkHealth();
      setHealth(data);
      setHealthError(null);
      setHealthStage('');
    } else {
      setHealthError('Could not reach backend. If hosted on free tier, it may take 50s to wake.');
      setHealthStage('');
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const handleUploadSuccess = (data) => {
    setProjectData(data);
    setActiveFeatureTab('explanation');
  };

  const handleCleanupSuccess = () => {
    setProjectData(null);
  };

  return (
    <div className="app-container">
      {/* Header / Navbar */}
      <nav className="navbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#FF3385',
            filter: 'drop-shadow(1.5px 1.5px 0px var(--ink))'
          }}>
            <Sparkles size={26} />
          </div>
          <span style={{
            fontSize: '1.45rem',
            fontWeight: 800,
            color: 'var(--ink)',
            fontFamily: 'var(--font-heading)',
            letterSpacing: '-0.02em'
          }}>
            CodeOracle
          </span>
        </div>

        {/* Global Health Status Chip */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button 
            className="btn-health" 
            onClick={fetchHealth} 
            disabled={healthLoading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.55rem',
              background: '#FF3385',
              color: '#FFFFFF',
              border: '2.5px solid var(--ink)',
              boxShadow: '3.5px 3.5px 0px var(--ink)',
              padding: '0.5rem 1.35rem',
              borderRadius: 'var(--radius-pill)',
              fontWeight: 800,
              fontSize: '0.92rem',
              cursor: 'pointer',
              fontFamily: 'var(--font-heading)',
              transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)'
            }}
          >
            <RefreshCw size={16} color="#FFFFFF" className={healthLoading ? 'spin' : ''} />
            <span>{healthLoading ? (healthStage ? 'Waking…' : 'Checking…') : 'API Health'}</span>
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {!projectData && (
          <div className="hero">
            <h1 className="hero-title">Understand your legacy code.<br />Modernize it with confidence.</h1>
            <p className="hero-subtitle">
              Analyze code, generate unit tests, refactor safely and detect breaking changes with AI.
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
                  padding: '0.65rem 1.15rem',
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
                  padding: '0.65rem 1.15rem',
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
                  padding: '0.65rem 1.15rem',
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
                  padding: '0.65rem 1.15rem',
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
                <span>4. Refactored Code</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveFeatureTab('improvements')}
                style={{
                  flex: '1 1 auto',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  padding: '0.65rem 1.15rem',
                  borderRadius: 'var(--radius-pill)',
                  border: activeFeatureTab === 'improvements' ? '2px solid var(--ink)' : '2px solid transparent',
                  background: activeFeatureTab === 'improvements' ? '#FFD000' : 'transparent',
                  color: 'var(--ink)',
                  fontSize: '0.92rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-heading)',
                  cursor: 'pointer',
                  boxShadow: activeFeatureTab === 'improvements' ? '2px 2px 0px var(--ink)' : 'none',
                  transform: activeFeatureTab === 'improvements' ? 'translate(-1px, -1px)' : 'none',
                  transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
                  whiteSpace: 'nowrap'
                }}
              >
                <Wrench size={17} style={{ color: activeFeatureTab === 'improvements' ? 'var(--ink)' : 'var(--text-secondary)' }} />
                <span>5. Improvements</span>
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

            {activeFeatureTab === 'improvements' && (
              <ImprovementsCard projectId={projectData.project_id} />
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

      {/* Floating AI Chatbot Widget */}
      <ChatbotWidget projectId={projectData?.project_id} />
    </div>
  );
}

export default App;
