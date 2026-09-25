import React, { useState } from "react";
import { X, Plus, Trash2, PlusCircle, Network } from "lucide-react";

const NODE_TYPES = [
  "person", "phone", "vehicle", "location", "organization",
  "bank", "account", "case", "fir", "entity"
];

const EDGE_TYPES = [
  "connected_to", "call", "transaction", "co_offender", "family",
  "associate", "prior_contact", "travel_with", "suspect_in"
];

export default function AddElementModal({
  isOpen,
  onClose,
  nodes = [],
  onAddNode,
  onAddEdge,
}) {
  const [tab, setTab] = useState("node"); // "node" | "edge"

  // Node fields
  const [nodeType, setNodeType] = useState("person");
  const [nodeName, setNodeName] = useState("");
  const [nodeProps, setNodeProps] = useState([]);
  const [propKey, setPropKey] = useState("");
  const [propVal, setPropVal] = useState("");

  // Edge fields
  const [edgeType, setEdgeType] = useState("connected_to");
  const [sourceNode, setSourceNode] = useState(nodes[0]?.id || "");
  const [targetNode, setTargetNode] = useState(nodes[1]?.id || nodes[0]?.id || "");
  const [edgeWeight, setEdgeWeight] = useState(1);

  const handleAddProp = () => {
    if (!propKey.trim()) return;
    setNodeProps((prev) => [
      ...prev,
      { key: propKey.trim(), value: propVal.trim() },
    ]);
    setPropKey("");
    setPropVal("");
  };

  const handleRemoveProp = (index) => {
    setNodeProps((prev) => prev.filter((_, i) => i !== index));
  };

  const handleApply = () => {
    if (tab === "node") {
      const name = nodeName.trim() || `New_${nodeType}_${Date.now().toString().slice(-4)}`;
      const id = name.replace(/\s+/g, "_");
      const properties = {
        name,
        type: nodeType,
      };
      nodeProps.forEach((p) => {
        if (p.key.trim()) properties[p.key.trim()] = p.value;
      });

      onAddNode?.({
        id,
        label: name,
        type: nodeType,
        properties,
      });
    } else {
      if (!sourceNode || !targetNode) return;
      if (sourceNode === targetNode) {
        alert("Source and Target nodes must be different.");
        return;
      }
      onAddEdge?.({
        id: `e_${sourceNode}_${targetNode}_${Date.now()}`,
        source: sourceNode,
        target: targetNode,
        label: edgeType,
        type: edgeType,
        weight: Number(edgeWeight) || 1,
        properties: {
          type: edgeType,
          weight: Number(edgeWeight) || 1,
        },
      });
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="crimenet-modal-backdrop">
      <div className="crimenet-modal-window">
        <div className="crimenet-modal-header">
          <div className="crimenet-modal-title">
            <PlusCircle size={15} /> Add New Element
          </div>
          <button className="crimenet-modal-close" onClick={onClose}>
            <X size={15} />
          </button>
        </div>

        {/* Tab Switcher: Node vs Edge */}
        <div className="crimenet-modal-tabs">
          <button
            type="button"
            className={`crimenet-modal-tab ${tab === "node" ? "active" : ""}`}
            onClick={() => setTab("node")}
          >
            Node
          </button>
          <button
            type="button"
            className={`crimenet-modal-tab ${tab === "edge" ? "active" : ""}`}
            onClick={() => setTab("edge")}
          >
            Edge
          </button>
        </div>

        <div className="crimenet-modal-body">
          {tab === "node" ? (
            <>
              <div className="crimenet-modal-section">
                <label className="crimenet-field-label">Element Type</label>
                <select
                  className="crimenet-select"
                  value={nodeType}
                  onChange={(e) => setNodeType(e.target.value)}
                >
                  {NODE_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div className="crimenet-modal-section">
                <label className="crimenet-field-label">Element Name / Label</label>
                <input
                  type="text"
                  className="crimenet-text-input"
                  placeholder="Name (e.g. John Doe, 9876543210, FIR-01)..."
                  value={nodeName}
                  onChange={(e) => setNodeName(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="crimenet-modal-divider" />

              {/* Properties */}
              <div className="crimenet-modal-section">
                <label className="crimenet-field-label">Properties</label>
                {nodeProps.map((p, idx) => (
                  <div key={idx} className="crimenet-prop-row">
                    <span className="crimenet-prop-tag">{p.key}: {p.value}</span>
                    <button
                      type="button"
                      className="crimenet-row-btn remove"
                      onClick={() => handleRemoveProp(idx)}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}

                <div className="crimenet-add-prop-inline">
                  <input
                    type="text"
                    className="crimenet-text-input-sm"
                    placeholder="Property name..."
                    value={propKey}
                    onChange={(e) => setPropKey(e.target.value)}
                  />
                  <input
                    type="text"
                    className="crimenet-text-input-sm"
                    placeholder="Value..."
                    value={propVal}
                    onChange={(e) => setPropVal(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddProp()}
                  />
                  <button
                    type="button"
                    className="crimenet-btn-plus"
                    onClick={handleAddProp}
                    title="Add property"
                  >
                    <Plus size={14} />
                  </button>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="crimenet-modal-section">
                <label className="crimenet-field-label">Edge Type / Relationship</label>
                <select
                  className="crimenet-select"
                  value={edgeType}
                  onChange={(e) => setEdgeType(e.target.value)}
                >
                  {EDGE_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div className="crimenet-modal-section">
                <label className="crimenet-field-label">Source Node</label>
                <select
                  className="crimenet-select"
                  value={sourceNode}
                  onChange={(e) => setSourceNode(e.target.value)}
                >
                  {nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.label || n.id} ({n.type})
                    </option>
                  ))}
                </select>
              </div>

              <div className="crimenet-modal-section">
                <label className="crimenet-field-label">Target Node</label>
                <select
                  className="crimenet-select"
                  value={targetNode}
                  onChange={(e) => setTargetNode(e.target.value)}
                >
                  {nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.label || n.id} ({n.type})
                    </option>
                  ))}
                </select>
              </div>

              <div className="crimenet-modal-section">
                <label className="crimenet-field-label">Weight / Strength</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="10"
                  className="crimenet-text-input"
                  value={edgeWeight}
                  onChange={(e) => setEdgeWeight(e.target.value)}
                />
              </div>
            </>
          )}
        </div>

        <div className="crimenet-modal-footer">
          <button
            type="button"
            className="crimenet-btn-secondary"
            onClick={onClose}
          >
            Close
          </button>
          <button
            type="button"
            className="crimenet-btn-primary"
            onClick={handleApply}
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}
