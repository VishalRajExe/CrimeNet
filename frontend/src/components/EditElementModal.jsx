import React, { useState, useEffect } from "react";
import { X, Plus, Trash2, Edit3 } from "lucide-react";

const STANDARD_TYPES = [
  "person", "phone", "vehicle", "location", "organization",
  "bank", "account", "case", "fir", "entity", "transaction", "connected_to"
];

export default function EditElementModal({
  isOpen,
  onClose,
  element, // node or edge object
  isEdge = false,
  onSave,
}) {
  const [elementType, setElementType] = useState("person");
  const [label, setLabel] = useState("");
  const [properties, setProperties] = useState([]);
  const [newPropKey, setNewPropKey] = useState("");
  const [newPropVal, setNewPropVal] = useState("");

  useEffect(() => {
    if (element) {
      setElementType(element.type || (isEdge ? "connected_to" : "person"));
      setLabel(element.label || element.properties?.name || element.id || "");
      const props = element.properties || {};
      const rows = Object.entries(props)
        .filter(([k]) => k !== "name" && k !== "type" && k !== "label")
        .map(([k, v]) => ({
          key: k,
          value: Array.isArray(v) ? v.join(", ") : String(v),
        }));
      setProperties(rows);
    }
  }, [element, isEdge, isOpen]);

  const handleAddProp = () => {
    if (!newPropKey.trim()) return;
    setProperties((prev) => [
      ...prev,
      { key: newPropKey.trim(), value: newPropVal.trim() },
    ]);
    setNewPropKey("");
    setNewPropVal("");
  };

  const handleRemoveProp = (index) => {
    setProperties((prev) => prev.filter((_, i) => i !== index));
  };

  const handlePropChange = (index, field, val) => {
    setProperties((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: val } : p))
    );
  };

  const handleApply = () => {
    const propObj = {};
    properties.forEach((p) => {
      if (p.key.trim()) {
        propObj[p.key.trim()] = p.value;
      }
    });

    onSave?.({
      ...element,
      type: elementType,
      label: label.trim() || element.id,
      properties: {
        ...(element.properties || {}),
        name: label.trim() || element.id,
        type: elementType,
        ...propObj,
      },
    });
    onClose();
  };

  if (!isOpen || !element) return null;

  return (
    <div className="crimenet-modal-backdrop">
      <div className="crimenet-modal-window">
        <div className="crimenet-modal-header">
          <div className="crimenet-modal-title">
            <Edit3 size={15} /> Edit Selected {isEdge ? "Edge" : "Element"}
          </div>
          <button className="crimenet-modal-close" onClick={onClose}>
            <X size={15} />
          </button>
        </div>

        <div className="crimenet-modal-body">
          <div className="crimenet-modal-section">
            <label className="crimenet-field-label">Element Type</label>
            <select
              className="crimenet-select"
              value={elementType}
              onChange={(e) => setElementType(e.target.value)}
            >
              {STANDARD_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {!isEdge && (
            <div className="crimenet-modal-section">
              <label className="crimenet-field-label">Element Name / Label</label>
              <input
                type="text"
                className="crimenet-text-input"
                placeholder="Name or identifier..."
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
            </div>
          )}

          <div className="crimenet-modal-divider" />

          {/* Properties */}
          <div className="crimenet-modal-section">
            <label className="crimenet-field-label">Custom Properties</label>

            {properties.map((p, idx) => (
              <div key={idx} className="crimenet-prop-row">
                <input
                  type="text"
                  className="crimenet-text-input-sm"
                  placeholder="Property..."
                  value={p.key}
                  onChange={(e) => handlePropChange(idx, "key", e.target.value)}
                />
                <input
                  type="text"
                  className="crimenet-text-input-sm"
                  placeholder="Value..."
                  value={p.value}
                  onChange={(e) => handlePropChange(idx, "value", e.target.value)}
                />
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
                placeholder="New property..."
                value={newPropKey}
                onChange={(e) => setNewPropKey(e.target.value)}
              />
              <input
                type="text"
                className="crimenet-text-input-sm"
                placeholder="Value..."
                value={newPropVal}
                onChange={(e) => setNewPropVal(e.target.value)}
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
