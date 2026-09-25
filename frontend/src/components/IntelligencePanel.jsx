import React, { useState } from "react";
import {
  FileDown, Sparkles, Link2, TriangleAlert, Waypoints,
  Target, Crosshair, User, MapPin, Box, CalendarClock
} from "lucide-react";

const SUBTABS = [
  { key: "insights", label: "Insights", icon: Sparkles },
  { key: "hidden", label: "Hidden links", icon: Link2 },
  { key: "anomalies", label: "Anomalies", icon: TriangleAlert },
  { key: "nhop", label: "N-hop & evidence", icon: Waypoints },
];

const TYPE_ICON = { person: User, location: MapPin, object: Box, event: CalendarClock };

export default function IntelligencePanel({
  nodes, focusId, setFocusId, depth, setDepth, radiusCount,
  evidenceLinks, hiddenLinksCount, anomaliesCount, onHighlight, onCenter,
}) {
  const [sub, setSub] = useState("nhop");
  const focusNode = nodes.find((n) => n.id === focusId);

  return (
    <div>
      <div className="row" style={{ marginBottom: 10 }}>
        <div className="panel-title" style={{ marginBottom: 0 }}>AI intelligence</div>
        <button className="btn ghost" style={{ width: "auto", marginBottom: 0 }}>
          <FileDown size={14} /> Export dossier
        </button>
      </div>

      <div className="subtabs">
        {SUBTABS.map((t) => {
          const Icon = t.icon;
          const count = t.key === "hidden" ? hiddenLinksCount : t.key === "anomalies" ? anomaliesCount : null;
          return (
            <button
              key={t.key}
              className={`subtab ${sub === t.key ? "active" : ""}`}
              onClick={() => setSub(t.key)}
            >
              <Icon size={13} /> {t.label}
              {count != null && <span className="count">({count})</span>}
            </button>
          );
        })}
      </div>

      {sub === "insights" && (
        <div className="panel-block">
          <div className="panel-title">Summary</div>
          <p style={{ fontSize: 12.5, color: "var(--ink-soft)", lineHeight: 1.5, margin: 0 }}>
            Run an analysis to generate insights for this network.
          </p>
        </div>
      )}

      {sub === "hidden" && (
        <div className="panel-block">
          <div className="panel-title">Predicted links</div>
          <p style={{ fontSize: 12.5, color: "var(--ink-soft)", lineHeight: 1.5, margin: 0 }}>
            {hiddenLinksCount} candidate connections found. Run link prediction from the Analysis tab.
          </p>
        </div>
      )}

      {sub === "anomalies" && (
        <div className="panel-block">
          <div className="panel-title">Flagged entities</div>
          <p style={{ fontSize: 12.5, color: "var(--ink-soft)", lineHeight: 1.5, margin: 0 }}>
            {anomaliesCount} entities deviate from expected network patterns.
          </p>
        </div>
      )}

      {sub === "nhop" && (
        <>
          <div className="panel-block">
            <div className="panel-title">Focus entity</div>
            <select className="field" value={focusId || ""} onChange={(e) => setFocusId(e.target.value)}>
              <option value="" disabled>Choose entity…</option>
              {nodes.map((n) => <option key={n.id} value={n.id}>{n.label}</option>)}
            </select>

            <div className="panel-title">Depth</div>
            <div className="depth-row">
              {[1, 2, 3].map((d) => (
                <button
                  key={d}
                  className={`depth-btn ${depth === d ? "active" : ""}`}
                  onClick={() => setDepth(d)}
                >
                  {d}-hop
                </button>
              ))}
            </div>

            <p style={{ fontSize: 12, color: "var(--ink-soft)", margin: "0 0 10px" }}>
              {radiusCount} entities within {depth}-hop of {focusNode?.label || "—"}.
            </p>

            <button className="btn primary" onClick={onHighlight}>
              <Target size={13} /> Highlight subgraph
            </button>
            <button className="btn" onClick={onCenter}>
              <Crosshair size={13} /> Center
            </button>
          </div>

          {focusNode && (
            <div className="evidence-card">
              <div className="evidence-head">
                <span className="dot" />
                <b>{focusNode.label}</b>
                <span className="pill blue">{focusNode.type}</span>
              </div>
              <div className="evidence-attr"><b>flight:</b> {focusNode.flight}</div>
              <div className="evidence-attr"><b>risk:</b> {focusNode.risk}</div>

              <div className="panel-title" style={{ marginTop: 10 }}>
                Direct links ({evidenceLinks.length})
              </div>
              <div className="link-list">
                {evidenceLinks.map((l) => {
                  const Icon = TYPE_ICON[l.type] || User;
                  return (
                    <div className="link-item" key={l.id + l.edgeLabel}>
                      <a href="#" onClick={(e) => { e.preventDefault(); setFocusId(l.id); }}>
                        <Icon size={12} style={{ verticalAlign: -2, marginRight: 4 }} />
                        {l.label}
                      </a>
                      <span className="pill">{l.edgeLabel}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
