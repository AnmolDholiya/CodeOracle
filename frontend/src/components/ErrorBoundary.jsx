import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("CodeOracle Frontend ErrorBoundary Caught:", error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          backgroundColor: '#090d16',
          color: '#f9fafb',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
          fontFamily: 'system-ui, -apple-system, sans-serif'
        }}>
          <div style={{
            maxWidth: '600px',
            width: '100%',
            background: 'rgba(17, 24, 39, 0.8)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            borderRadius: '12px',
            padding: '2rem',
            boxShadow: '0 0 25px rgba(239, 68, 68, 0.15)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem', color: '#ef4444' }}>
              <AlertTriangle size={28} />
              <h2 style={{ margin: 0, fontSize: '1.4rem' }}>CodeOracle Frontend Error</h2>
            </div>
            
            <p style={{ color: '#9ca3af', marginBottom: '1.25rem', fontSize: '0.95rem' }}>
              A React component error occurred while rendering the page.
            </p>

            <pre style={{
              background: '#000',
              padding: '1rem',
              borderRadius: '6px',
              color: '#fca5a5',
              fontSize: '0.85rem',
              overflowX: 'auto',
              marginBottom: '1.5rem',
              fontFamily: 'monospace'
            }}>
              {this.state.error?.toString() || 'Unknown React Error'}
            </pre>

            <button
              onClick={() => window.location.reload()}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: '#6366f1',
                color: '#fff',
                border: 'none',
                padding: '0.75rem 1.25rem',
                borderRadius: '6px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <RefreshCw size={16} /> Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
