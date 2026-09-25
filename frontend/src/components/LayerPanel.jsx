import React from "react";

const NODE_TYPES = [
  { key: "person", color: "#10b7a6" },
  { key: "location", color: "#f5a623" },
  { key: "object", color: "#7c5cbf" },
  { key: "event", color: "#2454ff" },
];

const EDGE_TYPES = ["prior_contact", "other_assoc", "visited", "owns", "linked_to"];

export default function LayerPanel({ visibleTypes, setVisibleTypes, showLabels, setShowLabels }) {
  const toggle = (key) => setVisibleTypes((v) => ({ ...v, [key]: v[key] === false ? true : false }));

  return (
    <div>
      <div className="panel-block">
        <div className="panel-title">Nodes</div>
        {NODE_TYPES.map((t) => (
          <div className="row" key={t.key}>
            <label>
              <input
                type="checkbox"
                checked={visibleTypes[t.key] !== false}
                onChange={() => toggle(t.key)}
              />
              <span className="swatch" style={{ background: t.color }} />
              {t.key}
            </label>
          </div>
        ))}
      </div>

      <div className="panel-block">
        <div className="panel-title">Edges</div>
        {EDGE_TYPES.map((e) => (
          <div className="row" key={e}>
            <label>
              <input type="checkbox" defaultChecked />
              <span className="swatch" style={{ background: "#c7cad1" }} />
              {e}
            </label>
          </div>
        ))}
      </div>

      <div className="panel-block">
        <div className="panel-title">Labels</div>
        <div className="row">
          <label>
            <input
              type="checkbox"
              checked={showLabels}
              onChange={() => setShowLabels((s) => !s)}
            />
            show name
          </label>
        </div>
      </div>
    </div>
  );
}
