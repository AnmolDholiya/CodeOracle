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
import { getProjectDependencies, formatApiErrorMessage } from '../services/api';
import { 
  GitFork, 
  RefreshCw, 
  Search, 
  FileCode, 
  AlertCircle, 
  Package, 
  ArrowRightLeft,
  Maximize2,
  Layers,
  Sparkles
} from 'lucide-react';

const NODE_WIDTH = 220;
const NODE_HEIGHT = 80;

// Category colors matching Legend
const CATEGORY_THEMES = {
  root: {
    label: 'Root Entry',
    badge: '⚡ Root Entry',
    headerBg: '#FFB800',
    headerColor: '#1E1E2F',
    border: '#1E1E2F',
    glowColor: 'rgba(255, 184, 0, 0.4)'
  },
  module: {
    label: 'Module',
    badge: '📦 Module',
    headerBg: '#8B5CF6',
    headerColor: '#FFFFFF',
    border: '#1E1E2F',
    glowColor: 'rgba(139, 92, 246, 0.4)'
  },
  utility: {
    label: 'Utility',
    badge: '🛠️ Utility',
    headerBg: '#00CC66',
    headerColor: '#FFFFFF',
    border: '#1E1E2F',
    glowColor: 'rgba(0, 204, 102, 0.4)'
  }
};

const getLanguageIcon = (path = '') => {
  const p = path.toLowerCase();
  if (p.endsWith('.py')) return { label: 'Python', icon: '🐍' };
  if (p.endsWith('.tsx') || p.endsWith('.jsx')) return { label: 'React', icon: '⚛️' };
  if (p.endsWith('.ts')) return { label: 'TypeScript', icon: '🔷' };
  if (p.endsWith('.js')) return { label: 'JavaScript', icon: '📜' };
  if (p.endsWith('.json')) return { label: 'JSON', icon: '📋' };
  if (p.endsWith('.yaml') || p.endsWith('.yml')) return { label: 'YAML', icon: '⚙️' };
  return { label: 'File', icon: '📄' };
};

// Custom Matrix Node Component with True Classification Colors
const FileNodeComponent = ({ data }) => {
  const category = (data.node_type || data.nodeData?.type || 'module').toLowerCase();
  const theme = CATEGORY_THEMES[category] || CATEGORY_THEMES.module;
  const lang = getLanguageIcon(data.relative_path);
  
  const isErr = data.has_syntax_error;
  const isSelected = data.isSelected;
  const isSearchMatch = data.isSearchMatch;
  const isOutgoing = data.isOutgoing;
  const isIncoming = data.isIncoming;
  const layoutDir = data.layoutDir || 'LR';

  const handlePosTarget = layoutDir === 'LR' ? Position.Left : Position.Top;
  const handlePosSource = layoutDir === 'LR' ? Position.Right : Position.Bottom;

  let borderColor = '#1E1E2F';
  let headerBg = theme.headerBg;
  let headerColor = theme.headerColor;
  let boxShadow = '3px 3px 0px #1E1E2F';

  if (isSelected) {
    borderColor = '#FF3385';
    boxShadow = '0 0 0 3px #FF3385, 4px 4px 0px #1E1E2F';
  } else if (isOutgoing) {
    borderColor = '#FF3385';
    boxShadow = '0 0 0 2.5px #FF3385, 3px 3px 0px #1E1E2F';
  } else if (isIncoming) {
    borderColor = '#00CC66';
    boxShadow = '0 0 0 2.5px #00CC66, 3px 3px 0px #1E1E2F';
  } else if (isErr) {
    headerBg = '#FF4D4D';
    headerColor = '#FFFFFF';
  } else if (isSearchMatch) {
    borderColor = '#00D8F6';
    boxShadow = '0 0 0 3px #00D8F6, 4px 4px 0px #1E1E2F';
  }

  const folderName = data.relative_path
    ? (data.relative_path.includes('/') ? data.relative_path.substring(0, data.relative_path.lastIndexOf('/')) : '.')
    : '.';

  return (
    <div style={{
      width: `${NODE_WIDTH}px`,
      height: `${NODE_HEIGHT}px`,
      background: '#FFFFFF',
      border: `2.5px solid ${borderColor}`,
      borderRadius: '12px',
      boxShadow: boxShadow,
      display: 'flex',
      flexDirection: 'column',
      position: 'relative',
      cursor: 'pointer',
      boxSizing: 'border-box',
      opacity: data.opacity ?? 1,
      fontFamily: 'var(--font-sans)',
      transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
      overflow: 'hidden'
    }}>
      <Handle 
        type="target" 
        position={handlePosTarget} 
        style={{ background: headerBg, width: 10, height: 10, border: '2px solid #1E1E2F' }} 
      />

      {/* Header Bar with Category Badge & Filename */}
      <div style={{
        background: headerBg,
        color: headerColor,
        padding: '4px 8px',
        fontSize: '11px',
        fontWeight: 800,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '2px solid #1E1E2F'
      }} title={data.relative_path}>
        <span style={{ 
          whiteSpace: 'nowrap', 
          overflow: 'hidden', 
          textOverflow: 'ellipsis', 
          maxWidth: '135px',
          fontFamily: 'var(--font-heading)'
        }}>
          {data.label}
        </span>
        <span style={{ 
          fontSize: '9px', 
          fontWeight: 800, 
          padding: '1px 5px', 
          borderRadius: '9999px', 
          background: 'rgba(0,0,0,0.15)',
          color: headerColor,
          fontFamily: 'var(--font-heading)'
        }}>
          {theme.badge}
        </span>
      </div>

      {/* Middle Row: Language & LOC */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', flex: 1, borderBottom: '1.5px solid #1E1E2F', background: '#FFFFFF' }}>
        <div style={{ borderRight: '1.5px solid #1E1E2F', padding: '3px 6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700, color: 'var(--ink)' }}>
          {lang.icon} {lang.label}
        </div>
        <div style={{ padding: '3px 6px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 800, color: '#FF3385', fontFamily: 'var(--font-mono)' }}>
          {data.lines_of_code || 0} LOC
        </div>
      </div>

      {/* Bottom Row: Folder & Functions */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 0.7fr', background: 'var(--bg-secondary)', fontSize: '9px', fontWeight: 700 }}>
        <div style={{ borderRight: '1.5px solid #1E1E2F', padding: '3px 6px', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={folderName}>
          📁 {folderName}
        </div>
        <div style={{ padding: '3px 6px', textAlign: 'center', color: '#8B5CF6', fontWeight: 800 }}>
          {data.functions_count || 0} fns
        </div>
      </div>

      <Handle 
        type="source" 
        position={handlePosSource} 
        style={{ background: headerBg, width: 10, height: 10, border: '2px solid #1E1E2F' }} 
      />
    </div>
  );
};

const nodeTypes = {
  fileNode: FileNodeComponent
};

// Dagre Automatic Layout Algorithm
export const getLayoutedElements = (rawNodes, rawEdges, direction = 'LR') => {
  if (!rawNodes || rawNodes.length === 0) {
    return { nodes: [], edges: [] };
  }

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ 
    rankdir: direction, 
    nodesep: 60, 
    ranksep: 120,
    marginx: 50,
    marginy: 50
  });

  const nodeMap = new Map();
  rawNodes.forEach(n => {
    nodeMap.set(n.id, n);
    dagreGraph.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  const edgesMap = new Map();

  // 1. Process explicit edges from backend
  (rawEdges || []).forEach(e => {
    if (nodeMap.has(e.source) && nodeMap.has(e.target) && e.source !== e.target) {
      const key = `${e.source}->${e.target}`;
      edgesMap.set(key, { source: e.source, target: e.target });
    }
  });

  // 2. Complement with node.project_dependencies in case edges list was partial
  rawNodes.forEach(n => {
    if (n.project_dependencies && Array.isArray(n.project_dependencies)) {
      n.project_dependencies.forEach(tgt => {
        if (nodeMap.has(tgt) && n.id !== tgt) {
          const key = `${n.id}->${tgt}`;
          if (!edgesMap.has(key)) {
            edgesMap.set(key, { source: n.id, target: tgt });
          }
        }
      });
    }
  });

  const validEdges = Array.from(edgesMap.values());

  validEdges.forEach(e => {
    dagreGraph.setEdge(e.source, e.target);
  });

  // Run Dagre Layout computation
  dagre.layout(dagreGraph);

  // Map computed coordinates onto React Flow nodes
  const layoutedNodes = rawNodes.map(n => {
    const nodeWithPosition = dagreGraph.node(n.id);
    const x = nodeWithPosition ? nodeWithPosition.x - NODE_WIDTH / 2 : 0;
    const y = nodeWithPosition ? nodeWithPosition.y - NODE_HEIGHT / 2 : 0;

    return {
      id: n.id,
      type: 'fileNode',
      data: {
        label: n.label || n.id,
        relative_path: n.relative_path || n.id,
        lines_of_code: n.lines_of_code || 0,
        classes_count: n.classes_count || 0,
        functions_count: n.functions_count || 0,
        has_syntax_error: n.has_syntax_error || false,
        node_type: n.type || 'module',
        nodeData: n,
        layoutDir: direction
      },
      position: { x, y }
    };
  });

  const layoutedEdges = validEdges.map((e, idx) => ({
    id: `edge-${e.source}->${e.target}-${idx}`,
    source: e.source,
    target: e.target,
    type: 'smoothstep',
    animated: false,
    style: {
      stroke: '#1E1E2F',
      strokeWidth: 2.5
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: '#1E1E2F',
      width: 18,
      height: 18
    }
  }));

  return { nodes: layoutedNodes, edges: layoutedEdges };
};

export default function DependencyGraph({ projectId }) {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [layoutDirection, setLayoutDirection] = useState('LR');
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const applyLayout = useCallback((rawNodes, rawEdges, direction) => {
    const { nodes: lNodes, edges: lEdges } = getLayoutedElements(rawNodes, rawEdges, direction);
    setNodes(lNodes);
    setEdges(lEdges);
  }, [setNodes, setEdges]);

  const fetchDependencies = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getProjectDependencies(projectId);
      setGraphData(data);
      applyLayout(data.nodes || [], data.edges || [], layoutDirection);
    } catch (err) {
      console.error('Failed to load dependency graph:', err);
      setError(formatApiErrorMessage(err, 'Unable to load dependency graph. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDependencies();
  }, [projectId]);

  const toggleLayoutDirection = () => {
    const newDir = layoutDirection === 'LR' ? 'TB' : 'LR';
    setLayoutDirection(newDir);
    if (graphData) {
      applyLayout(graphData.nodes || [], graphData.edges || [], newDir);
    }
  };

  const handleFitView = useCallback(() => {
    if (reactFlowInstance) {
      reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
    }
  }, [reactFlowInstance]);

  // Imperative fitView triggered whenever nodes change or graph instance is initialized
  useEffect(() => {
    if (reactFlowInstance && nodes.length > 0) {
      const timer = setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [nodes.length, layoutDirection, reactFlowInstance]);

  const onInitReactFlow = useCallback((instance) => {
    setReactFlowInstance(instance);
    setTimeout(() => {
      instance.fitView({ padding: 0.2, duration: 400 });
    }, 120);
  }, []);

  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node.data?.nodeData || null);
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

      let stroke = '#1E1E2F';
      let strokeWidth = 2.5;
      let opacity = 1;
      let animated = false;

      if (activeSelectedId) {
        if (isOutgoingEdge) {
          stroke = '#FF3385';
          strokeWidth = 3.5;
          opacity = 1;
          animated = true;
        } else if (isIncomingEdge) {
          stroke = '#00CC66';
          strokeWidth = 3.5;
          opacity = 1;
          animated = true;
        } else {
          stroke = '#CBD5E1';
          strokeWidth = 1.5;
          opacity = 0.15;
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', marginBottom: '2.5rem' }}>
      
      <div className="status-card" style={{ padding: '1.75rem' }}>
        
        {/* Header Toolbar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.6rem', fontFamily: 'var(--font-heading)' }}>
              <GitFork size={24} style={{ color: 'var(--accent-primary)', filter: 'drop-shadow(1.5px 1.5px 0px var(--ink))' }} />
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
                  background: '#FFFFFF',
                  color: 'var(--text-primary)'
                }}
              />
            </div>

            <button
              onClick={toggleLayoutDirection}
              className="btn-refresh"
              title="Toggle Layout Direction (Left-Right vs Top-Bottom)"
              style={{
                background: '#FFFFFF',
                color: 'var(--ink)',
                fontSize: '0.85rem',
                padding: '0.5rem 0.95rem'
              }}
            >
              <ArrowRightLeft size={15} style={{ color: 'var(--accent-primary)' }} />
              <span>{layoutDirection === 'LR' ? 'Left → Right' : 'Top → Bottom'}</span>
            </button>

            <button
              onClick={handleFitView}
              className="btn-refresh"
              title="Recenter & Fit View"
              style={{
                background: '#FFFFFF',
                color: 'var(--ink)',
                fontSize: '0.85rem',
                padding: '0.5rem 0.95rem'
              }}
            >
              <Maximize2 size={15} style={{ color: 'var(--accent-purple)' }} />
              <span>Fit View</span>
            </button>

            <button 
              className="btn-refresh"
              onClick={fetchDependencies}
              disabled={loading}
              style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              <span>Reload</span>
            </button>
          </div>
        </div>

        {loading && (
          <div style={{ height: '550px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', color: 'var(--text-secondary)' }}>
            <RefreshCw size={28} className="spin" style={{ color: 'var(--accent-primary)' }} />
            <span style={{ fontWeight: 700, fontFamily: 'var(--font-heading)' }}>Building codebase dependency architecture map…</span>
          </div>
        )}

        {!loading && error && (
          <div style={{ padding: '2rem', textAlign: 'center', background: '#FFF0F0', border: '2.5px solid var(--accent-error)', borderRadius: 'var(--radius-md)', boxShadow: '3px 3px 0px var(--accent-error)' }}>
            <AlertCircle size={32} style={{ color: 'var(--accent-error)', marginBottom: '0.5rem' }} />
            <p style={{ fontWeight: 700, color: 'var(--accent-error)', fontSize: '1rem' }}>{error}</p>
          </div>
        )}

        {!loading && !error && nodes && nodes.length > 0 && (
          <div>
            <div style={{ height: '660px', borderRadius: 'var(--radius-lg)', border: '2.5px solid var(--ink)', overflow: 'hidden', background: '#F8FAFC', position: 'relative', boxShadow: '4px 4px 0px var(--ink)' }}>
              
              {/* Instructions Banner & Categorization Legend */}
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
                  background: '#FFFFFF', 
                  padding: '0.4rem 0.9rem', 
                  borderRadius: 'var(--radius-pill)', 
                  border: '2px solid var(--ink)', 
                  fontSize: '0.8rem', 
                  color: 'var(--ink)', 
                  boxShadow: '2px 2px 0px var(--ink)',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem',
                  fontFamily: 'var(--font-heading)'
                }}>
                  <span>💡 Drag to Pan • Scroll to Zoom</span>
                  <span style={{ color: 'var(--ink)' }}>|</span>
                  <span style={{ color: 'var(--accent-primary)', fontWeight: 800 }}>
                    Nodes: {nodes.length} • Edges: {edges.length}
                  </span>
                </div>

                {/* Legend for Root, Module, Utility */}
                <div style={{ 
                  display: 'flex', 
                  gap: '0.65rem', 
                  background: '#FFFFFF', 
                  padding: '0.4rem 0.9rem', 
                  borderRadius: 'var(--radius-pill)', 
                  border: '2px solid var(--ink)', 
                  fontSize: '0.78rem', 
                  fontWeight: 800, 
                  boxShadow: '2px 2px 0px var(--ink)',
                  pointerEvents: 'auto',
                  fontFamily: 'var(--font-heading)'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#1E1E2F' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#FFB800', border: '1.5px solid #1E1E2F' }}></span> Root Entry
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#1E1E2F' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#8B5CF6', border: '1.5px solid #1E1E2F' }}></span> Modules
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#1E1E2F' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#00CC66', border: '1.5px solid #1E1E2F' }}></span> Utilities
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
                fitViewOptions={{ padding: 0.2, includeHiddenNodes: false }}
                minZoom={0.15}
                maxZoom={2.5}
              >
                <Background color="#1E1E2F" gap={20} size={1.2} style={{ opacity: 0.15 }} />
                <Controls position="bottom-right" style={{ background: '#FFFFFF', border: '2px solid var(--ink)', borderRadius: '10px', boxShadow: '3px 3px 0px var(--ink)' }} />
                <MiniMap 
                  nodeColor={(node) => {
                    if (node.data?.has_syntax_error) return '#FF4D4D';
                    const cat = (node.data?.node_type || 'module').toLowerCase();
                    return CATEGORY_THEMES[cat]?.headerBg || '#8B5CF6';
                  }}
                  maskColor="rgba(248, 250, 252, 0.7)"
                  style={{ background: '#FFFFFF', border: '2.5px solid var(--ink)', borderRadius: '12px', boxShadow: '3px 3px 0px var(--ink)' }} 
                />
              </ReactFlow>
            </div>

            {/* Selected Node Inspector */}
            {selectedNode && (
              <div style={{ marginTop: '1.5rem', padding: '1.5rem', background: 'var(--bg-secondary)', border: '2.5px solid var(--ink)', borderRadius: 'var(--radius-md)', boxShadow: '4px 4px 0px var(--ink)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                    <FileCode size={22} style={{ color: 'var(--accent-primary)' }} />
                    <span style={{ fontWeight: 800, fontSize: '1.15rem', color: 'var(--text-primary)', fontFamily: 'var(--font-heading)' }}>{selectedNode.relative_path}</span>
                    <span style={{ 
                      fontSize: '0.78rem', 
                      fontWeight: 800, 
                      padding: '0.2rem 0.65rem', 
                      borderRadius: 'var(--radius-pill)', 
                      background: CATEGORY_THEMES[selectedNode.type?.toLowerCase()]?.headerBg || '#8B5CF6',
                      color: CATEGORY_THEMES[selectedNode.type?.toLowerCase()]?.headerColor || '#FFFFFF',
                      border: '1.5px solid var(--ink)',
                      boxShadow: '1.5px 1.5px 0px var(--ink)'
                    }}>
                      {CATEGORY_THEMES[selectedNode.type?.toLowerCase()]?.badge || '📦 Module'}
                    </span>
                    <span style={{ fontSize: '0.78rem', fontWeight: 800, padding: '0.2rem 0.65rem', borderRadius: 'var(--radius-pill)', background: '#FFFFFF', color: '#FF3385', border: '1.5px solid var(--ink)', fontFamily: 'var(--font-mono)' }}>
                      {selectedNode.lines_of_code || 0} LOC
                    </span>
                  </div>
                  <button 
                    onClick={() => setSelectedNode(null)}
                    style={{ background: '#FFFFFF', border: '2px solid var(--ink)', borderRadius: '50%', width: '28px', height: '28px', color: 'var(--ink)', cursor: 'pointer', fontWeight: 800, boxShadow: '2px 2px 0px var(--ink)' }}
                  >
                    ✕
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', fontSize: '0.88rem' }}>
                  <div style={{ background: '#FFFFFF', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '2px solid var(--ink)' }}>
                    <div style={{ fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.5rem', fontFamily: 'var(--font-heading)' }}>
                      ⚡ Project Dependencies (Outgoing):
                    </div>
                    {selectedNode.project_dependencies && selectedNode.project_dependencies.length > 0 ? (
                      selectedNode.project_dependencies.map((dep, idx) => (
                        <span key={idx} style={{ display: 'block', color: '#FF3385', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.85rem' }}>→ {dep}</span>
                      ))
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>None (Leaf file)</span>
                    )}
                  </div>

                  <div style={{ background: '#FFFFFF', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '2px solid var(--ink)' }}>
                    <div style={{ fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.5rem', fontFamily: 'var(--font-heading)' }}>
                      📦 External Libraries Used:
                    </div>
                    {selectedNode.external_libraries && selectedNode.external_libraries.length > 0 ? (
                      selectedNode.external_libraries.map((lib, idx) => (
                        <span key={idx} style={{ display: 'block', color: '#FFB800', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.85rem' }}>📦 {lib}</span>
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

      {/* External Libraries Section */}
      <div className="status-card" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)' }}>
            <Package size={22} style={{ color: 'var(--accent-primary)', filter: 'drop-shadow(1.5px 1.5px 0px var(--ink))' }} />
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
                  border: '2.5px solid var(--ink)',
                  boxShadow: '3px 3px 0px var(--ink)',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
                  <span style={{ fontWeight: 800, fontSize: '1.05rem', color: 'var(--text-primary)', fontFamily: 'var(--font-heading)' }}>{lib.name}</span>
                  <span style={{ 
                    fontSize: '0.75rem', 
                    fontWeight: 800,
                    padding: '0.2rem 0.65rem', 
                    borderRadius: 'var(--radius-pill)', 
                    background: lib.type === 'standard_library' ? '#00CC66' : '#FF3385', 
                    color: '#FFFFFF',
                    border: '1.5px solid var(--ink)'
                  }}>
                    {lib.type === 'standard_library' ? 'StdLib' : 'Third-Party'}
                  </span>
                </div>

                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  <div style={{ fontWeight: 800, marginBottom: '0.35rem', color: 'var(--text-primary)' }}>Imported Submodules:</div>
                  <div style={{ maxHeight: '100px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    {lib.imports && lib.imports.length > 0 ? (
                      lib.imports.map((imp, impIdx) => (
                        <span key={impIdx} style={{ fontFamily: 'var(--font-mono)', color: 'var(--ink)', fontWeight: 600 }}>
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
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 600 }}>No external library dependencies detected.</p>
        )}
      </div>

    </div>
  );
}
