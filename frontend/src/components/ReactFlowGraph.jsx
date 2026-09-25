/**
 * ReactFlowGraph.jsx — Clean White-Theme Intelligence Graph Canvas.
 * Matches reference screenshots: circular teal/type-colored nodes, thin dark edges,
 * labels below nodes, floating action toolbar, bottom zoom bar, and rich click interactions.
 */

import React, {
  forwardRef, useCallback, useEffect, useImperativeHandle,
  useRef, useState,
} from "react";
import {
  ReactFlow, Background, useNodesState, useEdgesState,
  useReactFlow, ReactFlowProvider, MarkerType, Handle, Position,
  BaseEdge,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import {
  Network, Globe, MapPin, Box, CalendarClock, Mail, Building2,
  Layers, Search, Plus, Trash2, Edit3, Merge, EyeOff,
  RotateCcw, Eye, Maximize, GitFork, Crosshair, Copy,
  BookmarkPlus, ArrowRight, CheckCircle2, ChevronRight, ChevronLeft,
  AlignLeft, LayoutGrid, Sun, Moon,
  Phone, Car, User, FileText, CreditCard, DollarSign,
} from "lucide-react";
import { springLayout, directionalLayout } from "../lib/graphAnalysis";

import "@xyflow/react/dist/style.css";

// ─── Color Maps ───────────────────────────────────────────────────────────────
export const TYPE_COLOR = {
  person:       "#5b9bd5",
  location:     "#ff9800",
  object:       "#ab47bc",
  vehicle:      "#26c6da",
  event:        "#42a5f5",
  domain:       "#ef5350",
  ip:           "#26a69a",
  email:        "#ec407a",
  org:          "#7e57c2",
  organization: "#7e57c2",
  phone:        "#29b6f6",
  account:      "#66bb6a",
  upi:          "#ffa726",
  bank:         "#66bb6a",
};

export const TYPE_ICON = {
  person:       Network,
  location:     MapPin,
  phone:        Phone,
  vehicle:      Car,
  object:       Box,
  event:        CalendarClock,
  case:         FileText,
  domain:       Globe,
  ip:           Layers,
  email:        Mail,
  org:          Building2,
  organization: Building2,
  account:      CreditCard,
  upi:          CreditCard,
  bank:         CreditCard,
};

export const COMMUNITY_PALETTE = [
  "#5b9bd5", "#ef5350", "#ff9800", "#ab47bc",
  "#66bb6a", "#26c6da", "#ec407a", "#7e57c2",
];

// Node geometry
const CIRCLE = 38;   // Circle diameter in px (clean disc with centered SVG icon)
const NODE_W = 90;   // Bounding box width for layout calculations
const NODE_H = 65;   // Bounding box height

// ─── Dagre Layout ─────────────────────────────────────────────────────────────
function applyDagre(nodes, edges, rankdir = "LR") {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir, nodesep: 50, ranksep: 85 });
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const { x, y } = g.node(n.id);
    return { ...n, position: { x: x - CIRCLE / 2, y: y - CIRCLE / 2 } };
  });
}

// ─── Custom Circular Node with SVG Icon ───────────────────────────────────────
function CleanCircularNode({ data = {}, selected }) {
  const hex = data?.hexColor || "#5b9bd5";
  const isSelected = selected || data?.isSelected;
  const isNeighbor = data?.isNeighbor;
  const isDimmed = data?.isDimmed && !isSelected && !isNeighbor;
  const isPath = data?.isPath;
  const isDark = data?.theme === "dark";

  const ringColor = isSelected ? (isDark ? "#81d4fa" : "#1976d2") : isPath ? "#ff9800" : isNeighbor ? "#5b9bd5" : "transparent";
  const ringW = (isSelected || isPath) ? 4 : isNeighbor ? 3 : 0;

  const nodeType = (data?.type || "").toLowerCase();
  const Icon = TYPE_ICON[nodeType] || (nodeType.includes("phone") ? Phone : nodeType.includes("loc") ? MapPin : nodeType.includes("veh") ? Car : nodeType.includes("org") ? Building2 : Network);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 3,
        position: "relative",
        width: CIRCLE,
        overflow: "visible",
      }}
    >
      {/* Circle Node with Type SVG Icon */}
      <div
        className={`crimenet-node-shell ${isSelected ? "is-selected" : ""} ${isPath ? "is-path" : ""} ${isNeighbor ? "is-neighbor" : ""}`}
        style={{
          width: CIRCLE,
          height: CIRCLE,
          borderRadius: "50%",
          background: isSelected ? (isDark ? "#1565c0" : "#1976d2") : hex,
          border: isSelected ? "1px solid #64b5f6" : "1px solid rgba(255, 255, 255, 0.08)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: isDimmed ? 0.12 : 1,
          transition: "all 0.2s ease",
          boxShadow: ringW
            ? `0 0 0 ${ringW}px ${ringColor}88, 0 2px 8px rgba(0,0,0,0.15)`
            : "0 1px 4px rgba(0,0,0,0.12)",
          cursor: "pointer",
          flexShrink: 0,
          position: "relative",
          zIndex: 5,
        }}
      >
        {/* Centered SVG Icon for Node Type */}
        {Icon && (
          <Icon
            size={18}
            color="#ffffff"
            strokeWidth={2.2}
            style={{ pointerEvents: "none", flexShrink: 0 }}
          />
        )}
        {/* Centered Handles */}
        <Handle
          type="target"
          position={Position.Top}
          id="target"
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: 1,
            height: 1,
            opacity: 0,
            pointerEvents: "none",
            border: "none",
            background: "transparent",
          }}
        />
        <Handle
          type="source"
          position={Position.Bottom}
          id="source"
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: 1,
            height: 1,
            opacity: 0,
            pointerEvents: "none",
            border: "none",
            background: "transparent",
          }}
        />
      </div>

      {/* Clean Label Below Node — matching reference image style */}
      {data?.showLabel !== false && (
        <span
          style={{
            fontSize: 10.5,
            fontWeight: isSelected ? 700 : 500,
            color: isDimmed
              ? (isDark ? "#64748b" : "#94a3b8")
              : isSelected
              ? (isDark ? "#60a5fa" : "#2563eb")
              : (isDark ? "#f1f5f9" : "#1e293b"),
            textAlign: "center",
            width: "max-content",
            maxWidth: 105,
            lineHeight: 1.15,
            userSelect: "none",
            pointerEvents: "none",
            zIndex: 6,
            textShadow: isDark ? "0 1px 2px #000" : "0 1px 2px #fff",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {data?.label || ""}
        </span>
      )}
    </div>
  );
}

const nodeTypes = { cleanNode: CleanCircularNode };

// ─── Custom Curved Edge with Arrow ────────────────────────────────────────────
function CurvedArrowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  style = {},
  markerEnd,
  data,
}) {
  // Guard against missing/NaN coordinates during mount or layout transitions
  if (
    sourceX == null ||
    sourceY == null ||
    targetX == null ||
    targetY == null ||
    Number.isNaN(sourceX) ||
    Number.isNaN(sourceY) ||
    Number.isNaN(targetX) ||
    Number.isNaN(targetY)
  ) {
    return null;
  }

  const offset = data?.curvatureOffset || 0;
  const nodeRadius = 19; // CIRCLE / 2 (38 / 2)

  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const dist = Math.hypot(dx, dy) || 1;

  let edgePath;
  if (dist <= nodeRadius * 2 + 5) {
    if (offset === 0) {
      edgePath = `M ${sourceX} ${sourceY} L ${targetX} ${targetY}`;
    } else {
      const mx = (sourceX + targetX) / 2;
      const my = (sourceY + targetY) / 2;
      const nx = -dy / dist;
      const ny = dx / dist;
      const cx = mx + nx * offset;
      const cy = my + ny * offset;
      edgePath = `M ${sourceX} ${sourceY} Q ${cx} ${cy} ${targetX} ${targetY}`;
    }
  } else if (offset === 0) {
    const ux = dx / dist;
    const uy = dy / dist;
    const sx = sourceX + ux * nodeRadius;
    const sy = sourceY + uy * nodeRadius;
    const tx = targetX - ux * (nodeRadius + 2);
    const ty = targetY - uy * (nodeRadius + 2);
    edgePath = `M ${sx} ${sy} L ${tx} ${ty}`;
  } else {
    const mx = (sourceX + targetX) / 2;
    const my = (sourceY + targetY) / 2;
    const nx = -dy / dist;
    const ny = dx / dist;
    const cx = mx + nx * offset;
    const cy = my + ny * offset;

    const sdx = cx - sourceX;
    const sdy = cy - sourceY;
    const sDist = Math.hypot(sdx, sdy) || 1;
    const sx = sourceX + (sdx / sDist) * nodeRadius;
    const sy = sourceY + (sdy / sDist) * nodeRadius;

    const tdx = targetX - cx;
    const tdy = targetY - cy;
    const tDist = Math.hypot(tdx, tdy) || 1;
    const tx = targetX - (tdx / tDist) * (nodeRadius + 2);
    const ty = targetY - (tdy / tDist) * (nodeRadius + 2);

    edgePath = `M ${sx} ${sy} Q ${cx} ${cy} ${tx} ${ty}`;
  }

  return (
    <>
      {/* Invisible wider hit area for effortless clicking of the arrow / line */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={18}
        className="react-flow__edge-interaction"
        style={{ cursor: "pointer" }}
      />
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          cursor: "pointer",
          transition: "stroke 0.2s ease, stroke-width 0.2s ease, opacity 0.2s ease",
        }}
        markerEnd={markerEnd}
      />
    </>
  );
}

const edgeTypes = { curvedArrow: CurvedArrowEdge };

// ─── Context Menu ─────────────────────────────────────────────────────────────
function ContextMenu({ menu, onCenter, onDetails, onExpand, onFindPath, onFinding, onExclude, onCopy, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [onClose]);

  if (!menu) return null;
  const items = [
    { icon: Crosshair,    label: "Center on canvas",    action: onCenter },
    { icon: GitFork,      label: "Expand 1-hop",        action: onExpand },
    { icon: ChevronRight, label: "View details",        action: onDetails },
    { icon: ArrowRight,   label: "Find path from here", action: onFindPath },
    { icon: BookmarkPlus, label: "Add to intelligence", action: onFinding },
    null,
    { icon: EyeOff,       label: "Exclude node",        action: onExclude },
    { icon: Copy,         label: "Copy ID",             action: onCopy },
  ];

  return (
    <div ref={ref} className="ctx-menu" style={{ left: menu.x, top: menu.y }}>
      {items.map((item, i) =>
        item === null ? <div key={`s${i}`} className="ctx-sep" /> : (
          <div key={item.label} className="ctx-item"
            onClick={() => { item.action?.(); onClose(); }}>
            <item.icon size={13} />
            {item.label}
          </div>
        )
      )}
    </div>
  );
}

// ─── Inner Graph Component ────────────────────────────────────────────────────
const ReactFlowInner = forwardRef(function ReactFlowInner(
  {
    nodes: rawNodes = [],
    edges: rawEdges = [],
    colorMode = "type",
    communityOf,
    centralityOf,
    selectedId,
    selectedIds = [],
    pathIds,
    visibleTypes = {},
    showLabels = true,
    showEdgeLabels = false,
    layoutMode = "force",
    setLayoutMode,
    degreeMap = {},
    onSelect,
    onContextAction,
    onExpandNeighbors,
    onExcludeNode,
    onShowAllNodes,
    onClearView,
    onEditElement,
    onAddElement,
    onDeleteElement,
    onMergeElements,
    onOpenSearch,
    statusMessage,
    leftSidebarCollapsed,
    onToggleLeftSidebar,
    theme = "light",
    onSelectEdge,
    onToggleTheme,
  },
  ref
) {
  const { fitView, zoomIn, zoomOut, setCenter, getNode } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedEdgeId, setSelectedEdgeId] = useState(null);
  const [contextMenu, setContextMenu] = useState(null);
  const [tooltip, setTooltip] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(100);

  // Expose methods to parent
  useImperativeHandle(ref, () => ({
    fit: () => fitView({ padding: 0.12, duration: 350 }),
    zoomBy: (f) => (f > 1 ? zoomIn({ duration: 200 }) : zoomOut({ duration: 200 })),
    center: (id) => {
      const n = getNode(id);
      if (n) setCenter(n.position.x + CIRCLE / 2, n.position.y + CIRCLE / 2, { zoom: 1.6, duration: 350 });
      else fitView({ padding: 0.12, duration: 350 });
    },
    getNodeIds: () => nodes.map((n) => n.id),
  }));

  // Resolve node color
  const resolveHex = useCallback((node) => {
    if (colorMode === "community" && communityOf?.[node.id] != null) {
      return COMMUNITY_PALETTE[communityOf[node.id] % COMMUNITY_PALETTE.length];
    }
    if (colorMode === "centrality" && centralityOf?.[node.id] != null) {
      const t = centralityOf[node.id];
      return `rgb(${Math.round(84 + t * 140)}, ${Math.round(179 - t * 80)}, ${Math.round(153 - t * 100)})`;
    }
    const cleanType = (node.type || "person").toLowerCase();
    return TYPE_COLOR[cleanType] || "#54b399";
  }, [colorMode, communityOf, centralityOf]);

  // Compute 1-hop neighbors of selected node(s)
  const neighborSet = React.useMemo(() => {
    const targets = new Set();
    if (selectedId) targets.add(selectedId);
    if (selectedIds && selectedIds.length > 0) {
      selectedIds.forEach((id) => targets.add(id));
    }
    if (targets.size === 0) return new Set();

    const s = new Set();
    rawEdges.forEach((e) => {
      if (targets.has(e.source)) s.add(e.target);
      if (targets.has(e.target)) s.add(e.source);
    });
    return s;
  }, [selectedId, selectedIds, rawEdges]);

  // Build & layout nodes and edges
  useEffect(() => {
    const visNodes = rawNodes.filter((n) => visibleTypes[n.type] !== false);
    const visIds = new Set(visNodes.map((n) => n.id));
    const targetSet = new Set(selectedIds?.length ? selectedIds : (selectedId ? [selectedId] : []));
    const hasSelection = targetSet.size > 0;
    const pathSet = new Set(pathIds || []);

    const visEdges = rawEdges.filter((e) => visIds.has(e.source) && visIds.has(e.target));

    // Group edges between same node pair to calculate curved offsets
    const pairGroups = new Map();
    visEdges.forEach((e) => {
      const key = [e.source, e.target].sort().join("___");
      if (!pairGroups.has(key)) pairGroups.set(key, []);
      pairGroups.get(key).push(e);
    });

    const edgeOffsetMap = new Map();
    pairGroups.forEach((groupEdges, key) => {
      const n = groupEdges.length;
      const [firstNode] = key.split("___");
      groupEdges.forEach((e, idx) => {
        const edgeKey = e.id || `${e.source}__${e.target}__${idx}`;
        if (n === 1) {
          edgeOffsetMap.set(edgeKey, 0);
        } else {
          const step = 28;
          let offset = (idx - (n - 1) / 2) * step;
          if (e.source !== firstNode) offset = -offset;
          edgeOffsetMap.set(edgeKey, offset);
        }
      });
    });

    // Check if an edge is selected
    const selectedEdgeObj = visEdges.find((e, idx) => (e.id || `${e.source}__${e.target}__${idx}`) === selectedEdgeId);
    const edgeConnectedNodeIds = selectedEdgeObj
      ? new Set([selectedEdgeObj.source, selectedEdgeObj.target])
      : new Set();
    const hasAnySelection = hasSelection || selectedEdgeObj != null;

    const rfNodes = visNodes.map((n) => {
      const isConnectedToSelectedEdge = edgeConnectedNodeIds.has(n.id);
      const isSelected = targetSet.has(n.id) || isConnectedToSelectedEdge;
      const isNeighbor = neighborSet.has(n.id);
      const isPath = pathSet.has(n.id);
      const isDimmed = hasAnySelection ? (!isSelected && !isNeighbor && !isPath) : (pathIds?.length ? !isPath : false);

      return {
        id: n.id,
        type: "cleanNode",
        position: { x: 0, y: 0 },
        data: {
          label: n.label,
          type: n.type,
          hexColor: resolveHex(n),
          isSelected,
          isNeighbor,
          isDimmed,
          isPath,
          showLabel: showLabels,
          degree: degreeMap[n.id] ?? 0,
          rawNode: n,
          theme,
        },
      };
    });

    const rfEdges = visEdges.map((e, idx) => {
      const edgeKey = e.id || `${e.source}__${e.target}__${idx}`;
      const isThisEdgeSelected = edgeKey === selectedEdgeId;
      const connectsSelected = targetSet.size > 0 && (targetSet.has(e.source) || targetSet.has(e.target));
      const onPath = pathIds && pathSet.has(e.source) && pathSet.has(e.target);
      const isDimmed = hasAnySelection && !isThisEdgeSelected && !connectsSelected && !onPath;

      const highlightColor = theme === "dark" ? "#81d4fa" : "#1976d2";
      const defaultColor = theme === "dark" ? "#555555" : "#bbbbbb";
      const edgeColor = onPath ? "#ff9800" : (isThisEdgeSelected || connectsSelected) ? highlightColor : defaultColor;

      return {
        id: edgeKey,
        source: e.source,
        target: e.target,
        label: showEdgeLabels ? (e.label || e.type) : undefined,
        type: "curvedArrow",
        data: {
          curvatureOffset: edgeOffsetMap.get(edgeKey) || 0,
          rawEdge: e,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: edgeColor,
          width: isThisEdgeSelected ? 12 : 9,
          height: isThisEdgeSelected ? 12 : 9,
        },
        style: {
          stroke: edgeColor,
          strokeWidth: isThisEdgeSelected ? 3 : onPath ? 2.2 : connectsSelected ? 1.8 : 1.2,
          opacity: isDimmed ? 0.08 : onPath ? 0.95 : (isThisEdgeSelected || connectsSelected) ? 0.9 : (theme === "dark" ? 0.62 : 0.58),
          filter: isThisEdgeSelected
            ? `drop-shadow(0 0 3px ${theme === "dark" ? "rgba(79, 195, 247, 0.35)" : "rgba(25, 118, 210, 0.25)"})`
            : undefined,
        },
        labelStyle: { fill: theme === "dark" ? "#aaaaaa" : "#555555", fontSize: 9, fontWeight: 500 },
        labelBgStyle: { fill: theme === "dark" ? "#1a1a1a" : "#ffffff", fillOpacity: 0.9 },
      };
    });

    // Layout
    let laid;
    if (layoutMode === "dagre-tb") {
      const positions = directionalLayout(visNodes, visEdges, "TB", {
        width: 1050,
        height: 700,
        iterations: 160,
      });
      laid = rfNodes.map((n) => ({
        ...n,
        position: positions[n.id] ?? { x: Math.random() * 500, y: Math.random() * 350 },
      }));
    } else if (layoutMode === "dagre") {
      const positions = directionalLayout(visNodes, visEdges, "LR", {
        width: 1050,
        height: 700,
        iterations: 160,
      });
      laid = rfNodes.map((n) => ({
        ...n,
        position: positions[n.id] ?? { x: Math.random() * 500, y: Math.random() * 350 },
      }));
    } else {
      const positions = springLayout(visNodes, visEdges, {
        width: 1050,
        height: 700,
        iterations: 180,
      });
      laid = rfNodes.map((n) => ({
        ...n,
        position: positions[n.id] ?? { x: Math.random() * 500, y: Math.random() * 350 },
      }));
    }

    setNodes(laid);
    setEdges(rfEdges);
    setTimeout(() => fitView({ padding: 0.15, duration: 320 }), 90);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawNodes, rawEdges, visibleTypes, colorMode, communityOf, centralityOf,
      selectedId, selectedIds, pathIds, showLabels, showEdgeLabels, layoutMode, degreeMap, neighborSet, selectedEdgeId]);

  // Node clicks
  const onNodeClick = useCallback((e, n) => {
    setSelectedEdgeId(null);
    onSelectEdge?.(null);
    const isMulti = e?.shiftKey || e?.ctrlKey || e?.metaKey;
    onSelect?.(n.id, isMulti);
  }, [onSelect, onSelectEdge]);

  const onEdgeClick = useCallback((e, edge) => {
    e.stopPropagation();
    setSelectedEdgeId((prev) => {
      const next = prev === edge.id ? null : edge.id;
      const raw = next ? (edge.data?.rawEdge || edge) : null;
      onSelectEdge?.(raw);
      return next;
    });
  }, [onSelectEdge]);

  const onNodeDoubleClick = useCallback((_, n) => {
    onSelect?.(n.id);
    const nodeObj = getNode(n.id);
    if (nodeObj) {
      setCenter(nodeObj.position.x + CIRCLE / 2, nodeObj.position.y + CIRCLE / 2, { zoom: 1.8, duration: 350 });
    }
  }, [getNode, onSelect, setCenter]);

  const onPaneClick = useCallback(() => {
    onSelect?.(null);
    setSelectedEdgeId(null);
    onSelectEdge?.(null);
    setContextMenu(null);
    setTooltip(null);
  }, [onSelect, onSelectEdge]);

  const onNodeContextMenu = useCallback((e, n) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, nodeId: n.id });
    onSelect?.(n.id);
  }, [onSelect]);

  // Hover tooltip
  const onNodeMouseEnter = useCallback((e, n) => {
    const raw = n.data.rawNode;
    setTooltip({
      x: e.clientX + 12,
      y: e.clientY + 12,
      label: n.data.label,
      type: n.data.type,
      degree: n.data.degree,
      risk: raw?.risk,
    });
  }, []);

  const onNodeMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  // Update zoom percentage on viewport change
  const onMove = useCallback((_, viewport) => {
    setZoomLevel(Math.round(viewport.zoom * 100));
  }, []);

  return (
    <div className="graph-stage" style={{ width: "100%", height: "100%", position: "relative" }}>


      {/* ─── Vertical Action Toolbar (Right Side) ─────────────────────────── */}
      <div className="floating-action-toolbar">
        {/* Graph Layout Switcher (Force, LR, TB) */}
        <div className="toolbar-group">
          <button
            className={`layout-toggle-btn ${layoutMode === "force" ? "active" : ""}`}
            onClick={() => setLayoutMode?.("force")}
            title="Force-directed spring layout"
          >
            <Layers size={11} /> Force
          </button>
          <button
            className={`layout-toggle-btn ${layoutMode === "dagre" ? "active" : ""}`}
            onClick={() => setLayoutMode?.("dagre")}
            title="Left-to-Right hierarchical layout"
          >
            <AlignLeft size={11} /> LR
          </button>
          <button
            className={`layout-toggle-btn ${layoutMode === "dagre-tb" ? "active" : ""}`}
            onClick={() => setLayoutMode?.("dagre-tb")}
            title="Top-to-Bottom hierarchical layout"
          >
            <LayoutGrid size={11} /> TB
          </button>
        </div>

        {/* Search */}
        <button
          className="action-btn neutral"
          onClick={() => (onOpenSearch ? onOpenSearch() : onContextAction?.("search"))}
        >
          <Search size={12} /> Search
        </button>

        <div className="toolbar-sep-h" />

        {/* Rose outline buttons */}
        <button className="action-btn rose" onClick={onEditElement}>
          <Edit3 size={12} /> Edit Element
        </button>
        <button className="action-btn rose" onClick={onAddElement}>
          <Plus size={12} /> Add Element
        </button>
        <button className="action-btn rose" onClick={onDeleteElement}>
          <Trash2 size={12} /> Delete Elements
        </button>
        <button className="action-btn rose" onClick={onMergeElements}>
          <Merge size={12} /> Merge Elements
        </button>

        <div className="toolbar-sep-h" />

        {/* Green outline buttons */}
        <button className="action-btn green" onClick={() => onExcludeNode?.(selectedId)}>
          <EyeOff size={12} /> Exclude Elements
        </button>
        <button className="action-btn green" onClick={onClearView}>
          <RotateCcw size={12} /> Clear View
        </button>
        <button className="action-btn green" onClick={onShowAllNodes}>
          <Eye size={12} /> Show All Nodes
        </button>
        <button className="action-btn green" onClick={() => fitView({ padding: 0.1, duration: 350 })}>
          <Maximize size={12} /> Expand All Nodes
        </button>
        <button className="action-btn green" onClick={() => onExpandNeighbors?.()}>
          <GitFork size={12} /> Expand Node(s)
        </button>

        <div className="toolbar-sep-h" />

        {/* Theme Toggle (Light / Dark) */}
        <button
          className="action-btn neutral"
          onClick={onToggleTheme}
          title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        >
          {theme === "dark" ? <Sun size={12} /> : <Moon size={12} />}
          {theme === "dark" ? "Light Mode" : "Dark Mode"}
        </button>
      </div>

      {/* Main Graph Canvas */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        onNodeContextMenu={onNodeContextMenu}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseLeave={onNodeMouseLeave}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        onMove={onMove}
        minZoom={0.2}
        maxZoom={3.5}
        defaultEdgeOptions={{ type: "curvedArrow" }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color={theme === "dark" ? "#222222" : "#e0ddd8"} gap={32} size={1} />
      </ReactFlow>



      {/* Bottom Right Zoom Control Bar (- 123% + FIT CTR) */}
      <div className="zoom-control-bar">
        <button className="zoom-btn" onClick={() => zoomOut({ duration: 200 })} title="Zoom Out" aria-label="Zoom out">
          -
        </button>
        <span className="zoom-val">{zoomLevel}%</span>
        <button className="zoom-btn" onClick={() => zoomIn({ duration: 200 })} title="Zoom In" aria-label="Zoom in">
          +
        </button>
        <button className="zoom-text-btn" onClick={() => fitView({ padding: 0.14, duration: 300 })}>
          Fit
        </button>
        <button className="zoom-text-btn" onClick={() => {
          if (selectedId) {
            const n = getNode(selectedId);
            if (n) setCenter(n.position.x + CIRCLE / 2, n.position.y + CIRCLE / 2, { zoom: 1.6, duration: 300 });
          } else {
            fitView({ padding: 0.14, duration: 300 });
          }
        }}>
          Ctr
        </button>
      </div>

      {/* Hover Tooltip */}
      {tooltip && (
        <div className="canvas-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          <div className="ct-title">{tooltip.label}</div>
          <div className="ct-row">
            <span>Type:</span>
            <strong>{tooltip.type}</strong>
          </div>
          <div className="ct-row">
            <span>Connections:</span>
            <strong>{tooltip.degree}</strong>
          </div>
          {tooltip.risk && (
            <div className="ct-row">
              <span>Risk:</span>
              <strong style={{ textTransform: "capitalize" }}>{tooltip.risk}</strong>
            </div>
          )}
        </div>
      )}

      {/* Context Menu */}
      <ContextMenu
        menu={contextMenu}
        onCenter={() => {
          const n = getNode(contextMenu?.nodeId);
          if (n) setCenter(n.position.x + CIRCLE / 2, n.position.y + CIRCLE / 2, { zoom: 1.8, duration: 350 });
        }}
        onDetails={() => onContextAction?.("details", contextMenu?.nodeId)}
        onExpand={() => onExpandNeighbors?.(contextMenu?.nodeId)}
        onFindPath={() => onContextAction?.("findPath", contextMenu?.nodeId)}
        onFinding={() => onContextAction?.("finding", contextMenu?.nodeId)}
        onExclude={() => onExcludeNode?.(contextMenu?.nodeId)}
        onCopy={() => {
          if (contextMenu?.nodeId) navigator.clipboard?.writeText(contextMenu.nodeId);
        }}
        onClose={() => setContextMenu(null)}
      />
    </div>
  );
});

// ─── Export Wrapped in Provider ───────────────────────────────────────────────
export default forwardRef(function ReactFlowGraph(props, ref) {
  return (
    <ReactFlowProvider>
      <ReactFlowInner {...props} ref={ref} />
    </ReactFlowProvider>
  );
});
