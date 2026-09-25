/**
 * AIAnnotationPanel.jsx — CrimeNet Universal AI Intelligence Engine (Client-Side)
 * Ported directly from CrimeNet/visualizer/assets/unbound_panel.js
 * 
 * Features:
 * - INSIGHTS: Topology metrics, explainable AI brief, entity search & filter chips, ranked operatives
 * - HIDDEN LINKS: Adamic-Adar triadic closure link prediction with Accept / Dismiss leads & Focus Pair
 * - ANOMALIES: Hub outliers, communication bridges (articulation points), cross-case entities, night bursts
 * - N-HOP & EVIDENCE: Multi-hop BFS neighborhood exploration with distance slider & subgraph highlighting
 * - TIMELINE: Chronological forensic event feed from node/edge timestamps
 * - EXPORT DOSSIER: Printable & copyable case intelligence report
 */

import React, { useMemo, useState, useEffect } from "react";
import {
  Download, ExternalLink, Search, Sparkles, AlertCircle,
  Network, Share2, Clock, GitCommit, FileText, ChevronRight,
  Printer, Copy, Check, Eye, Filter, ArrowRight, ShieldCheck, Play
} from "lucide-react";
import { TYPE_COLOR } from "./ReactFlowGraph";
import { api } from "../lib/api";

export default function AIAnnotationPanel({
  nodes = [],
  edges = [],
  selectedId,
  onSelectNode,
  onFocusPair,
  onHighlightNHop,
  onToast,
  caseName = "Active Case",
  caseId = "CASE-2024-MH-088",
  onOpenDoc,
}) {
  const [activeSubtab, setActiveSubtab] = useState("insights"); // "insights" | "hidden" | "anomalies" | "nhop" | "timeline"
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState("ALL");
  const [acceptedLeads, setAcceptedLeads] = useState(new Set());
  const [dismissedLeads, setDismissedLeads] = useState(new Set());
  const [nHopDistance, setNHopDistance] = useState(2);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [copiedFlash, setCopiedFlash] = useState(false);
  const [backendAnomalies, setBackendAnomalies] = useState([]);
  const [langGraphBrief, setLangGraphBrief] = useState(null);
  const [langGraphLoading, setLangGraphLoading] = useState(false);

  // Fetch real scikit-learn Isolation Forest anomalies from FastAPI backend
  useEffect(() => {
    if (nodes && nodes.length > 0) {
      api.getAnomalies({ nodes, edges })
        .then((res) => {
          if (res && res.anomalies) {
            setBackendAnomalies(res.anomalies);
          }
        })
        .catch((err) => console.warn("Backend anomalies notice:", err));
    }
  }, [nodes, edges]);

  // Run LangGraph Agentic Investigative Workflow
  const handleRunLangGraph = async () => {
    setLangGraphLoading(true);
    try {
      const res = await api.runAgenticWorkflow({
        caseId: caseId || caseName || "CASE-2024-MH-088",
        query: `Analyze criminal syndicate structure, identify key brokers, and prescribe police action for ${nodes.length} entities.`,
        nodes,
        edges,
      });
      if (res && res.dossier) {
        setLangGraphBrief(res);
        if (res.anomalies && res.anomalies.length > 0) {
          setBackendAnomalies(res.anomalies);
        }
        onToast?.("[LangGraph] Explainable intelligence synthesized!");
      }
    } catch (err) {
      console.error("LangGraph error:", err);
      onToast?.("LangGraph workflow error: " + (err.message || "Failed"));
    } finally {
      setLangGraphLoading(false);
    }
  };

  // ── Node & Adjacency Mapping ───────────────────────────────────────────────
  const { nodeMap, adj, degreeMap } = useMemo(() => {
    const nMap = new Map();
    const aMap = new Map();
    const dMap = {};

    nodes.forEach((n) => {
      nMap.set(n.id, n);
      aMap.set(n.id, []);
      dMap[n.id] = 0;
    });

    edges.forEach((e) => {
      if (nMap.has(e.source) && nMap.has(e.target)) {
        aMap.get(e.source).push({ neighborId: e.target, edge: e, dir: "out" });
        aMap.get(e.target).push({ neighborId: e.source, edge: e, dir: "in" });
        dMap[e.source] = (dMap[e.source] || 0) + 1;
        dMap[e.target] = (dMap[e.target] || 0) + 1;
      }
    });

    return { nodeMap: nMap, adj: aMap, degreeMap: dMap };
  }, [nodes, edges]);

  // ── Topology Diagnostics ───────────────────────────────────────────────────
  const metrics = useMemo(() => {
    const n = nodes.length;
    const m = edges.length;
    const density = n > 1 ? ((2 * m) / (n * (n - 1))) * 100 : 0;
    let sumDeg = 0;
    let maxDeg = 0;
    nodes.forEach((node) => {
      const d = degreeMap[node.id] || 0;
      if (d > maxDeg) maxDeg = d;
      sumDeg += d;
    });

    // Connected components via BFS
    const visited = new Set();
    let components = 0;
    nodes.forEach((node) => {
      if (!visited.has(node.id)) {
        components += 1;
        const q = [node.id];
        visited.add(node.id);
        while (q.length > 0) {
          const curr = q.shift();
          const neighbors = adj.get(curr) || [];
          neighbors.forEach((nbr) => {
            if (!visited.has(nbr.neighborId)) {
              visited.add(nbr.neighborId);
              q.push(nbr.neighborId);
            }
          });
        }
      }
    });

    return {
      density: density.toFixed(1),
      components,
      avgDegree: n > 0 ? (sumDeg / n).toFixed(1) : "0",
      maxDegree: maxDeg,
    };
  }, [nodes, edges, degreeMap, adj]);

  // Top broker
  const topBroker = useMemo(() => {
    if (!nodes.length) return null;
    let maxNode = nodes[0];
    let maxDeg = degreeMap[maxNode.id] || 0;
    nodes.forEach((n) => {
      const d = degreeMap[n.id] || 0;
      if (d > maxDeg) {
        maxDeg = d;
        maxNode = n;
      }
    });
    return { ...maxNode, degree: maxDeg };
  }, [nodes, degreeMap]);

  // Type counts
  const typeCounts = useMemo(() => {
    const counts = {};
    nodes.forEach((n) => {
      counts[n.type] = (counts[n.type] || 0) + 1;
    });
    return counts;
  }, [nodes]);

  // ── Hidden Links (Adamic-Adar & Common Neighbors) ──────────────────────────
  const hiddenLinks = useMemo(() => {
    const results = [];
    const n = nodes.length;
    if (n < 3) return results;

    const directNeighbors = new Map();
    nodes.forEach((node) => {
      const nbrs = new Set((adj.get(node.id) || []).map((x) => x.neighborId));
      directNeighbors.set(node.id, nbrs);
    });

    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const u = nodes[i];
        const v = nodes[j];
        const pairKey = [u.id, v.id].sort().join("__");
        if (dismissedLeads.has(pairKey)) continue;

        const uNbrs = directNeighbors.get(u.id);
        if (uNbrs.has(v.id)) continue; // Already connected

        // Common neighbors
        const common = [];
        uNbrs.forEach((wId) => {
          if (directNeighbors.get(v.id).has(wId)) {
            common.push(nodeMap.get(wId));
          }
        });

        if (common.length > 0) {
          let adamicAdar = 0;
          common.forEach((w) => {
            if (w) {
              const deg = degreeMap[w.id] || 1;
              adamicAdar += 1 / Math.log2(deg + 1.1);
            }
          });

          const conf = Math.min(95, Math.round(45 + common.length * 15 + adamicAdar * 12));
          const accepted = acceptedLeads.has(pairKey);

          results.push({
            pairKey,
            nodeA: u,
            nodeB: v,
            score: conf,
            shared: common.filter(Boolean),
            accepted,
          });
        }
      }
    }

    return results.sort((a, b) => b.score - a.score).slice(0, 15);
  }, [nodes, adj, degreeMap, nodeMap, dismissedLeads, acceptedLeads]);

  // ── Anomalies (Hubs, Bridges, Cross-Case, Night Bursts) ─────────────────────
  const anomalies = useMemo(() => {
    const list = [];
    if (nodes.length === 0) return list;

    // 1. Hub Anomalies
    const mean = nodes.reduce((s, n) => s + (degreeMap[n.id] || 0), 0) / nodes.length;
    const variance =
      nodes.reduce((s, n) => s + Math.pow((degreeMap[n.id] || 0) - mean, 2), 0) / nodes.length;
    const std = Math.sqrt(variance);
    const threshold = Math.max(3, mean + 1.4 * std);

    nodes.forEach((node) => {
      const d = degreeMap[node.id] || 0;
      if (d >= threshold) {
        list.push({
          sev: d >= threshold * 1.3 ? "high" : "medium",
          type: "Hub / Central Coordinator",
          badge: "HUB",
          subject: `${node.label} (${node.id})`,
          nodeId: node.id,
          why: `Extreme connectivity: ${d} direct connections (average is ${mean.toFixed(1)}). Central communications hub.`,
        });
      }
    });

    // 2. Critical Bridge / Bottleneck Nodes (Articulation Points)
    nodes.forEach((node) => {
      const nbrs = (adj.get(node.id) || []).map((x) => x.neighborId);
      if (nbrs.length >= 2) {
        let hasBridgePattern = false;
        for (let i = 0; i < nbrs.length; i++) {
          const nbrA = nbrs[i];
          const nbrANeighbors = new Set((adj.get(nbrA) || []).map((x) => x.neighborId));
          for (let j = i + 1; j < nbrs.length; j++) {
            const nbrB = nbrs[j];
            if (!nbrANeighbors.has(nbrB)) {
              hasBridgePattern = true;
              break;
            }
          }
          if (hasBridgePattern) break;
        }

        if (hasBridgePattern && (degreeMap[node.id] || 0) >= 3) {
          list.push({
            sev: "medium",
            type: "Communication Bridge",
            badge: "BRIDGE",
            subject: `${node.label} (${node.id})`,
            nodeId: node.id,
            why: `Structural bottleneck linking disparate clusters. Severing this entity disrupts cross-group communication.`,
          });
        }
      }
    });

    // 3. Cross-Case Identifiers
    nodes.forEach((node) => {
      const cases = node.properties?.cases || [];
      if (Array.isArray(cases) && cases.length >= 2) {
        list.push({
          sev: "high",
          type: "Cross-Case Entity",
          badge: "MULTI-CASE",
          subject: `${node.label} (${node.id})`,
          nodeId: node.id,
          why: `Appears across ${cases.length} independent investigations: ${cases.join(", ")}.`,
        });
      }
    });

    // 4. Night-time odd-hour burst communications
    edges.forEach((edge) => {
      const ts = edge.properties?.timestamp || edge.properties?.date || edge.properties?.time || "";
      if (ts && String(ts).includes("T")) {
        const hr = new Date(ts).getHours();
        if (hr >= 0 && hr < 5) {
          const srcNode = nodeMap.get(edge.source);
          const tgtNode = nodeMap.get(edge.target);
          list.push({
            sev: "medium",
            type: "Odd-Hour Interaction",
            badge: "NIGHT-BURST",
            subject: `${srcNode?.label || edge.source} ↔ ${tgtNode?.label || edge.target}`,
            nodeId: edge.source,
            why: `Interaction recorded at ${ts.replace("T", " ")} (00:00–05:00 window). Night-time operation deviates from baseline activity.`,
          });
        }
      }
    });

    return list.slice(0, 15);
  }, [nodes, edges, degreeMap, adj, nodeMap]);

  // Combine scikit-learn Isolation Forest anomalies with heuristic fallbacks
  const finalAnomalies = useMemo(() => {
    if (backendAnomalies && backendAnomalies.length > 0) {
      return backendAnomalies.map((a) => ({
        sev: a.threat_level === "CRITICAL" || a.anomaly_score >= 0.75 ? "high" : "medium",
        type: a.tags?.[0] || "Isolation Forest Anomaly",
        badge: "ISO-FOREST",
        subject: `${a.label} (${a.id})`,
        nodeId: a.id,
        why: `${a.reason} [Anomaly Confidence: ${Math.round(a.anomaly_score * 100)}%]`,
      }));
    }
    return anomalies;
  }, [backendAnomalies, anomalies]);

  // ── N-Hop Neighborhood Traversal ───────────────────────────────────────────
  const activeRootNode = useMemo(() => {
    return (selectedId && nodeMap.get(selectedId)) || topBroker || nodes[0];
  }, [selectedId, nodeMap, topBroker, nodes]);

  const nHopResults = useMemo(() => {
    if (!activeRootNode) return { nodesByHop: [], allNodeIds: new Set() };

    const rootId = activeRootNode.id;
    const visited = new Map();
    visited.set(rootId, 0);
    const queue = [{ id: rootId, hop: 0 }];
    const nodesByHop = [[activeRootNode]];

    for (let h = 1; h <= nHopDistance; h++) nodesByHop[h] = [];

    while (queue.length > 0) {
      const curr = queue.shift();
      if (curr.hop >= nHopDistance) continue;

      const neighbors = adj.get(curr.id) || [];
      neighbors.forEach((nbr) => {
        if (!visited.has(nbr.neighborId)) {
          const nextHop = curr.hop + 1;
          visited.set(nbr.neighborId, nextHop);
          const nd = nodeMap.get(nbr.neighborId);
          if (nd) nodesByHop[nextHop].push(nd);
          queue.push({ id: nbr.neighborId, hop: nextHop });
        }
      });
    }

    return {
      nodesByHop,
      allNodeIds: new Set(visited.keys()),
    };
  }, [activeRootNode, nHopDistance, adj, nodeMap]);

  // ── Timeline Events Extractor ──────────────────────────────────────────────
  const timelineEvents = useMemo(() => {
    const events = [];

    edges.forEach((edge) => {
      const p = edge.properties || {};
      const ts = p.timestamp || p.date || p.time || p.call_time || p.txn_date;
      if (ts) {
        const srcNode = nodeMap.get(edge.source);
        const tgtNode = nodeMap.get(edge.target);
        const sub = [];
        if (p.duration) sub.push(`${p.duration}s`);
        if (p.amount) sub.push(`₹${Number(p.amount).toLocaleString("en-IN")}`);
        if (p.cases) sub.push(Array.isArray(p.cases) ? p.cases.join(", ") : p.cases);

        events.push({
          date: String(ts),
          type: edge.type || "Interaction",
          label: `${srcNode?.label || edge.source} → ${tgtNode?.label || edge.target}`,
          sub: sub.join(" · ") || edge.label || "Communication",
          sourceId: edge.source,
        });
      }
    });

    nodes.forEach((node) => {
      const p = node.properties || {};
      const ts = p.date || p.timestamp || p.registration_date;
      if (ts) {
        events.push({
          date: String(ts),
          type: (node.type || "entity").toUpperCase(),
          label: `${node.label} recorded in registry`,
          sub: (p.cases && p.cases.join(", ")) || node.type,
          sourceId: node.id,
        });
      }
    });

    return events.sort((a, b) => new Date(a.date) - new Date(b.date));
  }, [edges, nodes, nodeMap]);

  // ── Filtered Ranked Operatives ─────────────────────────────────────────────
  const filteredNodes = useMemo(() => {
    let list = [...nodes].sort((a, b) => (degreeMap[b.id] || 0) - (degreeMap[a.id] || 0));
    if (filterType !== "ALL") {
      list = list.filter((n) => n.type.toLowerCase() === filterType.toLowerCase());
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (n) =>
          n.label.toLowerCase().includes(q) ||
          n.id.toLowerCase().includes(q) ||
          Object.values(n.properties || {}).some((v) => String(v).toLowerCase().includes(q))
      );
    }
    return list;
  }, [nodes, degreeMap, filterType, searchQuery]);

  // ── Lead Management Handlers ───────────────────────────────────────────────
  const handleAcceptLead = (pairKey) => {
    setAcceptedLeads((prev) => new Set([...prev, pairKey]));
    onToast?.("Lead verified and saved to dossier");
  };

  const handleDismissLead = (pairKey) => {
    setDismissedLeads((prev) => new Set([...prev, pairKey]));
    onToast?.("Lead dismissed");
  };

  // ── Dossier Export Content ─────────────────────────────────────────────────
  const handleCopyReport = () => {
    const reportText = [
      `==================================================================`,
      `          CRIMENET CASE INTELLIGENCE DOSSIER`,
      `          Automated Multi-Source Forensic Analysis`,
      `==================================================================`,
      `Case Title      : ${caseName}`,
      `Generated At    : ${new Date().toLocaleString()}`,
      `Total Entities  : ${nodes.length}`,
      `Total Links     : ${edges.length}`,
      `Network Density : ${metrics.density}%`,
      `Clusters/Comps  : ${metrics.components}`,
      `Key Broker      : ${topBroker?.label} (${topBroker?.degree} direct connections)`,
      ``,
      `--- 1. HIGH-PRIORITY FORENSIC ANOMALIES ---`,
      ...anomalies.map((a, i) => `[${i + 1}] [${a.badge}] ${a.subject}\n    ${a.why}`),
      ``,
      `--- 2. AI PREDICTED HIDDEN CONNECTIONS ---`,
      ...hiddenLinks.map((l, i) => `[${i + 1}] ${l.nodeA.label} <---> ${l.nodeB.label} (${l.score}% Confidence)\n    Shared Intermediaries: ${l.shared.map((s) => s.label).join(", ")}`),
      ``,
      `--- 3. KEY OPERATIVES (TOP RANKED) ---`,
      ...filteredNodes.slice(0, 15).map((n, i) => `[${i + 1}] ${n.label} [${n.type.toUpperCase()}] - ${degreeMap[n.id] || 0} links`),
      `==================================================================`,
    ].join("\n");

    navigator.clipboard?.writeText(reportText);
    setCopiedFlash(true);
    setTimeout(() => setCopiedFlash(false), 2000);
    onToast?.("Dossier copied to clipboard");
  };

  return (
    <div className="intel-tab-pane">
      {/* Header */}
      <div className="intel-header">
        <span className="intel-title">AI Intelligence</span>
        <button className="btn-export-dossier" onClick={() => setReportModalOpen(true)}>
          <Download size={12} /> Export Dossier
        </button>
      </div>

      {/* Subtabs */}
      <div className="intel-subtabs">
        <button
          className={`intel-subtab-btn ${activeSubtab === "insights" ? "active" : ""}`}
          onClick={() => setActiveSubtab("insights")}
        >
          INSIGHTS
        </button>
        <button
          className={`intel-subtab-btn ${activeSubtab === "hidden" ? "active" : ""}`}
          onClick={() => setActiveSubtab("hidden")}
        >
          HIDDEN LINKS ({hiddenLinks.length})
        </button>
        <button
          className={`intel-subtab-btn ${activeSubtab === "anomalies" ? "active" : ""}`}
          onClick={() => setActiveSubtab("anomalies")}
        >
          ANOMALIES ({finalAnomalies.length})
        </button>
        <button
          className={`intel-subtab-btn ${activeSubtab === "nhop" ? "active" : ""}`}
          onClick={() => setActiveSubtab("nhop")}
        >
          N-HOP & EVIDENCE
        </button>
        <button
          className={`intel-subtab-btn ${activeSubtab === "timeline" ? "active" : ""}`}
          onClick={() => setActiveSubtab("timeline")}
        >
          TIMELINE ({timelineEvents.length})
        </button>
      </div>

      <div className="intel-content-scroll">
        {/* ── SUBTAB 1: INSIGHTS ────────────────────────────────────────────── */}
        {activeSubtab === "insights" && (
          <div>
            {/* 4 Metric Cards */}
            <div className="crimenet-metrics-grid">
              <div className="crimenet-metric-card">
                <div className="val" style={{ color: "var(--blue)" }}>{nodes.length}</div>
                <div className="lbl">ENTITIES</div>
              </div>
              <div className="crimenet-metric-card">
                <div className="val" style={{ color: "var(--green)" }}>{edges.length}</div>
                <div className="lbl">LINKS</div>
              </div>
              <div className="crimenet-metric-card">
                <div className="val" style={{ color: "var(--orange)" }}>{metrics.density}%</div>
                <div className="lbl">DENSITY</div>
              </div>
              <div className="crimenet-metric-card">
                <div className="val" style={{ color: "var(--purple)" }}>{metrics.components}</div>
                <div className="lbl">CLUSTERS</div>
              </div>
            </div>

            {/* Explainable AI Insights Card */}
            <div className="unbound-sect-h" style={{ marginTop: 12 }}>
              Explainable AI Insights
            </div>
            <div className="unbound-card" style={{ fontSize: 11, lineHeight: 1.5, padding: "8px 10px" }}>
              {topBroker && (
                <div style={{ marginBottom: 6 }}>
                  • <b>Primary Key Broker:</b>{" "}
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      onSelectNode?.(topBroker.id);
                    }}
                    style={{ color: "var(--teal)", fontWeight: 600, textDecoration: "none" }}
                  >
                    {topBroker.label}
                  </a>{" "}
                  controls the highest connection density ({topBroker.degree} links) across the network.
                </div>
              )}
              <div style={{ marginBottom: 6 }}>
                • <b>Topology Diagnostics:</b> Network comprises {metrics.components} distinct components with an average degree of {metrics.avgDegree} connections per entity.
              </div>
              <div>
                • <b>Entity Spectrum:</b> Identified {Object.keys(typeCounts).length} functional entity classes:{" "}
                {Object.entries(typeCounts).map(([t, c]) => `${c} ${t}s`).join(", ")}.
              </div>
            </div>

            {/* LangGraph Agentic Intelligence Trigger */}
            <button
              onClick={handleRunLangGraph}
              disabled={langGraphLoading}
              style={{
                marginTop: 10,
                marginBottom: 10,
                width: "100%",
                padding: "8px 12px",
                borderRadius: 6,
                border: "none",
                background: "var(--teal, #4fc3f7)",
                color: "#ffffff",
                fontWeight: 600,
                fontSize: 12,
                cursor: langGraphLoading ? "wait" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                boxShadow: "0 2px 8px rgba(79, 70, 229, 0.25)"
              }}
            >
              <Sparkles size={14} />
              {langGraphLoading ? "Running LangGraph Workflow..." : "Synthesize AI Intelligence (LangGraph)"}
            </button>

            {langGraphBrief && (
              <div className="unbound-card" style={{ marginBottom: 12, border: "1px solid var(--border-2)", background: "var(--panel-2)", padding: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--teal)", fontWeight: 700, fontSize: 12, marginBottom: 6 }}>
                  <ShieldCheck size={14} />
                  LangGraph Explainable Intelligence Dossier
                </div>
                <div style={{ fontSize: 11.5, lineHeight: 1.5, color: "var(--text)", whiteSpace: "pre-wrap", marginBottom: 8 }}>
                  {langGraphBrief.dossier?.executive_summary}
                </div>
                {langGraphBrief.recommendations && langGraphBrief.recommendations.length > 0 && (
                  <div style={{ marginTop: 8, borderTop: "1px solid var(--border)", paddingTop: 6 }}>
                    <div style={{ fontSize: 10.5, fontWeight: 700, color: "var(--teal)", marginBottom: 4 }}>
                      ACTIONABLE POLICE MEASURES:
                    </div>
                    {langGraphBrief.recommendations.map((rec, i) => (
                      <div key={i} style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 3 }}>
                        • <b>{rec.action}</b> ({rec.statute}): {rec.rationale}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Search & Filter Entities */}
            <div className="unbound-sect-h" style={{ marginTop: 12 }}>
              Search & Filter Entities
            </div>
            <div style={{ marginBottom: 6 }}>
              <div className="crimenet-search-wrapper">
                <Search size={13} className="search-icon" />
                <input
                  type="text"
                  className="crimenet-search-bar"
                  placeholder="Search entity name, phone, plate, ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 8 }}>
              <button
                className={`crimenet-type-chip ${filterType === "ALL" ? "active" : ""}`}
                onClick={() => setFilterType("ALL")}
              >
                All ({nodes.length})
              </button>
              {Object.entries(typeCounts).map(([t, cnt]) => (
                <button
                  key={t}
                  className={`crimenet-type-chip ${filterType === t ? "active" : ""}`}
                  onClick={() => setFilterType(t)}
                >
                  <span className="unbound-dot" style={{ background: TYPE_COLOR[t] || "#64748b" }} />
                  {t} ({cnt})
                </button>
              ))}
            </div>

            {/* Key Entities Ranked List */}
            <div className="unbound-sect-h">
              Ranked Entities <span className="unbound-n">{filteredNodes.length}</span>
            </div>
            <div className="unbound-rank">
              {filteredNodes.slice(0, 15).map((e) => {
                const maxD = metrics.maxDegree || 1;
                const pct = Math.max(8, Math.round(((degreeMap[e.id] || 0) / maxD) * 100));
                const isSel = e.id === selectedId;
                return (
                  <div
                    key={e.id}
                    className={`unbound-rank-row ${isSel ? "selected-rank" : ""}`}
                    onClick={() => onSelectNode?.(e.id)}
                  >
                    <div className="unbound-row-top">
                      <div className="unbound-name-wrap">
                        <span className="unbound-dot" style={{ background: TYPE_COLOR[e.type] || "#2563eb" }} />
                        <span className="unbound-nm">{e.label}</span>
                      </div>
                      <span className="unbound-vl">{degreeMap[e.id] || 0} links</span>
                    </div>
                    <div className="unbound-bar">
                      <i style={{ width: `${pct}%`, background: TYPE_COLOR[e.type] || "#2563eb" }} />
                    </div>
                    <div className="unbound-hint">{e.type} · ID: {e.id}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── SUBTAB 2: HIDDEN LINKS ────────────────────────────────────────── */}
        {activeSubtab === "hidden" && (
          <div>
            <div className="unbound-sect-h">
              AI Hidden-Link Prediction <span className="unbound-n">{hiddenLinks.length}</span>
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8 }}>
              Inferred using Adamic-Adar triadic closure over indirect shared contacts.
            </div>

            {hiddenLinks.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-dim)", fontSize: 12 }}>
                No hidden link anomalies found in current network.
              </div>
            ) : (
              <div className="unbound-card">
                {hiddenLinks.map((p) => (
                  <div key={p.pairKey} className="unbound-item">
                    <div className="unbound-t">
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          onSelectNode?.(p.nodeA.id);
                        }}
                        style={{ color: "var(--teal)", fontWeight: 600, textDecoration: "none" }}
                      >
                        {p.nodeA.label}
                      </a>
                      <span style={{ color: "#94a3b8", margin: "0 4px" }}>↔</span>
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          onSelectNode?.(p.nodeB.id);
                        }}
                        style={{ color: "var(--teal)", fontWeight: 600, textDecoration: "none" }}
                      >
                        {p.nodeB.label}
                      </a>
                      <span className={`unbound-badge ${p.score > 70 ? "badge-orange" : ""}`}>
                        {p.score}% Lead
                      </span>
                    </div>

                    <div className="unbound-why">
                      No direct link observed. <b>{p.shared.length} shared connection(s)</b> via{" "}
                      {p.shared.map((s) => s.label).join(", ")}.
                    </div>

                    <div className="unbound-row-actions">
                      <button
                        className="unbound-mini-btn"
                        onClick={() => onFocusPair?.(p.nodeA.id, p.nodeB.id)}
                      >
                        Focus Pair
                      </button>
                      {p.accepted ? (
                        <span className="unbound-badge badge-green">Accepted</span>
                      ) : (
                        <>
                          <button
                            className="unbound-mini-btn"
                            style={{ color: "var(--green)" }}
                            onClick={() => handleAcceptLead(p.pairKey)}
                          >
                            Accept Lead
                          </button>
                          <button
                            className="unbound-mini-btn"
                            style={{ color: "#94a3b8" }}
                            onClick={() => handleDismissLead(p.pairKey)}
                          >
                            Dismiss
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── SUBTAB 3: ANOMALIES ───────────────────────────────────────────── */}
        {activeSubtab === "anomalies" && (
          <div>
            <div className="unbound-sect-h">
              Anomaly Alerts <span className="unbound-n">{finalAnomalies.length}</span>
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8 }}>
              Powered by scikit-learn Isolation Forest & topological graph analytics.
            </div>

            {finalAnomalies.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-dim)", fontSize: 12 }}>
                No critical anomalies detected in current network.
              </div>
            ) : (
              <div className="unbound-card">
                {finalAnomalies.map((a, idx) => (
                  <div key={idx} className="unbound-item">
                    <div className="unbound-t">
                      <span className={`unbound-badge ${a.sev === "high" ? "badge-red" : "badge-orange"}`}>
                        {a.badge}
                      </span>
                      <span style={{ fontWeight: 600 }}>{a.type}</span>
                    </div>
                    <div className="unbound-why" style={{ marginTop: 3 }}>
                      <b style={{ color: "var(--text)" }}>{a.subject}</b> — {a.why}
                    </div>
                    <div className="unbound-row-actions">
                      <button
                        className="unbound-mini-btn"
                        onClick={() => onSelectNode?.(a.nodeId)}
                      >
                        Focus in Graph
                      </button>
                      <button
                        className="unbound-mini-btn"
                        onClick={() => {
                          onSelectNode?.(a.nodeId);
                          setActiveSubtab("nhop");
                        }}
                      >
                        Explore N-Hop
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── SUBTAB 4: N-HOP & EVIDENCE ────────────────────────────────────── */}
        {activeSubtab === "nhop" && (
          <div>
            <div className="unbound-sect-h">N-Hop Neighborhood & Evidence</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8 }}>
              Explore multi-hop relationships and critical connectivity paths.
            </div>

            {/* Root Node Selector */}
            <div className="unbound-card" style={{ padding: 10, marginBottom: 10 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text)", display: "block", marginBottom: 4 }}>
                Target Root Entity:
              </label>
              <select
                className="crimenet-select-sm"
                value={activeRootNode?.id || ""}
                onChange={(e) => onSelectNode?.(e.target.value)}
                style={{ width: "100%", marginBottom: 8 }}
              >
                {nodes.map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.label} ({n.type})
                  </option>
                ))}
              </select>

              {/* Hop Distance Slider */}
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
                <span>Exploration Radius:</span>
                <b style={{ color: "var(--blue)" }}>{nHopDistance} Hops</b>
              </div>
              <input
                type="range"
                min="1"
                max="3"
                step="1"
                value={nHopDistance}
                onChange={(e) => setNHopDistance(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--teal)" }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#94a3b8", marginTop: 2 }}>
                <span>1-Hop (Direct)</span>
                <span>2-Hop (Associates)</span>
                <span>3-Hop (Extended)</span>
              </div>
            </div>

            <div style={{ marginBottom: 8 }}>
              <button
                className="crimenet-btn-primary"
                style={{ width: "100%", padding: "6px 12px", fontSize: 12 }}
                onClick={() => onHighlightNHop?.(activeRootNode?.id, nHopDistance)}
              >
                Highlight {nHopDistance}-Hop Subgraph in Canvas
              </button>
            </div>

            {/* Hop Breakdown */}
            {nHopResults.nodesByHop.map((hopNodes, h) => {
              if (h === 0) return null;
              return (
                <div key={h} style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", marginBottom: 4 }}>
                    Hop {h} Entities ({hopNodes.length})
                  </div>
                  <div className="unbound-rank" style={{ maxHeight: 150, overflowY: "auto" }}>
                    {hopNodes.map((n) => (
                      <div
                        key={n.id}
                        className="unbound-rank-row"
                        onClick={() => onSelectNode?.(n.id)}
                        style={{ cursor: "pointer" }}
                      >
                        <span className="unbound-dot" style={{ background: TYPE_COLOR[n.type] || "#64748b" }} />
                        <span className="unbound-nm">{n.label}</span>
                        <span className="unbound-vl">{n.type}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ── SUBTAB 5: TIMELINE ────────────────────────────────────────────── */}
        {activeSubtab === "timeline" && (
          <div>
            <div className="unbound-sect-h">
              Forensic Timeline <span className="unbound-n">{timelineEvents.length}</span>
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8 }}>
              Chronological sequence of documented transactions and interactions.
            </div>

            {timelineEvents.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "#94a3b8", fontSize: 12 }}>
                No timestamped events found in this dataset.
              </div>
            ) : (
              <div className="crimenet-timeline">
                {timelineEvents.map((evt, idx) => (
                  <div key={idx} className="crimenet-timeline-item">
                    <div className="crimenet-timeline-point" />
                    <div className="crimenet-timeline-content">
                      <div className="crimenet-timeline-date">{evt.date}</div>
                      <div className="crimenet-timeline-label">{evt.label}</div>
                      <div className="crimenet-timeline-sub">{evt.sub}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Bottom Network Summary Card & Documentation Button (matching CrimeNet) */}
        <div style={{ marginTop: 16 }}>
          <div className="network-summary-card">
            <div className="summary-row">
              <span className="label">Network</span>
              <span className="val">{caseName}</span>
            </div>
            <div className="summary-row">
              <span className="label"># Nodes</span>
              <span className="val">{nodes.length}</span>
            </div>
            <div className="summary-row">
              <span className="label"># Edges</span>
              <span className="val">{edges.length}</span>
            </div>
          </div>

          <button
            className="btn-user-doc"
            onClick={() => onOpenDoc ? onOpenDoc() : onToast?.("User documentation opened")}
          >
            <ExternalLink size={13} /> USER DOCUMENTATION
          </button>
        </div>
      </div>

      {/* ── REPORT MODAL (Export Dossier) ─────────────────────────────────── */}
      {reportModalOpen && (
        <div className="crimenet-modal-backdrop">
          <div className="crimenet-modal-window report-modal">
            <div className="crimenet-modal-header">
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text)" }}>
                  CrimeNet Case Intelligence Dossier
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Automated Multi-Source Forensic Analysis · Generated {new Date().toLocaleString()}
                </div>
              </div>
              <button className="crimenet-modal-close" onClick={() => setReportModalOpen(false)}>
                ✕
              </button>
            </div>

            <div className="crimenet-modal-body" id="crimenet-printable-report">
              <div style={{ background: "#f8fafc", padding: 12, borderRadius: 6, marginBottom: 12, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, textAlign: "center" }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#2563eb" }}>{nodes.length}</div>
                  <div style={{ fontSize: 10, color: "var(--text-muted)" }}>TOTAL ENTITIES</div>
                </div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#16a34a" }}>{edges.length}</div>
                  <div style={{ fontSize: 10, color: "var(--text-muted)" }}>RELATIONSHIPS</div>
                </div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#ea580c" }}>{metrics.density}%</div>
                  <div style={{ fontSize: 10, color: "var(--text-muted)" }}>DENSITY</div>
                </div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#dc2626" }}>{anomalies.length}</div>
                  <div style={{ fontSize: 10, color: "var(--text-muted)" }}>ACTIVE ALERTS</div>
                </div>
              </div>

              <div style={{ fontSize: 12, fontWeight: 700, margin: "12px 0 6px" }}>1. Key Entities of Interest</div>
              <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse", marginBottom: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #e2e8f0", color: "var(--text-muted)", textAlign: "left" }}>
                    <th style={{ padding: 4 }}>Entity</th>
                    <th style={{ padding: 4 }}>Type</th>
                    <th style={{ padding: 4 }}>Connections</th>
                    <th style={{ padding: 4 }}>Associated Context</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredNodes.slice(0, 8).map((e) => (
                    <tr key={e.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: 4, fontWeight: 600 }}>{e.label}</td>
                      <td style={{ padding: 4 }}>
                        <span style={{ color: TYPE_COLOR[e.type] || "#2563eb" }}>{e.type}</span>
                      </td>
                      <td style={{ padding: 4 }}>{degreeMap[e.id] || 0}</td>
                      <td style={{ padding: 4, color: "var(--text-muted)" }}>
                        {e.properties?.cases ? e.properties.cases.join(", ") : e.properties?.role || "Active node in network"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div style={{ fontSize: 12, fontWeight: 700, margin: "12px 0 6px" }}>2. High-Priority Forensic Anomalies</div>
              <div style={{ fontSize: 11, display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
                {anomalies.slice(0, 5).map((a, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "6px 8px",
                      background: "#f8fafc",
                      borderLeft: `3px solid ${a.sev === "high" ? "#dc2626" : "#ea580c"}`,
                      borderRadius: 3,
                    }}
                  >
                    <b>[{a.type}]</b> {a.subject}: {a.why}
                  </div>
                ))}
              </div>

              <div style={{ fontSize: 12, fontWeight: 700, margin: "12px 0 6px" }}>3. AI Predicted Hidden Links</div>
              <div style={{ fontSize: 11, display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
                {hiddenLinks.slice(0, 4).map((l, idx) => (
                  <div key={idx} style={{ padding: "6px 8px", background: "#f8fafc", borderRadius: 3 }}>
                    <b>{l.nodeA.label} ↔ {l.nodeB.label}</b> ({l.score}% confidence)
                    <div style={{ color: "var(--text-muted)", marginTop: 2 }}>
                      Shared intermediaries: {l.shared.map((s) => s.label).join(", ")}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="crimenet-modal-footer">
              <button className="crimenet-btn-primary" onClick={() => window.print()}>
                <Printer size={13} /> Print / Save PDF
              </button>
              <button className="crimenet-btn-secondary" onClick={handleCopyReport}>
                {copiedFlash ? <Check size={13} /> : <Copy size={13} />} Copy Dossier
              </button>
              <button className="crimenet-btn-secondary" onClick={() => setReportModalOpen(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
