/**
 * NodeDetailPanel.jsx — CrimeNet AI Node Detail & Forensic Dossier
 * Shows: label, type badge, risk pill, properties, connections,
 * AI Plain English intelligence summary, sources cited, and 1-click police action dispatchers.
 */

import React, { useState, useEffect } from "react";
import { Copy, FileText, Sparkles, ShieldAlert, DollarSign, Send, CheckCircle2, Loader2, ArrowRight } from "lucide-react";
import { TYPE_COLOR } from "./ReactFlowGraph";
import { api } from "../lib/api";

const RISK_CLS = { high: "high", med: "med", low: "low" };

export default function NodeDetailPanel({
  nodes,
  edges,
  selectedId,
  analysisScores,
  annotations,
  onAnnotate,
  onSelectNode,
  onNotify,
  onHighlightPath,
  caseId = "CASE-2024-MH-088",
}) {
  const [copyFlash, setCopyFlash] = useState(false);
  const [dossier, setDossier] = useState(null);
  const [loadingDossier, setLoadingDossier] = useState(false);
  const [actionStatus, setActionStatus] = useState(null);

  const node = nodes.find((n) => n.id === selectedId);

  // Fetch AI Dossier from FastAPI backend whenever selectedId changes
  useEffect(() => {
    if (!node) {
      setDossier(null);
      return;
    }

    let isMounted = true;
    setLoadingDossier(true);
    setActionStatus(null);

    api.getEntityDossier(node.id, caseId)
      .then((data) => {
        if (isMounted) setDossier(data);
      })
      .catch((err) => {
        console.warn("Could not fetch dossier from backend, using local fallback:", err);
        if (isMounted) {
          setDossier({
            name: node.label,
            type: node.type,
            threatLevel: node.threatLevel || "HIGH",
            threatScore: node.threatScore || 0.75,
            summary: `Investigative entity ${node.label} (${node.type}) actively mapped within the network.`,
            connectionsSummary: `Connected to ${edges.filter(e => e.source === node.id || e.target === node.id).length} links.`,
            recommendedActions: [
              { id: "LOC", title: "Issue Immediate Lookout Circular (LOC)", section: "Bureau of Immigration" },
              { id: "FREEZE", title: "Requisition Account Freeze", section: "Sec 102 CrPC" }
            ],
            sources: [{ doc: "Active Case File", citation: "Initial FIR Narrative" }]
          });
        }
      })
      .finally(() => {
        if (isMounted) setLoadingDossier(false);
      });

    return () => {
      isMounted = false;
    };
  }, [node?.id, caseId]);

  if (!node) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", gap: 8 }}>
        <FileText size={32} style={{ opacity: 0.3 }} />
        <span style={{ fontSize: 12 }}>Click a node to view details & AI dossier</span>
      </div>
    );
  }

  const color = TYPE_COLOR[node.type] || "#888";
  const score = analysisScores?.[node.id];

  // Neighbors
  const neighbors = edges
    .filter((e) => e.source === node.id || e.target === node.id)
    .map((e) => {
      const otherId = e.source === node.id ? e.target : e.source;
      const other = nodes.find((n) => n.id === otherId);
      return { id: otherId, label: other?.label ?? otherId, type: other?.type, edgeLabel: e.label };
    });

  const handleCopy = () => {
    navigator.clipboard?.writeText(node.id);
    setCopyFlash(true);
    setTimeout(() => setCopyFlash(false), 1400);
  };

  const handleDispatchAction = async (actionId, title) => {
    try {
      setActionStatus(`Dispatching: ${title}...`);
      const res = await api.dispatchAction(actionId, node.id, caseId);
      setActionStatus(`Dispatched: ${res.title} (Audit: ${res.auditId || "Logged"})`);
      onNotify?.(`Action Dispatched: ${res.title}`);
    } catch (err) {
      console.error(err);
      setActionStatus("Action failed: Backend offline");
    }
  };

  const handleFollowMoney = async () => {
    try {
      setActionStatus("Tracing financial flow 3 hops...");
      const res = await api.followTheMoney(node.id, caseId);
      if (res.highlightedNodeIds && onHighlightPath) {
        onHighlightPath(res.highlightedNodeIds);
      }
      setActionStatus(`Traced ${res.flowChain.length} hops: ${res.totalAmountFlagged}`);
      onNotify?.(`Financial Trace: ${res.flowChain.length} hops highlighted`);
    } catch (err) {
      console.error(err);
      setActionStatus("Financial trace failed");
    }
  };

  // All displayable properties
  // All displayable properties cleanly unpacked
  const props = [];
  Object.entries(node).forEach(([k, v]) => {
    if (["id", "label", "type", "threatLevel", "threatScore"].includes(k)) return;
    if (k === "properties" && typeof v === "object" && v !== null) {
      Object.entries(v).forEach(([pk, pv]) => {
        if (!["id", "label", "type", "name"].includes(pk)) {
          props.push([pk, Array.isArray(pv) ? pv.join(", ") : String(pv)]);
        }
      });
    } else if (typeof v === "object" && v !== null) {
      props.push([k, JSON.stringify(v)]);
    } else {
      props.push([k, String(v)]);
    }
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div className="node-detail-header">
        <div className="ndh-top">
          <div>
            <div className="ndh-label">{node.label}</div>
            <div className="ndh-meta" style={{ marginTop: 6 }}>
              <span
                className={`pill ${node.type}`}
                style={{ borderLeft: `3px solid ${color}` }}
              >
                {node.type}
              </span>
              <span className={`pill ${dossier?.threatLevel === "CRITICAL" ? "high" : "med"}`}>
                {dossier?.threatLevel || "ACTIVE"} THREAT
              </span>
              {neighbors.length > 0 && (
                <span className="pill muted">{neighbors.length} neighbors</span>
              )}
            </div>
          </div>
          <button
            className="icon-btn"
            onClick={handleCopy}
            title="Copy node ID"
            style={copyFlash ? { background: "var(--green-s)", borderColor: "var(--green)", color: "var(--green)" } : {}}
          >
            <Copy size={13} />
          </button>
        </div>

        {score != null && (
          <div style={{ marginTop: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>
              <span>Centrality score</span>
              <span style={{ color: "var(--orange)", fontWeight: 600 }}>{(score * 100).toFixed(1)}%</span>
            </div>
            <div className="result-bar-track">
              <div className="result-bar-fill" style={{ width: `${score * 100}%` }} />
            </div>
          </div>
        )}
      </div>

      <div className="panel-scroll" style={{ paddingBottom: 30 }}>
        {/* CrimeNet AI Intelligence Dossier */}
        <div className="panel-section" style={{ background: "rgba(37, 99, 235, 0.08)", border: "1px solid rgba(37, 99, 235, 0.25)", borderRadius: 6, padding: "10px 12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#38bdf8", fontWeight: 600, fontSize: 12, marginBottom: 6 }}>
            <Sparkles size={14} />
            <span>CrimeNet AI Dossier</span>
          </div>

          {loadingDossier ? (
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-muted)" }}>
              <Loader2 size={13} className="animate-spin" />
              <span>Synthesizing intelligence & citations...</span>
            </div>
          ) : (
            <div style={{ fontSize: 12, lineHeight: 1.5, color: "var(--text-primary)" }}>
              <p style={{ margin: "0 0 6px 0" }}>{dossier?.summary}</p>
              {dossier?.connectionsSummary && (
                <p style={{ margin: "0 0 6px 0", color: "var(--text-muted)", fontSize: 11 }}>
                  <strong>Associations:</strong> {dossier.connectionsSummary}
                </p>
              )}

              {/* Citations */}
              {dossier?.sources && dossier.sources.length > 0 && (
                <div style={{ marginTop: 8, borderTop: "1px dashed rgba(255,255,255,0.15)", paddingTop: 6 }}>
                  <div style={{ fontSize: 10, textTransform: "uppercase", color: "#f59e0b", fontWeight: 700, marginBottom: 4 }}>
                    Verified Sources Cited
                  </div>
                  {dossier.sources.map((s, idx) => (
                    <div key={idx} style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2 }}>
                      • <strong>{s.doc}</strong> ({s.citation})
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 1-Click Police Action Dispatchers */}
        <div className="panel-section">
          <div className="section-title">Investigative Actions</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {dossier?.recommendedActions?.map((act) => (
              <button
                key={act.id}
                onClick={() => handleDispatchAction(act.id, act.title)}
                className="btn"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: 11,
                  padding: "6px 10px",
                  background: act.id === "LOC" ? "rgba(239, 68, 68, 0.15)" : "var(--bg-tertiary)",
                  borderColor: act.id === "LOC" ? "#ef4444" : "var(--border-color)",
                  color: act.id === "LOC" ? "#fca5a5" : "var(--text-primary)",
                  borderRadius: 4,
                  cursor: "pointer"
                }}
              >
                <span>{act.title}</span>
                <Send size={11} />
              </button>
            ))}

            {(node.type === "ACCOUNT" || node.type === "PERSON") && (
              <button
                onClick={handleFollowMoney}
                className="btn"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: 11,
                  padding: "6px 10px",
                  background: "rgba(16, 185, 129, 0.15)",
                  borderColor: "#10b981",
                  color: "#6ee7b7",
                  borderRadius: 4,
                  cursor: "pointer"
                }}
              >
                <span>Follow the Money (3-Hop Trace)</span>
                <DollarSign size={12} />
              </button>
            )}

            {actionStatus && (
              <div style={{ fontSize: 11, color: "#10b981", marginTop: 4, display: "flex", alignItems: "center", gap: 4 }}>
                <CheckCircle2 size={12} />
                <span>{actionStatus}</span>
              </div>
            )}
          </div>
        </div>

        {/* Properties */}
        {props.length > 0 && (
          <div className="panel-section">
            <div className="section-title">Properties</div>
            <table className="prop-table">
              <tbody>
                {props.map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td style={{ fontFamily: typeof v === "string" && v.includes("@") ? "monospace" : undefined }}>
                      {String(v)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Neighbors */}
        {neighbors.length > 0 && (
          <div className="panel-section">
            <div className="section-title">Connections ({neighbors.length})</div>
            <div style={{ maxHeight: 200, overflowY: "auto" }}>
              {neighbors.map((nb, index) => (
                <div
                  key={`${nb.id}-${nb.edgeLabel}-${index}`}
                  className="neighbor-item"
                  onClick={() => onSelectNode?.(nb.id)}
                >
                  <span
                    className="ni-dot"
                    style={{ background: TYPE_COLOR[nb.type] || "#888" }}
                  />
                  <span className="ni-label">{nb.label}</span>
                  <span className="ni-edge">{nb.edgeLabel}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Annotation */}
        <div className="panel-section">
          <div className="section-title">Notes</div>
          <textarea
            className="field"
            placeholder="Add investigation notes…"
            value={annotations?.[node.id] || ""}
            onChange={(e) => onAnnotate?.(node.id, e.target.value)}
            style={{ minHeight: 80, fontSize: 12 }}
          />
        </div>
      </div>
    </div>
  );
}
