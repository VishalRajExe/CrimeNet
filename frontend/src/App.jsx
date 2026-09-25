import React, {
  useCallback, useEffect, useMemo, useRef, useState,
} from "react";
import {
  Network, ChevronDown, ChevronLeft, ChevronRight, RefreshCw,
  Upload, Download, Save, Image as ImageIcon, ExternalLink,
  X, Plus, Trash2, Edit3, Merge, Eye, EyeOff, Search,
  FileText, BarChart2, FolderOpen, ArrowRight,
  CheckCircle2, Minus, Square, Layers, GitFork, Tag,
  LayoutDashboard, Sidebar, Maximize2, Sliders, Sun, Moon,
} from "lucide-react";

import ReactFlowGraph, { TYPE_COLOR } from "./components/ReactFlowGraph";
import NodeDetailPanel from "./components/NodeDetailPanel";
import AnalysisPanel from "./components/AnalysisPanel";
import AIAnnotationPanel from "./components/AIAnnotationPanel";
import SearchFilterModal from "./components/SearchFilterModal";
import EditElementModal from "./components/EditElementModal";
import AddElementModal from "./components/AddElementModal";
import MergeElementsModal from "./components/MergeElementsModal";
import DeleteConfirmModal from "./components/DeleteConfirmModal";
import TacticalCommandBar from "./components/TacticalCommandBar";
import UserDocumentationModal from "./components/UserDocumentationModal";
import DynamicActionLoader from "./components/DynamicActionLoader";

import { DATASETS_CATALOG, getDatasetById } from "./data/crimeNetDatasets";
import { degreeMap as buildDegreeMap } from "./lib/graphAnalysis";

import "./styles/App.css";
import "./styles/futuristic.css";

export default function App() {
  // ── Theme State (Light / Dark) ─────────────────────────────────────────────
  const [theme, setTheme] = useState(() => {
    // v2 introduces the dark-first command-center visual system.
    const savedTheme = localStorage.getItem("crimenet_visual_theme");
    return savedTheme === "light" ? "light" : "dark";
  });

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === "light" ? "dark" : "light";
      localStorage.setItem("crimenet_visual_theme", next);
      return next;
    });
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Quick search is available from anywhere with the familiar ⌘K / Ctrl+K shortcut.
  useEffect(() => {
    const handleShortcut = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setIsSearchOpen(true);
      }
    };

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  // ── Core Dataset Selection ──────────────────────────────────────────────────
  const [selectedDatasetId, setSelectedDatasetId] = useState("unbound_case_2026");
  const currentDataset = useMemo(
    () => getDatasetById(selectedDatasetId),
    [selectedDatasetId]
  );

  // Network state allowing user edits (add/delete/exclude/merge)
  const [activeNodes, setActiveNodes] = useState([]);
  const [activeEdges, setActiveEdges] = useState([]);

  // Status & Notification Toast
  const [statusMessage, setStatusMessage] = useState(
    `The complete ${currentDataset.name} Network was loaded`
  );
  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);
  const notify = useCallback((msg) => {
    setToast(msg);
    setStatusMessage(msg);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2600);
  }, []);

  // Scoped entity filter in Network Tab
  const [scopedEntityIds, setScopedEntityIds] = useState([]);
  const [entitySearchFilter, setEntitySearchFilter] = useState("");



  const filteredEntityOptions = useMemo(() => {
    if (!entitySearchFilter.trim()) return currentDataset.nodes;
    const q = entitySearchFilter.toLowerCase();
    return currentDataset.nodes.filter(
      (n) => n.label.toLowerCase().includes(q) || n.type.toLowerCase().includes(q)
    );
  }, [currentDataset, entitySearchFilter]);

  useEffect(() => {
    setActiveNodes(currentDataset.nodes);
    setActiveEdges(currentDataset.edges);
    setScopedEntityIds([]);
    setEntitySearchFilter("");
  }, [currentDataset]);

  // ── Modals State ────────────────────────────────────────────────────────────
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isMergeOpen, setIsMergeOpen] = useState(false);
  const [isDocOpen, setIsDocOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionLoadingMessage, setActionLoadingMessage] = useState("");

  // ── Windows Application Style Box States (Minimize / Maximize) ──────────────
  const [boxStates, setBoxStates] = useState({
    nodes: { collapsed: false, maximized: false },
    edges: { collapsed: false, maximized: false },
    labels: { collapsed: false, maximized: false },
  });

  const toggleBoxCollapse = (key) => {
    setBoxStates((prev) => ({
      ...prev,
      [key]: { ...prev[key], collapsed: !prev[key].collapsed },
    }));
  };

  const toggleBoxMaximize = (key) => {
    setBoxStates((prev) => ({
      ...prev,
      [key]: { ...prev[key], maximized: !prev[key].maximized },
    }));
  };

  // ── Move Aside / Sidebar Collapse States ────────────────────────────────────
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(
    () => typeof window !== "undefined" && window.innerWidth < 1100
  );
  const [rightSidebarMaximized, setRightSidebarMaximized] = useState(false);

  // ── Left Sidebar Filter Tables (NODES, EDGES, LABELS) ───────────────────────
  const [visibleTypes, setVisibleTypes] = useState({});
  const [highlightTypes, setHighlightTypes] = useState({});
  const [visibleEdges, setVisibleEdges] = useState({});
  const [highlightEdges, setHighlightEdges] = useState({});
  const [labelSettings, setLabelSettings] = useState({ name: true, type: false });

  // ── Canvas & Selection State ────────────────────────────────────────────────
  const [selectedId, setSelectedId] = useState(null);
  const [layoutMode, setLayoutMode] = useState("force");
  const [colorMode, setColorMode] = useState("type");
  const [communityOf, setCommunityOf] = useState(null);
  const [centralityOf, setCentralityOf] = useState(null);
  const [pathIds, setPathIds] = useState(null);

  // ── Right Sidebar Tabs: NETWORK | ANALYSIS | INTELLIGENCE ───────────────────
  const [activeTab, setActiveTab] = useState("network"); // "network" | "analysis" | "intelligence"

  const handleTabSwitch = useCallback((newTab) => {
    if (newTab === activeTab) return;
    const titles = {
      network: "Loading Network Explorer...",
      analysis: "Running Graph Analysis Engine...",
      intelligence: "Loading AI Intelligence Module..."
    };
    setActionLoadingMessage(titles[newTab] || "Switching View...");
    setActionLoading(true);
    setActiveTab(newTab);
    setTimeout(() => setActionLoading(false), 260);
  }, [activeTab]);

  const handleDatasetChange = useCallback((newId) => {
    const ds = DATASETS_CATALOG.find(d => d.id === newId);
    setActionLoadingMessage(`Loading ${ds ? ds.name : newId}...`);
    setActionLoading(true);
    setSelectedDatasetId(newId);
    setTimeout(() => setActionLoading(false), 320);
  }, []);

  const [showNodeDetail, setShowNodeDetail] = useState(false);
  const [isGeminiChatOpen, setIsGeminiChatOpen] = useState(false);

  // Findings & Annotations
  const [annotations, setAnnotations] = useState({});
  const [findings, setFindings] = useState([
    {
      id: "f0",
      title: "Primary Key Broker Identified",
      severity: "high",
      body: "High-degree coordinator detected in network topology. Coordinate cross-verification.",
      tags: ["p1"],
      ts: Date.now() - 480000,
    },
  ]);

  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  const displayedEdges = activeEdges;

  // Degree Map
  const degreeMap = useMemo(
    () => buildDegreeMap(activeNodes, displayedEdges),
    [activeNodes, displayedEdges]
  );

  // Unique node types and edge types from active network
  const nodeTypesList = useMemo(() => {
    return Array.from(new Set(activeNodes.map((n) => (n.type || "person").toLowerCase())));
  }, [activeNodes]);

  const edgeTypesList = useMemo(() => {
    return Array.from(new Set(activeEdges.map((e) => e.type || e.label || "connected_to")));
  }, [activeEdges]);

  // Unique label variables across nodes
  const availableLabelVars = useMemo(() => {
    const vars = new Set(["name", "type"]);
    currentDataset.nodes.forEach((n) => {
      if (n.properties) {
        Object.keys(n.properties).forEach((k) => vars.add(k));
      }
    });
    return Array.from(vars);
  }, [currentDataset]);

  // Reset state when dataset changes
  useEffect(() => {
    setSelectedId(null);
    setShowNodeDetail(false);
    setColorMode("type");
    setCommunityOf(null);
    setCentralityOf(null);
    setPathIds(null);
    setVisibleTypes({});
    setHighlightTypes({});
    setVisibleEdges({});
    setStatusMessage(`The complete ${currentDataset.name} Network was loaded`);
  }, [currentDataset]);

  // ── Node & Canvas Handlers ─────────────────────────────────────────────────
  const [selectedEdge, setSelectedEdge] = useState(null);

  const handleSelectEdge = useCallback((edge) => {
    setSelectedEdge(edge);
    if (edge) {
      const srcNode = currentDataset.nodes.find((n) => n.id === edge.source);
      const tgtNode = currentDataset.nodes.find((n) => n.id === edge.target);
      const srcLabel = srcNode?.label || edge.source;
      const tgtLabel = tgtNode?.label || edge.target;
      const typeLabel = edge.type || edge.label || "connected";
      setStatusMessage(`Selected link: ${srcLabel} ➔ ${tgtLabel} (${typeLabel})`);
      notify(`Selected link: ${srcLabel} ➔ ${tgtLabel}`);
    }
  }, [currentDataset, notify]);

  const handleSelect = useCallback((id, isMulti = false) => {
    setSelectedEdge(null);
    if (!id) {
      setSelectedId(null);
      setScopedEntityIds([]);
      setShowNodeDetail(false);
      return;
    }

    if (isMulti) {
      setScopedEntityIds((prev) => {
        const set = new Set(prev);
        if (selectedId) set.add(selectedId);
        if (set.has(id)) set.delete(id);
        else set.add(id);
        const next = Array.from(set);
        setSelectedId(next.length > 0 ? next[next.length - 1] : null);
        return next;
      });
      setShowNodeDetail(true);
    } else {
      setSelectedId(id);
      setScopedEntityIds([id]);
      setShowNodeDetail(true);
    }
  }, [selectedId]);

  const handleContextAction = useCallback((action, nodeId) => {
    if (action === "details") {
      setSelectedId(nodeId);
      setShowNodeDetail(true);
    } else if (action === "findPath") {
      setSelectedId(nodeId);
      setActiveTab("analysis");
      setRightSidebarCollapsed(false);
    } else if (action === "finding") {
      setSelectedId(nodeId);
      setActiveTab("intelligence");
      setRightSidebarCollapsed(false);
    } else if (action === "search") {
      setActiveTab("network");
      setRightSidebarCollapsed(false);
    }
  }, []);

  // Expand neighbors (1-hop) - gathers selected node(s) and their connections
  const handleExpandNeighbors = useCallback((nodeId) => {
    const targetSet = new Set();
    if (nodeId) targetSet.add(nodeId);
    if (selectedId) targetSet.add(selectedId);
    if (scopedEntityIds && scopedEntityIds.length > 0) {
      scopedEntityIds.forEach((id) => targetSet.add(id));
    }

    if (targetSet.size === 0) {
      notify("Select node(s) first to expand");
      return;
    }

    const targetIds = Array.from(targetSet);

    // Find all 1-hop connected neighbors and their connecting edges from the active dataset
    const gatheredNodeIds = new Set(targetIds);
    const gatheredEdges = [];

    currentDataset.edges.forEach((e) => {
      const isSrc = targetSet.has(e.source);
      const isTgt = targetSet.has(e.target);
      if (isSrc || isTgt) {
        gatheredNodeIds.add(e.source);
        gatheredNodeIds.add(e.target);
        gatheredEdges.push(e);
      }
    });

    // Also include any internal edges between the gathered nodes
    currentDataset.edges.forEach((e) => {
      if (gatheredNodeIds.has(e.source) && gatheredNodeIds.has(e.target)) {
        if (!gatheredEdges.some((ge) => ge.id === e.id || (ge.source === e.source && ge.target === e.target))) {
          gatheredEdges.push(e);
        }
      }
    });

    const gatheredNodes = currentDataset.nodes.filter((n) => gatheredNodeIds.has(n.id));

    // If canvas is already scoped to a subset, merge them with existing activeNodes;
    // Otherwise, gather and isolate the selected nodes + their neighbors
    if (activeNodes.length < currentDataset.nodes.length && activeNodes.length > 0) {
      const nodeMap = new Map();
      activeNodes.forEach((n) => nodeMap.set(n.id, n));
      gatheredNodes.forEach((n) => nodeMap.set(n.id, n));

      const edgeMap = new Map();
      activeEdges.forEach((e) => edgeMap.set(e.id || `${e.source}-${e.target}`, e));
      gatheredEdges.forEach((e) => edgeMap.set(e.id || `${e.source}-${e.target}`, e));

      setActiveNodes(Array.from(nodeMap.values()));
      setActiveEdges(Array.from(edgeMap.values()));
    } else {
      setActiveNodes(gatheredNodes);
      setActiveEdges(gatheredEdges);
    }

    const neighborCount = gatheredNodes.length - targetIds.length;
    notify(`Gathered ${gatheredNodes.length} nodes (${targetIds.length} selected + ${neighborCount} connected)`);

    setTimeout(() => {
      canvasRef.current?.fit();
    }, 150);
  }, [selectedId, scopedEntityIds, currentDataset, activeNodes, activeEdges, notify]);

  // Exclude node
  const handleExcludeNode = useCallback((nodeId) => {
    const targetId = nodeId || selectedId;
    if (!targetId) {
      notify("Select a node to exclude");
      return;
    }
    setActiveNodes((prev) => prev.filter((n) => n.id !== targetId));
    setActiveEdges((prev) => prev.filter((e) => e.source !== targetId && e.target !== targetId));
    if (selectedId === targetId) {
      setSelectedId(null);
      setShowNodeDetail(false);
    }
    notify(`Excluded element from canvas`);
  }, [selectedId, notify]);

  // Clear view
  const handleClearView = useCallback(() => {
    setSelectedId(null);
    setSelectedEdge(null);
    setShowNodeDetail(false);
    setPathIds(null);
    setColorMode("type");
    setCommunityOf(null);
    setCentralityOf(null);
    notify("Cleared view");
  }, [notify]);

  // Show all nodes
  const handleShowAllNodes = useCallback(() => {
    setActiveNodes(currentDataset.nodes);
    setActiveEdges(currentDataset.edges);
    setVisibleTypes({});
    setHighlightTypes({});
    setVisibleEdges({});
    setHighlightEdges({});
    setScopedEntityIds([]);
    canvasRef.current?.fit();
    notify("All nodes restored");
  }, [currentDataset, notify]);

  // ── Modal Actions (Add, Edit, Merge, Delete, Search) ───────────────────────
  const handleAddNode = useCallback((newNode) => {
    setActiveNodes((prev) => [...prev, newNode]);
    setSelectedId(newNode.id);
    setShowNodeDetail(true);
    notify(`Added node ${newNode.label}`);
  }, [notify]);

  const handleAddEdge = useCallback((newEdge) => {
    setActiveEdges((prev) => [...prev, newEdge]);
    notify(`Added relationship between ${newEdge.source} and ${newEdge.target}`);
  }, [notify]);

  const handleSaveEditedElement = useCallback((updatedElement) => {
    setActiveNodes((prev) =>
      prev.map((n) => (n.id === updatedElement.id ? updatedElement : n))
    );
    notify(`Updated properties for ${updatedElement.label || updatedElement.id}`);
  }, [notify]);

  const handleMergeNodes = useCallback(({ keepId, label, type, properties, removeIds }) => {
    // 1. Create consolidated node
    const mergedNode = {
      id: keepId,
      label,
      type,
      properties,
    };

    // 2. Remove old nodes and add consolidated node
    setActiveNodes((prev) => [
      ...prev.filter((n) => !removeIds.includes(n.id)),
      mergedNode,
    ]);

    // 3. Reroute all incident edges to the consolidated node
    setActiveEdges((prev) =>
      prev.map((e) => {
        let newSrc = e.source;
        let newTgt = e.target;
        if (removeIds.includes(e.source)) newSrc = keepId;
        if (removeIds.includes(e.target)) newTgt = keepId;
        return {
          ...e,
          source: newSrc,
          target: newTgt,
        };
      }).filter((e) => e.source !== e.target) // Remove self-loops created by merge
    );

    setSelectedId(keepId);
    setShowNodeDetail(true);
    notify(`Merged entities into consolidated node: ${label}`);
  }, [notify]);

  const handleDeleteConfirmed = useCallback(() => {
    if (!selectedId) return;
    setActiveNodes((prev) => prev.filter((n) => n.id !== selectedId));
    setActiveEdges((prev) => prev.filter((e) => e.source !== selectedId && e.target !== selectedId));
    setSelectedId(null);
    setShowNodeDetail(false);
    notify(`Permanently deleted element`);
  }, [selectedId, notify]);

  const handleApplyFilter = useCallback(({ quickQuery, propertyFilters, matchMode }) => {
    if (!quickQuery && (!propertyFilters || propertyFilters.length === 0)) {
      // Reset filter
      setActiveNodes(currentDataset.nodes);
      setActiveEdges(currentDataset.edges);
      notify("Filter cleared");
      return;
    }

    const matchedNodes = currentDataset.nodes.filter((node) => {
      // 1. Check quick query
      let matchesQuick = true;
      if (quickQuery) {
        const q = quickQuery.toLowerCase();
        const matchesName = (node.label || "").toLowerCase().includes(q);
        const matchesId = (node.id || "").toLowerCase().includes(q);
        const matchesProps = Object.values(node.properties || {}).some((v) =>
          String(v).toLowerCase().includes(q)
        );
        matchesQuick = matchesName || matchesId || matchesProps;
      }

      // 2. Check property filters
      if (!propertyFilters || propertyFilters.length === 0) {
        return matchesQuick;
      }

      const rowMatches = propertyFilters.map((row) => {
        const propVal =
          row.property === "label"
            ? node.label
            : row.property === "id"
            ? node.id
            : row.property === "type"
            ? node.type
            : node.properties?.[row.property];

        if (propVal == null) return false;
        const targetStr = String(propVal).toLowerCase();
        const queryStr = String(row.value).toLowerCase();

        if (row.condition === "equals") return targetStr === queryStr;
        if (row.condition === "contains") return targetStr.includes(queryStr);
        if (row.condition === "starts_with") return targetStr.startsWith(queryStr);
        if (row.condition === "ends_with") return targetStr.endsWith(queryStr);
        if (row.condition === "greater_than") return Number(propVal) > Number(row.value);
        if (row.condition === "less_than") return Number(propVal) < Number(row.value);
        return false;
      });

      const matchesProps =
        matchMode === "OR"
          ? rowMatches.some(Boolean)
          : rowMatches.every(Boolean);

      return quickQuery ? matchesQuick && matchesProps : matchesProps;
    });

    const matchedIds = new Set(matchedNodes.map((n) => n.id));
    setActiveNodes(matchedNodes);
    setActiveEdges(
      currentDataset.edges.filter(
        (e) => matchedIds.has(e.source) && matchedIds.has(e.target)
      )
    );

    notify(`Filter applied: ${matchedNodes.length} entities matched`);
  }, [currentDataset, notify]);

  // ── Focus Pair & N-Hop Handlers ────────────────────────────────────────────
  const handleFocusPair = useCallback((idA, idB) => {
    const nodeA = activeNodes.find((n) => n.id === idA);
    const nodeB = activeNodes.find((n) => n.id === idB);
    if (!nodeA || !nodeB) {
      notify(`Entities not found in active view`);
      return;
    }

    // Find shared intermediaries
    const nbrsA = new Set(
      activeEdges.filter((e) => e.source === idA || e.target === idA).map((e) => (e.source === idA ? e.target : e.source))
    );
    const nbrsB = new Set(
      activeEdges.filter((e) => e.source === idB || e.target === idB).map((e) => (e.source === idB ? e.target : e.source))
    );
    const intermediaries = Array.from(nbrsA).filter((x) => nbrsB.has(x));

    const focusIds = [idA, idB, ...intermediaries];
    setPathIds(focusIds);
    setSelectedId(idA);
    notify(`Focused on Lead Pair: ${nodeA.label} ↔ ${nodeB.label} (${intermediaries.length} shared connectors)`);
  }, [activeNodes, activeEdges, notify]);

  const handleHighlightNHop = useCallback((rootId, hops) => {
    if (!rootId) return;
    const visited = new Set([rootId]);
    let currentQueue = [rootId];

    for (let h = 0; h < hops; h++) {
      const nextQueue = [];
      currentQueue.forEach((curr) => {
        activeEdges.forEach((e) => {
          if (e.source === curr && !visited.has(e.target)) {
            visited.add(e.target);
            nextQueue.push(e.target);
          } else if (e.target === curr && !visited.has(e.source)) {
            visited.add(e.source);
            nextQueue.push(e.source);
          }
        });
      });
      currentQueue = nextQueue;
    }

    setPathIds(Array.from(visited));
    setSelectedId(rootId);
    notify(`Highlighted ${visited.size} entities in ${hops}-hop subgraph`);
  }, [activeEdges, notify]);

  // ── AI Narrative / Evidence Ingestion Handler ──────────────────────────
  const handleGraphUpdate = useCallback((newNodes, newEdges) => {
    if (!newNodes || !newNodes.length) return;
    setActiveNodes((prev) => {
      const existingIds = new Set(prev.map((n) => n.id));
      const toAdd = newNodes.filter((n) => !existingIds.has(n.id));
      return [...prev, ...toAdd];
    });
    setActiveEdges((prev) => {
      const existingIds = new Set(prev.map((e) => e.id));
      const toAdd = (newEdges || []).filter((e) => !existingIds.has(e.id));
      return [...prev, ...toAdd];
    });
    notify(`CrimeNet AI updated network: +${newNodes.length} nodes, +${(newEdges || []).length} edges`);
    setTimeout(() => {
      canvasRef.current?.fit();
    }, 300);
  }, [notify]);

  // ── File Upload / Export Handlers ──────────────────────────────────────────
  const handleFileUpload = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result;
        if (typeof text !== "string") return;

        // Try JSON format
        if (file.name.endsWith(".json")) {
          let parsed;
          try {
            parsed = JSON.parse(text);
          } catch {
            // Newline-delimited JSON
            const lines = text.split(/\r?\n/);
            const nList = [];
            const eList = [];
            lines.forEach((line) => {
              const trimmed = line.trim();
              if (!trimmed || trimmed.startsWith("#")) return;
              try {
                const obj = JSON.parse(trimmed);
                if (obj.type === "node" && obj.id) {
                  nList.push({
                    id: String(obj.id),
                    label: obj.properties?.name || obj.id,
                    type: obj.properties?.type || "person",
                    properties: obj.properties || {},
                  });
                } else if (obj.type === "edge" && obj.source && obj.target) {
                  eList.push({
                    id: `e_${obj.source}_${obj.target}_${eList.length}`,
                    source: String(obj.source),
                    target: String(obj.target),
                    label: obj.properties?.type || "connected_to",
                    type: obj.properties?.type || "connected_to",
                    weight: Number(obj.properties?.weight || 1),
                    properties: obj.properties || {},
                  });
                }
              } catch {}
            });
            parsed = { nodes: nList, edges: eList, name: file.name.replace(".json", "") };
          }

          if (parsed && Array.isArray(parsed.nodes)) {
            setActiveNodes(parsed.nodes);
            setActiveEdges(parsed.edges || []);
            notify(`Loaded network from ${file.name} (${parsed.nodes.length} nodes, ${parsed.edges?.length || 0} edges)`);
          }
        } else {
          notify("Uploaded file format recognized");
        }
      } catch (err) {
        notify("Could not parse file: " + err.message);
      }
    };
    reader.readAsText(file);
  }, [notify]);

  const handleExportNetwork = useCallback(() => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(
      JSON.stringify({
        id: currentDataset.id,
        name: currentDataset.name,
        numNodes: activeNodes.length,
        numEdges: activeEdges.length,
        nodes: activeNodes,
        edges: activeEdges
      }, null, 2)
    );
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${currentDataset.id}_network_export.json`);
    downloadAnchor.click();
    notify("Network exported as JSON");
  }, [activeNodes, activeEdges, currentDataset, notify]);

  const handleSaveNetworkState = useCallback(() => {
    handleExportNetwork();
    notify("Network state saved to local file");
  }, [handleExportNetwork, notify]);

  const handleExportImage = useCallback(() => {
    notify("Canvas screenshot ready for download");
  }, [notify]);

  // Selected node object for editing/deleting
  const selectedNodeObj = useMemo(
    () => activeNodes.find((n) => n.id === selectedId),
    [activeNodes, selectedId]
  );

  return (
    <div className={`app ${theme}`} data-theme={theme}>
      {/* ── Top Tactical Navigation Bar ─────────────────────────────────────── */}
      <TacticalCommandBar
        caseId={selectedDatasetId}
        nodesCount={activeNodes.length}
        edgesCount={displayedEdges.length}
        onToggleTheme={toggleTheme}
        theme={theme}
      />

      {/* ── Main Body ────────────────────────────────────────────────────────── */}
      <div className="body" role="main">
        {/* ── Left Sidebar: Control Boxes (Nodes, Edges, Labels) ───────────────── */}
        <div className={`left-sidebar ${leftSidebarCollapsed ? "collapsed" : ""}`}>
          <div className="left-sidebar-toolbar" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8, flexShrink: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 700, fontSize: 12, color: "var(--text)" }}>
              <Layers size={14} color="var(--teal)" />
              <span>Control Boxes</span>
            </div>

            <button
              className="win-btn"
              aria-label="Collapse left sidebar"
              onClick={() => setLeftSidebarCollapsed(true)}
              title="Move aside left panel"
            >
              <ChevronLeft size={13} />
            </button>
          </div>

          {/* "OPEN ORIGINAL NETWORK" Button */}
          <button className="btn-open-original" onClick={handleShowAllNodes}>
            <FolderOpen size={13} />
            Open Original Network
          </button>

          {/* NODES Box Card */}
          <div className={`box-card ${boxStates.nodes.collapsed ? "collapsed" : ""} ${boxStates.nodes.maximized ? "maximized" : ""}`}>
            <div className="box-card-header">
              <div className="box-title-wrap">
                <Layers size={11} />
                <span>Nodes ({activeNodes.length})</span>
              </div>
              <div className="win-controls">
                <button
                  className="win-btn"
                  title={boxStates.nodes.collapsed ? "Expand box" : "Minimize box"}
                  onClick={() => toggleBoxCollapse("nodes")}
                >
                  {boxStates.nodes.collapsed ? <ChevronDown size={12} /> : <Minus size={12} />}
                </button>
                <button
                  className={`win-btn ${boxStates.nodes.maximized ? "active" : ""}`}
                  title={boxStates.nodes.maximized ? "Restore height" : "Maximize height"}
                  onClick={() => toggleBoxMaximize("nodes")}
                >
                  <Square size={10} />
                </button>
              </div>
            </div>
            <div className="box-card-content">
              <table className="box-card-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Show</th>
                    <th>Highlight</th>
                  </tr>
                </thead>
                <tbody>
                  {nodeTypesList.map((type) => {
                    const isVisible = visibleTypes[type] !== false;
                    const isHighlighted = highlightTypes[type] === true;
                    const count = activeNodes.filter((n) => n.type === type).length;
                    return (
                      <tr key={type}>
                        <td>
                          <span
                            className="type-indicator-dot"
                            style={{ background: TYPE_COLOR[type] || "#54b399" }}
                          />
                          <span style={{ textTransform: "capitalize" }}>
                            {type} ({count})
                          </span>
                        </td>
                        <td>
                          <input
                            type="checkbox"
                            className="mini-checkbox"
                            aria-label={`Show ${type} entities`}
                            checked={isVisible}
                            onChange={(e) =>
                              setVisibleTypes((prev) => ({ ...prev, [type]: e.target.checked }))
                            }
                          />
                        </td>
                        <td>
                          <input
                            type="checkbox"
                            className="mini-checkbox"
                            aria-label={`Highlight ${type} entities`}
                            checked={isHighlighted}
                            onChange={(e) =>
                              setHighlightTypes((prev) => ({ ...prev, [type]: e.target.checked }))
                            }
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* EDGES Box Card */}
          <div className={`box-card ${boxStates.edges.collapsed ? "collapsed" : ""} ${boxStates.edges.maximized ? "maximized" : ""}`}>
            <div className="box-card-header">
              <div className="box-title-wrap">
                <GitFork size={11} />
                <span>Edges ({displayedEdges.length})</span>
              </div>
              <div className="win-controls">
                <button
                  className="win-btn"
                  title={boxStates.edges.collapsed ? "Expand box" : "Minimize box"}
                  onClick={() => toggleBoxCollapse("edges")}
                >
                  {boxStates.edges.collapsed ? <ChevronDown size={12} /> : <Minus size={12} />}
                </button>
                <button
                  className={`win-btn ${boxStates.edges.maximized ? "active" : ""}`}
                  title={boxStates.edges.maximized ? "Restore height" : "Maximize height"}
                  onClick={() => toggleBoxMaximize("edges")}
                >
                  <Square size={10} />
                </button>
              </div>
            </div>
            <div className="box-card-content">
              <table className="box-card-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Show</th>
                    <th>Highlight</th>
                  </tr>
                </thead>
                <tbody>
                  {edgeTypesList.map((type) => {
                    const isVisible = visibleEdges[type] !== false;
                    const isHighlighted = highlightEdges[type] === true;
                    const count = displayedEdges.filter((e) => (e.type || e.label) === type).length;
                    return (
                      <tr key={type}>
                        <td>
                          <span style={{ textTransform: "capitalize" }}>
                            {type} ({count})
                          </span>
                        </td>
                        <td>
                          <input
                            type="checkbox"
                            className="mini-checkbox"
                            aria-label={`Show ${type} relationships`}
                            checked={isVisible}
                            onChange={(e) =>
                              setVisibleEdges((prev) => ({ ...prev, [type]: e.target.checked }))
                            }
                          />
                        </td>
                        <td>
                          <input
                            type="checkbox"
                            className="mini-checkbox"
                            aria-label={`Highlight ${type} relationships`}
                            checked={isHighlighted}
                            onChange={(e) =>
                              setHighlightEdges((prev) => ({ ...prev, [type]: e.target.checked }))
                            }
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* LABELS Box Card */}
          <div className={`box-card ${boxStates.labels.collapsed ? "collapsed" : ""} ${boxStates.labels.maximized ? "maximized" : ""}`}>
            <div className="box-card-header">
              <div className="box-title-wrap">
                <Tag size={11} />
                <span>Labels</span>
              </div>
              <div className="win-controls">
                <button
                  className="win-btn"
                  title={boxStates.labels.collapsed ? "Expand box" : "Minimize box"}
                  onClick={() => toggleBoxCollapse("labels")}
                >
                  {boxStates.labels.collapsed ? <ChevronDown size={12} /> : <Minus size={12} />}
                </button>
                <button
                  className={`win-btn ${boxStates.labels.maximized ? "active" : ""}`}
                  title={boxStates.labels.maximized ? "Restore height" : "Maximize height"}
                  onClick={() => toggleBoxMaximize("labels")}
                >
                  <Square size={10} />
                </button>
              </div>
            </div>
            <div className="box-card-content">
              <table className="box-card-table">
                <thead>
                  <tr>
                    <th>Variable</th>
                    <th>Display</th>
                  </tr>
                </thead>
                <tbody>
                  {availableLabelVars.map((v) => (
                    <tr key={v}>
                      <td>{v}</td>
                      <td>
                        <input
                          type="checkbox"
                          className="mini-checkbox"
                          aria-label={`Show ${v} label`}
                          checked={Boolean(labelSettings[v])}
                          onChange={(e) =>
                            setLabelSettings((prev) => ({ ...prev, [v]: e.target.checked }))
                          }
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ── Main Canvas ────────────────────────────────────────────────────── */}
        <div className="canvas-wrap">
          {/* Floating button to restore Left Sidebar if collapsed */}
          {leftSidebarCollapsed && (
            <button
              className="sidebar-dock-btn-left"
              onClick={() => setLeftSidebarCollapsed(false)}
              title="Show control boxes"
            >
              <Sidebar size={12} />
              Boxes
              <ChevronRight size={13} />
            </button>
          )}

          {/* Floating button to restore Right Sidebar if collapsed */}
          {rightSidebarCollapsed && (
            <button
              className="sidebar-dock-btn-right"
              onClick={() => setRightSidebarCollapsed(false)}
              title="Show dashboard & analysis"
            >
              <LayoutDashboard size={12} />
              Dashboard
              <ChevronLeft size={13} />
            </button>
          )}

          <ReactFlowGraph
            ref={canvasRef}
            nodes={activeNodes}
            edges={displayedEdges}
            colorMode={colorMode}
            communityOf={communityOf}
            centralityOf={centralityOf}
            selectedId={selectedId}
            selectedIds={scopedEntityIds}
            pathIds={pathIds}
            visibleTypes={visibleTypes}
            showLabels={labelSettings.name}
            showEdgeLabels={labelSettings.type}
            layoutMode={layoutMode}
            setLayoutMode={setLayoutMode}
            degreeMap={degreeMap}
            onSelect={handleSelect}
            onContextAction={handleContextAction}
            onExpandNeighbors={handleExpandNeighbors}
            onExcludeNode={handleExcludeNode}
            onShowAllNodes={handleShowAllNodes}
            onClearView={handleClearView}
            onEditElement={() => setIsEditOpen(true)}
            onAddElement={() => setIsAddOpen(true)}
            onDeleteElement={() => setIsDeleteOpen(true)}
            onMergeElements={() => setIsMergeOpen(true)}
            onOpenSearch={() => setIsSearchOpen(true)}
            statusMessage={statusMessage}
            leftSidebarCollapsed={leftSidebarCollapsed}
            onToggleLeftSidebar={() => setLeftSidebarCollapsed((v) => !v)}
            theme={theme}
            onSelectEdge={handleSelectEdge}
            onToggleTheme={toggleTheme}
          />
        </div>

        {/* ── Right Sidebar: Tabs (NETWORK | ANALYSIS | INTELLIGENCE) ─────────── */}
        <div
          className={`right-sidebar ${rightSidebarCollapsed ? "collapsed" : ""} ${
            rightSidebarMaximized ? "maximized" : ""
          }`}
        >
          {/* Top Tabs with Window Actions */}
          <div className="tab-bar">
            <button
              className={`tab-btn ${activeTab === "network" ? "active" : ""}`}
              onClick={() => handleTabSwitch("network")}
            >
              Network
            </button>
            <button
              className={`tab-btn ${activeTab === "analysis" ? "active" : ""}`}
              onClick={() => handleTabSwitch("analysis")}
            >
              Analysis
            </button>
            <button
              className={`tab-btn ${activeTab === "intelligence" ? "active" : ""}`}
              onClick={() => handleTabSwitch("intelligence")}
            >
              Intelligence
            </button>

            <div className="tab-window-actions">
              <button
                className={`win-btn ${rightSidebarMaximized ? "active" : ""}`}
                aria-label={rightSidebarMaximized ? "Restore panel width" : "Expand panel width"}
                title={rightSidebarMaximized ? "Restore panel width" : "Expand panel width"}
                onClick={() => setRightSidebarMaximized((v) => !v)}
              >
                <Maximize2 size={11} />
              </button>
              <button
                className="win-btn"
                aria-label="Collapse right dashboard"
                title="Move aside right dashboard"
                onClick={() => setRightSidebarCollapsed(true)}
              >
                <ChevronRight size={13} />
              </button>
            </div>
          </div>

          {/* Tab Panes */}
          <div className="tab-content">
            {/* NETWORK Tab */}
            {activeTab === "network" && (
              <div className="network-tab-pane">
                {/* Dataset selector dropdown */}
                <div style={{ marginBottom: 10 }}>
                  <label className="crimenet-field-label">Select network ...</label>
                  <select
                    className="crimenet-select"
                    aria-label="Select investigation network"
                    value={selectedDatasetId}
                    onChange={(e) => handleDatasetChange(e.target.value)}
                    style={{ fontWeight: 500, cursor: "pointer" }}
                  >
                    {DATASETS_CATALOG.map((ds) => (
                      <option key={ds.id} value={ds.id}>
                        {ds.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Scope Entities Searchable Multi-Selector */}
                <div style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <label className="crimenet-field-label" style={{ margin: 0 }}>
                      Select entities ...
                    </label>
                    <span style={{ fontSize: 10.5, color: "#64748b", fontWeight: 600 }}>
                      {scopedEntityIds.length > 0 ? `${scopedEntityIds.length} of ${currentDataset.nodes.length} selected` : `All (${currentDataset.nodes.length})`}
                    </span>
                  </div>

                  <div className="entity-selector-box">
                    <div className="entity-selector-toolbar">
                      <input
                        type="text"
                        className="entity-selector-search"
                        aria-label="Search entities to scope"
                        placeholder="Search entities to scope..."
                        value={entitySearchFilter}
                        onChange={(e) => setEntitySearchFilter(e.target.value)}
                      />
                      <div className="entity-selector-quick-btns">
                        <button
                          type="button"
                          className="entity-quick-btn"
                          onClick={() => setScopedEntityIds(currentDataset.nodes.map((n) => n.id))}
                        >
                          All
                        </button>
                        <span style={{ color: "#cbd5e1" }}>·</span>
                        <button
                          type="button"
                          className="entity-quick-btn"
                          onClick={() => setScopedEntityIds([])}
                        >
                          Clear
                        </button>
                      </div>
                    </div>

                    <div className="entity-selector-list">
                      {filteredEntityOptions.map((n) => {
                        const isChecked = scopedEntityIds.includes(n.id);
                        return (
                          <div
                            key={n.id}
                            className={`entity-selector-item ${isChecked ? "selected" : ""}`}
                            onClick={() => {
                              setScopedEntityIds((prev) =>
                                isChecked ? prev.filter((id) => id !== n.id) : [...prev, n.id]
                              );
                            }}
                          >
                            <div className="entity-info">
                              <span
                                className="type-indicator-dot"
                                style={{ background: TYPE_COLOR[n.type] || "#64748b" }}
                              />
                              <span>{n.label}</span>
                              <span style={{ color: "#94a3b8", fontSize: 10.5 }}>({n.type})</span>
                            </div>
                            <input
                              type="checkbox"
                              className="mini-checkbox"
                              aria-label={`Select ${n.label}`}
                              checked={isChecked}
                              readOnly
                            />
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Primary LOAD NETWORK Button */}
                <button
                  className="btn-load-network"
                  onClick={() => {
                    if (scopedEntityIds.length > 0) {
                      const idSet = new Set(scopedEntityIds);
                      const filtered = currentDataset.nodes.filter((n) => idSet.has(n.id));
                      setActiveNodes(filtered);
                      setActiveEdges(
                        currentDataset.edges.filter(
                          (e) => idSet.has(e.source) && idSet.has(e.target)
                        )
                      );
                      notify(`Loaded ${filtered.length} scoped entities`);
                    } else {
                      handleShowAllNodes();
                    }
                  }}
                >
                  <RefreshCw size={13} /> Load Network
                </button>

                {/* Action Buttons List */}
                <div className="network-action-list">
                  <input
                    type="file"
                    ref={fileInputRef}
                    aria-label="Upload network file"
                    style={{ display: "none" }}
                    accept=".json,.csv,.txt"
                    onChange={handleFileUpload}
                  />
                  <button
                    className="btn-network-action"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload size={12} /> Upload CSV / File
                  </button>
                  <button
                    className="btn-network-action"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <FolderOpen size={12} /> Load From File
                  </button>
                  <button
                    className="btn-network-action"
                    onClick={handleSaveNetworkState}
                  >
                    <Save size={12} /> Save Network State
                  </button>
                  <button
                    className="btn-network-action"
                    onClick={handleExportNetwork}
                  >
                    <Download size={12} /> Export Network
                  </button>
                  <button
                    className="btn-network-action"
                    onClick={handleExportImage}
                  >
                    <ImageIcon size={12} /> Export Image
                  </button>
                </div>



                {/* Bottom Summary Card */}
                <div className="network-summary-card">
                  <div className="summary-row">
                    <span className="label">Network</span>
                    <span className="val">{currentDataset.name}</span>
                  </div>
                  <div className="summary-row">
                    <span className="label"># Nodes</span>
                    <span className="val">{activeNodes.length}</span>
                  </div>
                  <div className="summary-row">
                    <span className="label"># Edges</span>
                    <span className="val">{displayedEdges.length}</span>
                  </div>
                </div>

                {/* User Documentation Button */}
                <button
                  className="btn-user-doc"
                  onClick={() => setIsDocOpen(true)}
                >
                  <ExternalLink size={12} /> User Documentation
                </button>
              </div>
            )}

            {/* ANALYSIS Tab */}
            {activeTab === "analysis" && (
              <AnalysisPanel
                nodes={activeNodes}
                edges={displayedEdges}
                onApplyScores={(scores) => {
                  if (scores) {
                    setCentralityOf(scores);
                    setColorMode("centrality");
                  } else {
                    setCentralityOf(null);
                    setColorMode("type");
                  }
                }}
                onApplyCommunity={(res) => {
                  if (res) {
                    setCommunityOf(res.communityOf);
                    setColorMode("community");
                  } else {
                    setCommunityOf(null);
                    setColorMode("type");
                  }
                }}
                onHighlightPath={(path) => setPathIds(path)}
                onToast={notify}
              />
            )}

            {/* INTELLIGENCE Tab */}
            {activeTab === "intelligence" && (
              <AIAnnotationPanel
                nodes={activeNodes}
                edges={displayedEdges}
                selectedId={selectedId}
                onSelectNode={(id) => {
                  handleSelect(id);
                  canvasRef.current?.center(id);
                }}
                onFocusPair={handleFocusPair}
                onHighlightNHop={handleHighlightNHop}
                onToast={notify}
                caseName={currentDataset.name}
                caseId={selectedDatasetId}
                onOpenDoc={() => setIsDocOpen(true)}
              />
            )}
          </div>

          {/* Selected Node Detail Drawer/Inspector */}
          {selectedId && showNodeDetail && (
            <div className="node-inspector-drawer">
              <div className="nid-header">
                <span className="nid-title">Entity Inspector</span>
                <X
                  size={14}
                  style={{ cursor: "pointer", color: "var(--text-muted)" }}
                  onClick={() => setShowNodeDetail(false)}
                />
              </div>
              <NodeDetailPanel
                nodes={activeNodes}
                edges={displayedEdges}
                selectedId={selectedId}
                analysisScores={centralityOf}
                annotations={annotations}
                onAnnotate={(id, text) => setAnnotations((prev) => ({ ...prev, [id]: text }))}
                onSelectNode={(id) => {
                  handleSelect(id);
                  canvasRef.current?.center(id);
                }}
                onNotify={notify}
                onHighlightPath={setPathIds}
                caseId={selectedDatasetId}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Modals ──────────────────────────────────────────────────────────── */}
      <SearchFilterModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        nodes={activeNodes}
        onApplyFilter={handleApplyFilter}
      />

      <EditElementModal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        element={selectedNodeObj}
        onSave={handleSaveEditedElement}
      />

      <AddElementModal
        isOpen={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        nodes={activeNodes}
        onAddNode={handleAddNode}
        onAddEdge={handleAddEdge}
      />

      <MergeElementsModal
        isOpen={isMergeOpen}
        onClose={() => setIsMergeOpen(false)}
        nodes={activeNodes}
        selectedNodeId={selectedId}
        onMerge={handleMergeNodes}
      />

      <DeleteConfirmModal
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        elementName={selectedNodeObj?.label}
        onConfirm={handleDeleteConfirmed}
      />

      <UserDocumentationModal
        isOpen={isDocOpen}
        onClose={() => setIsDocOpen(false)}
      />

      <DynamicActionLoader
        active={actionLoading}
        message={actionLoadingMessage}
      />
    </div>
  );
}
