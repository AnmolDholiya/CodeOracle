import React, { useState, useEffect } from 'react';
import { checkHealth } from './services/api';
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
  RefreshCw 
} from 'lucide-react';

function App() {
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState(null);
  
  // Project Metadata
  const [projectData, setProjectData] = useState(null);

  const fetchHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await checkHealth();
      setHealth(data);
    } catch (err) {
      setHealthError(err.message || 'Failed to connect to backend server');
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const handleUploadSuccess = (metadata) => {
    setProjectData(metadata);
  };

  const handleCleanupSuccess = () => {
    setProjectData(null);
  };

  return (
    <div className="app-container">
      {/* Navbar */}
      <nav className="navbar">
        <div className="brand">
          <Sparkles className="brand-icon" size={24} />
          <span>CodeOracle</span>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <button 
            className="btn-refresh" 
            onClick={fetchHealth}
            disabled={healthLoading}
          >
            <RefreshCw size={15} className={healthLoading ? 'spin' : ''} />
            {healthLoading ? 'Checking...' : 'API Health'}
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
            <Explanation projectId={projectData.project_id} projectFiles={projectData.files} />
            <UnitTestCard projectId={projectData.project_id} projectFiles={projectData.files} />
            <RefactorCard projectId={projectData.project_id} projectFiles={projectData.files} />
            <BreakingChangeCard projectId={projectData.project_id} projectFiles={projectData.files} />
            <DependencyGraph projectId={projectData.project_id} />
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
