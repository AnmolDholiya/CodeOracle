import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  ReactFlow, 
  Background, 
  Controls, 
  MiniMap, 
  useNodesState, 
  useEdgesState, 
  MarkerType,
  Position,
  Handle
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from '@dagrejs/dagre';
import { getProjectDependencies, formatApiError } from '../services/api';
import { 
  GitFork, 
  RefreshCw, 
  Search, 
  FileCode, 
  AlertCircle, 
  Package, 
  ArrowRightLeft,
  Sparkles
} from 'lucide-react';

const getLanguageTheme = (path) => {
  if (!path) return { label: 'File', color: '#64748b', bgColor: '#ffffff', borderColor: '#cbd5e1', badgeBg: '#f1f5f9', badgeColor: '#475569', icon: '📄' };
  if (path.endsWith('.py')) {
    return {
      label: 'Python',
      color: '#0d9488',
      bgColor: 'rgba(13, 148, 136, 0.04)',
      borderColor: '#0d9488',
      badgeBg: 'rgba(13, 148, 136, 0.12)',
      badgeColor: '#0f766e',
      icon: '🐍'
    };
  }
  if (path.endsWith('.tsx') || path.endsWith('.jsx')) {
    return {
      label: 'React',
      color: '#6366f1',
      bgColor: 'rgba(99, 102, 241, 0.04)',
      borderColor: '#6366f1',
      badgeBg: 'rgba(99, 102, 241, 0.12)',
      badgeColor: '#4338ca',
      icon: '⚛️'
    };
  }
  if (path.endsWith('.ts') || path.endsWith('.js')) {
    return {
      label: 'JS/TS',
      color: '#f59e0b',
      bgColor: 'rgba(245, 158, 11, 0.04)',
      borderColor: '#f59e0b',
      badgeBg: 'rgba(245, 158, 11, 0.12)',
      badgeColor: '#b45309',
      icon: '📜'
    };
  }
  if (path.endsWith('.json') || path.endsWith('.yaml') || path.endsWith('.yml')) {
    return {
      label: 'Config',
      color: '#64748b',
      bgColor: 'rgba(100, 116, 139, 0.04)',
      borderColor: '#64748b',
      badgeBg: 'rgba(100, 116, 139, 0.12)',
      badgeColor: '#334155',
      icon: '⚙️'
    };
  }
  return {
    label: 'File',
    color: '#64748b',
    bgColor: '#ffffff',
    borderColor: '#cbd5e1',
    badgeBg: '#f1f5f9',
    badgeColor: '#475569',
    icon: '📄'
  };
};

// Structured PERT / CPM Matrix Card Component
const FileNodeComponent = ({ data }) => {
  const lang = getLanguageTheme(data.relative_path);
  const isErr = data.has_syntax_error;
  const isSelected = data.isSelected;
  const isSearchMatch = data.isSearchMatch;
  const isOutgoing = data.isOutgoing;
  const isIncoming = data.isIncoming;
  const layoutDir = data.layoutDir || 'LR';

  const handlePosTarget = layoutDir === 'LR' ? Position.Left : Position.Top;
  const handlePosSource = layoutDir === 'LR' ? Position.Right : Position.Bottom;

  let borderColor = '#475569';
  let headerBg = '#334155';
  let headerColor = '#ffffff';

  if (isSelected) {
    borderColor = '#ef4444';
    headerBg = '#ef4444';
  } else if (isOutgoing) {
    borderColor = '#ef4444';
    headerBg = '#ef4444';
  } else if (isIncoming) {
    borderColor = '#10b981';
    headerBg = '#10b981';
  } else if (isErr) {
    borderColor = '#dc2626';
    headerBg = '#dc2626';
  } else if (isSearchMatch) {
    borderColor = '#0284c7';
    headerBg = '#0284c7';
  }

  const folderName = data.relative_path ? (data.relative_path.includes('/') ? data.relative_path.substring(0, data.relative_path.lastIndexOf('/')) : 'root') : 'root';

  return (
    <div style={{
      width: '185px',
      height: '66px',
      background: '#ffffff',
      border: `1.75px solid ${borderColor}`,
      borderRadius: '4px',
      boxShadow: isSelected || isOutgoing ? '0 0 0 3px rgba(239, 68, 68, 0.35)' : '0 2px 8px rgba(0, 0, 0, 0.08)',
      display: 'flex',
      flexDirection: 'column',
      position: 'relative',
      cursor: 'pointer',
      boxSizing: 'border-box',
      opacity: data.opacity ?? 1,
      fontFamily: 'var(--font-mono, monospace)',
      transition: 'all 0.2s ease'
    }}>
      <Handle 
        type="target" 
        position={handlePosTarget} 
        style={{ background: borderColor, width: 8, height: 8, border: '1.5px solid #fff' }} 
      />

      {/* Top Header: Title / Filename */}
      <div style={{
        background: headerBg,
        color: headerColor,
        padding: '3px 6px',
        fontSize: '11px',
        fontWeight: 800,
        textAlign: 'center',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        borderBottom: `1px solid ${borderColor}`
      }} title={data.label}>
        {data.label}
      </div>

      {/* Middle Row: 2 Split Cells */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', flex: 1, borderBottom: `1px solid ${borderColor}`, background: '#ffffff' }}>
        <div style={{ borderRight: `1px solid ${borderColor}`, padding: '2px 4px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700, color: 'var(--text-primary)' }}>
          {lang.icon} {lang.label}
        </div>
        <div style={{ padding: '2px 4px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700, color: 'var(--text-primary)' }}>
          {data.lines_of_code || 0} LOC
        </div>
      </div>

      {/* Bottom Row: 2 Split Cells */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', background: '#f8fafc', fontSize: '9px', fontWeight: 600 }}>
        <div style={{ borderRight: `1px solid ${borderColor}`, padding: '2px 4px', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={folderName}>
          📁 {folderName}
        </div>
        <div style={{ padding: '2px 4px', textAlign: 'center', color: lang.color, fontWeight: 700 }}>
          {data.functions_count || 0} fns
        </div>
      </div>

      <Handle 
        type="source" 
        position={handlePosSource} 
        style={{ background: borderColor, width: 8, height: 8, border: '1.5px solid #fff' }} 
      />
    </div>
  );
};

const nodeTypes = {
  fileNode: FileNodeComponent
};

export default function DependencyGraph({ projectId }) {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [layoutDirection, setLayoutDirection] = useState('LR'); // Default LR (Left to Right) as shown in reference diagram
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const fetchDependencies = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getProjectDependencies(projectId);
      setGraphData(data);
      buildFlowElements(data.nodes || [], data.edges || [], layoutDirection);
    } catch (err) {
      console.error('Failed to load dependency graph:', err);
      setError(formatApiError(err, 'Unable to load dependency graph. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDependencies();
  }, [projectId]);

  const toggleLayoutDirection = () => {
    const newDirection = layoutDirection === 'LR' ? 'TB' : 'LR';
    setLayoutDirection(newDirection);
    if (graphData) {
      buildFlowElements(graphData.nodes || [], graphData.edges || [], newDirection);
    }
  };

  // Build Left-to-Right PERT / CPM Column Matrix Layout
  const buildFlowElements = (rawNodes, rawEdges, dir = 'LR') => {
    if (!rawNodes || rawNodes.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const nodeMap = new Map();
    rawNodes.forEach(n => nodeMap.set(n.id, n));

    const edgesMap = new Map();

    // 1. Extract backend rawEdges
    (rawEdges || []).forEach(e => {
      if (nodeMap.has(e.source) && nodeMap.has(e.target) && e.source !== e.target) {
        const edgeKey = `${e.source}->${e.target}`;
        edgesMap.set(edgeKey, { source: e.source, target: e.target });
      }
    });

    // 2. Complement from node.project_dependencies if any missing
    rawNodes.forEach(n => {
      if (n.project_dependencies && Array.isArray(n.project_dependencies)) {
        n.project_dependencies.forEach(tgt => {
          if (nodeMap.has(tgt) && n.id !== tgt) {
            const edgeKey = `${n.id}->${tgt}`;
            if (!edgesMap.has(edgeKey)) {
              edgesMap.set(edgeKey, { source: n.id, target: tgt });
            }
          }
        });
      }
    });

    const validEdges = Array.from(edgesMap.values());

    // 3. Create Dagre Graph for PERT / CPM Matrix alignment
    const g = new dagre.graphlib.Graph();
    g.setGraph({ 
      rankdir: dir, 
      nodesep: 35, 
      ranksep: 90, 
      marginx: 40, 
      marginy: 40 
    });
    g.setDefaultEdgeLabel(() => ({}));

    const cardWidth = 185;
    const cardHeight = 66;

    rawNodes.forEach(n => {
      g.setNode(n.id, { width: cardWidth, height: cardHeight });
    });

    validEdges.forEach(e => {
      g.setEdge(e.source, e.target);
    });

    dagre.layout(g);

    // 4. Generate Flow Nodes
    const flowNodes = rawNodes.map(n => {
      const dagNode = g.node(n.id);
      const x = dagNode ? dagNode.x - cardWidth / 2 : 0;
      const y = dagNode ? dagNode.y - cardHeight / 2 : 0;

      return {
        id: n.id,
        type: 'fileNode',
        data: {
          label: n.label,
          relative_path: n.relative_path,
          lines_of_code: n.lines_of_code,
          classes_count: n.classes_count,
          functions_count: n.functions_count,
          has_syntax_error: n.has_syntax_error,
          nodeData: n,
          layoutDir: dir
        },
        position: { x, y }
      };
    });

    // 5. Generate Flow Edges
    const flowEdges = validEdges.map((e, idx) => ({
      id: `edge-${e.source}->${e.target}-${idx}`,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      animated: false,
      style: {
        stroke: '#475569',
        strokeWidth: 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#475569',
        width: 16,
        height: 16,
      },
    }));

    setNodes(flowNodes);
    setEdges(flowEdges);

    if (reactFlowInstance) {
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.15, duration: 400 });
      }, 100);
    }
  };

  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node.data?.nodeData || null);
  }, []);

  const onInitReactFlow = useCallback((instance) => {
    setReactFlowInstance(instance);
    setTimeout(() => {
      instance.fitView({ padding: 0.15, duration: 400 });
    }, 120);
  }, []);

  // Compute node/edge highlighting on Search or Node Click
  const { displayNodes, displayEdges } = useMemo(() => {
    const activeSelectedId = selectedNode?.id || selectedNode?.relative_path;

    const outgoingTargets = new Set();
    const incomingSources = new Set();
    const connectedNodeIds = new Set();

    if (activeSelectedId) {
      connectedNodeIds.add(activeSelectedId);

      edges.forEach(e => {
        if (e.source === activeSelectedId) {
          outgoingTargets.add(e.target);
          connectedNodeIds.add(e.target);
        }
        if (e.target === activeSelectedId) {
          incomingSources.add(e.source);
          connectedNodeIds.add(e.source);
        }
      });
    }

    const updatedNodes = nodes.map(node => {
      const isSearchMatch = searchQuery.trim() 
        ? node.id.toLowerCase().includes(searchQuery.toLowerCase()) || 
          (node.data?.relative_path && node.data.relative_path.toLowerCase().includes(searchQuery.toLowerCase()))
        : false;

      const isSelected = activeSelectedId === node.id;
      const isOutgoing = activeSelectedId ? outgoingTargets.has(node.id) : false;
      const isIncoming = activeSelectedId ? incomingSources.has(node.id) : false;
      const isConnected = activeSelectedId ? connectedNodeIds.has(node.id) : true;

      let opacity = 1;
      if (searchQuery.trim()) {
        opacity = isSearchMatch ? 1 : 0.2;
      } else if (activeSelectedId) {
        opacity = isConnected ? 1 : 0.2;
      }

      return {
        ...node,
        data: {
          ...node.data,
          isSelected,
          isSearchMatch,
          isOutgoing,
          isIncoming,
          isConnected,
          opacity,
          layoutDir: layoutDirection
        }
      };
    });

    const updatedEdges = edges.map(edge => {
      const isOutgoingEdge = activeSelectedId && edge.source === activeSelectedId;
      const isIncomingEdge = activeSelectedId && edge.target === activeSelectedId;

      let stroke = '#475569';
      let strokeWidth = 2;
      let opacity = 1;
      let animated = false;

      if (activeSelectedId) {
        if (isOutgoingEdge) {
          stroke = '#ef4444';  // Red preferred route line
          strokeWidth = 3.5;
          opacity = 1;
          animated = true;
        } else if (isIncomingEdge) {
          stroke = '#10b981';
          strokeWidth = 3.5;
          opacity = 1;
          animated = true;
        } else {
          stroke = '#cbd5e1';
          strokeWidth = 1;
          opacity = 0.12;
        }
      }

      return {
        ...edge,
        animated,
        style: {
          ...edge.style,
          stroke,
          strokeWidth,
          opacity
        },
        markerEnd: {
          ...edge.markerEnd,
          color: stroke
        }
      };
    });

    return { displayNodes: updatedNodes, displayEdges: updatedEdges };
  }, [nodes, edges, searchQuery, selectedNode, layoutDirection]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', marginBottom: '2rem' }}>
      
      <div className="status-card" style={{ padding: '1.5rem' }}>
        
        {/* Header Toolbar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <GitFork size={22} style={{ color: 'var(--accent-primary)' }} />
              <span>Interactive Codebase Architecture Map</span>
            </h3>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', width: '220px' }}>
              <Search size={15} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search file path..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.6rem 0.5rem 2rem',
                  fontSize: '0.85rem',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  background: '#ffffff',
                  color: 'var(--text-primary)',
                  outline: 'none',
                  boxShadow: 'var(--shadow-sm)'
                }}
              />
            </div>

            <button
              onClick={toggleLayoutDirection}
              title="Toggle Layout Direction (Left-Right vs Top-Bottom)"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.5rem 0.85rem',
                borderRadius: '9999px',
                border: '1px solid var(--border-color)',
                background: '#ffffff',
                color: 'var(--text-primary)',
                fontSize: '0.825rem',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: 'var(--shadow-sm)',
                transition: 'all 0.2s ease'
              }}
            >
              <ArrowRightLeft size={14} style={{ color: 'var(--accent-primary)' }} />
              <span>{layoutDirection === 'LR' ? 'Left → Right' : 'Top → Bottom'}</span>
            </button>

            <button 
              className="btn-refresh"
              onClick={fetchDependencies}
              disabled={loading}
              style={{ fontSize: '0.825rem' }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              <span>Reload</span>
            </button>
          </div>
        </div>

        {loading && (
          <div style={{ height: '550px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', color: 'var(--text-secondary)' }}>
            <RefreshCw size={28} className="spin" style={{ color: 'var(--accent-primary)' }} />
            <span>Building codebase dependency architecture map...</span>
          </div>
        )}

        {!loading && error && (
          <div style={{ padding: '2rem', textAlign: 'center', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: 'var(--radius-md)' }}>
            <AlertCircle size={32} style={{ color: 'var(--accent-error)', marginBottom: '0.5rem' }} />
            <p style={{ fontWeight: 600, color: 'var(--accent-error)', fontSize: '1rem' }}>{error}</p>
          </div>
        )}

        {!loading && !error && nodes && nodes.length > 0 && (
          <div>
            <div style={{ height: '660px', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', overflow: 'hidden', background: '#f8fafc', position: 'relative' }}>
              
              {/* Instructions Banner & Legend */}
              <div style={{ 
                position: 'absolute', 
                top: '12px', 
                left: '12px', 
                right: '12px', 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                pointerEvents: 'none', 
                zIndex: 5,
                flexWrap: 'wrap',
                gap: '0.5rem'
              }}>
                <div style={{ 
                  background: 'rgba(255, 255, 255, 0.94)', 
                  backdropFilter: 'blur(8px)', 
                  padding: '0.4rem 0.9rem', 
                  borderRadius: '9999px', 
                  border: '1px solid var(--border-color)', 
                  fontSize: '0.78rem', 
                  color: 'var(--text-secondary)', 
                  boxShadow: 'var(--shadow-sm)',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem'
                }}>
                  <span>💡 Drag to Pan • Scroll to Zoom</span>
                  <span style={{ color: 'var(--border-color)' }}>|</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                    Nodes: {nodes.length} • Edges: {edges.length}
                    {edges.length === 0 ? ' (No dependency edges returned by backend)' : ''}
                  </span>
                </div>

                <div style={{ 
                  display: 'flex', 
                  gap: '0.85rem', 
                  background: 'rgba(255, 255, 255, 0.94)', 
                  backdropFilter: 'blur(8px)', 
                  padding: '0.4rem 0.9rem', 
                  borderRadius: '9999px', 
                  border: '1px solid var(--border-color)', 
                  fontSize: '0.75rem', 
                  fontWeight: 700, 
                  boxShadow: 'var(--shadow-sm)',
                  pointerEvents: 'auto'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#ef4444' }}>
                    <span style={{ width: '14px', height: '2px', background: '#ef4444' }}></span> Dependency Route / Active Path
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#475569' }}>
                    <span style={{ width: '14px', height: '2px', background: '#475569' }}></span> Module Link
                  </span>
                </div>
              </div>

              <ReactFlow
                nodes={displayNodes}
                edges={displayEdges}
                nodeTypes={nodeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                onPaneClick={() => setSelectedNode(null)}
                onInit={onInitReactFlow}
                fitView
                fitViewOptions={{ padding: 0.15, includeHiddenNodes: false }}
                minZoom={0.15}
                maxZoom={2.5}
              >
                <Background color="#cbd5e1" gap={16} size={1} />
                <Controls position="bottom-right" style={{ background: '#ffffff', border: '1px solid var(--border-color)', color: 'var(--text-primary)', boxShadow: 'var(--shadow-sm)' }} />
                <MiniMap 
                  nodeColor={(node) => {
                    if (node.data?.has_syntax_error) return '#ef4444';
                    const lang = getLanguageTheme(node.data?.relative_path);
                    return lang.color || '#6366f1';
                  }}
                  maskColor="rgba(248, 250, 252, 0.75)"
                  style={{ background: '#ffffff', border: '1px solid var(--border-color)', borderRadius: '12px' }} 
                />
              </ReactFlow>
            </div>

            {/* Selected Node Inspector */}
            {selectedNode && (
              <div style={{ marginTop: '1.25rem', padding: '1.25rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FileCode size={20} style={{ color: 'var(--accent-primary)' }} />
                    <span style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--text-primary)' }}>{selectedNode.relative_path}</span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '0.15rem 0.55rem', borderRadius: '9999px', background: 'rgba(99, 102, 241, 0.1)', color: '#4338ca' }}>
                      {selectedNode.lines_of_code || 0} LOC
                    </span>
                  </div>
                  <button 
                    onClick={() => setSelectedNode(null)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.1rem' }}
                  >
                    ✕
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', fontSize: '0.85rem' }}>
                  <div>
                    <div style={{ fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>Project Dependencies (Outgoing):</div>
                    {selectedNode.project_dependencies && selectedNode.project_dependencies.length > 0 ? (
                      selectedNode.project_dependencies.map((dep, idx) => (
                        <span key={idx} style={{ display: 'block', color: '#ef4444', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>→ {dep}</span>
                      ))
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>None</span>
                    )}
                  </div>

                  <div>
                    <div style={{ fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>External Libraries Used:</div>
                    {selectedNode.external_libraries && selectedNode.external_libraries.length > 0 ? (
                      selectedNode.external_libraries.map((lib, idx) => (
                        <span key={idx} style={{ display: 'block', color: 'var(--accent-secondary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>📦 {lib}</span>
                      ))
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>None</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* External Libraries */}
      <div className="status-card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Package size={20} style={{ color: 'var(--accent-primary)' }} />
            <span>External Libraries ({graphData?.external_libraries?.length || 0})</span>
          </h3>
        </div>

        {graphData?.external_libraries && graphData.external_libraries.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
            {graphData.external_libraries.map((lib, idx) => (
              <div 
                key={idx} 
                style={{ 
                  padding: '1.15rem 1.25rem', 
                  borderRadius: 'var(--radius-md)', 
                  background: 'var(--bg-secondary)', 
                  border: '1px solid var(--border-color)',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '1.05rem', color: 'var(--text-primary)' }}>{lib.name}</span>
                  <span style={{ 
                    fontSize: '0.725rem', 
                    fontWeight: 700,
                    padding: '0.2rem 0.65rem', 
                    borderRadius: '9999px', 
                    background: lib.type === 'standard_library' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.08)', 
                    color: lib.type === 'standard_library' ? 'var(--accent-success)' : 'var(--accent-primary)',
                    border: lib.type === 'standard_library' ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(244, 63, 94, 0.2)'
                  }}>
                    {lib.type === 'standard_library' ? 'StdLib' : 'Third-Party'}
                  </span>
                </div>

                <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.35rem', color: 'var(--text-primary)' }}>Imported Submodules:</div>
                  <div style={{ maxHeight: '100px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    {lib.imports && lib.imports.length > 0 ? (
                      lib.imports.map((imp, impIdx) => (
                        <span key={impIdx} style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                          • {imp}
                        </span>
                      ))
                    ) : (
                      <span>{lib.top_module}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>No external library dependencies detected.</p>
        )}
      </div>

    </div>
  );
}
