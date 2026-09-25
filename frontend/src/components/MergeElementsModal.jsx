import React, { useState } from "react";
import { X, Merge, GitMerge } from "lucide-react";

export default function MergeElementsModal({
  isOpen,
  onClose,
  nodes = [],
  selectedNodeId,
  onMerge,
}) {
  const [nodeAId, setNodeAId] = useState(selectedNodeId || nodes[0]?.id || "");
  const [nodeBId, setNodeBId] = useState(nodes[1]?.id || nodes[0]?.id || "");
  const [mergedName, setMergedName] = useState("");
  const [targetType, setTargetType] = useState("person");

  const nodeA = nodes.find((n) => n.id === nodeAId);
  const nodeB = nodes.find((n) => n.id === nodeBId);

  const handleApply = () => {
    if (!nodeAId || !nodeBId) return;
    if (nodeAId === nodeBId) {
      alert("Please select two distinct entities to merge.");
      return;
    }

    const finalName = mergedName.trim() || `${nodeA?.label || nodeAId} / ${nodeB?.label || nodeBId}`;
    const mergedId = `${nodeAId}__${nodeBId}`;

    // Combine properties
    const combinedProps = {
      ...(nodeB?.properties || {}),
      ...(nodeA?.properties || {}),
      name: finalName,
      type: targetType,
      merged_from: [nodeAId, nodeBId],
    };

    onMerge?.({
      keepId: mergedId,
      label: finalName,
      type: targetType,
      properties: combinedProps,
      removeIds: [nodeAId, nodeBId],
    });

    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="crimenet-modal-backdrop">
      <div className="crimenet-modal-window">
        <div className="crimenet-modal-header">
          <div className="crimenet-modal-title">
            <GitMerge size={15} /> Merge Selected Elements
          </div>
          <button className="crimenet-modal-close" onClick={onClose}>
            <X size={15} />
          </button>
        </div>

        <div className="crimenet-modal-body">
          <div className="crimenet-modal-hint-box">
            Merging consolidates two identities into a single node. All incoming and outgoing relationships from both entities will be transferred to the consolidated node.
          </div>

          <div className="crimenet-modal-section">
            <label className="crimenet-field-label">Primary Entity (Node A)</label>
            <select
              className="crimenet-select"
              value={nodeAId}
              onChange={(e) => setNodeAId(e.target.value)}
            >
              {nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.label || n.id} ({n.type})
                </option>
              ))}
            </select>
          </div>

          <div className="crimenet-modal-section">
            <label className="crimenet-field-label">Entity to Merge (Node B)</label>
            <select
              className="crimenet-select"
              value={nodeBId}
              onChange={(e) => setNodeBId(e.target.value)}
            >
              {nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.label || n.id} ({n.type})
                </option>
              ))}
            </select>
          </div>

          <div className="crimenet-modal-divider" />

          <div className="crimenet-modal-section">
            <label className="crimenet-field-label">Consolidated Name / Label</label>
            <input
              type="text"
              className="crimenet-text-input"
              placeholder={nodeA ? `${nodeA.label} (Consolidated)` : "Consolidated name..."}
              value={mergedName}
              onChange={(e) => setMergedName(e.target.value)}
            />
          </div>

          <div className="crimenet-modal-section">
            <label className="crimenet-field-label">Consolidated Type</label>
            <select
              className="crimenet-select"
              value={targetType}
              onChange={(e) => setTargetType(e.target.value)}
            >
              <option value="person">person</option>
              <option value="phone">phone</option>
              <option value="vehicle">vehicle</option>
              <option value="organization">organization</option>
              <option value="location">location</option>
              <option value="account">account</option>
              <option value="case">case</option>
              <option value="entity">entity</option>
            </select>
          </div>
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
            Merge Elements
          </button>
        </div>
      </div>
    </div>
  );
}
