import React, { useState, useMemo } from "react";
import { X, Plus, Trash2, Search, Filter } from "lucide-react";

export default function SearchFilterModal({
  isOpen,
  onClose,
  nodes = [],
  onApplyFilter,
}) {
  const [quickQuery, setQuickQuery] = useState("");
  const [propertyFilters, setPropertyFilters] = useState([]);
  const [matchMode, setMatchMode] = useState("AND"); // "AND" | "OR"

  // Collect all available property keys from nodes
  const availableProperties = useMemo(() => {
    const keys = new Set(["id", "label", "type"]);
    nodes.forEach((n) => {
      if (n.properties) {
        Object.keys(n.properties).forEach((k) => keys.add(k));
      }
    });
    return Array.from(keys);
  }, [nodes]);

  const addFilterRow = () => {
    setPropertyFilters((prev) => [
      ...prev,
      {
        id: `f_${Date.now()}_${prev.length}`,
        property: availableProperties[0] || "label",
        condition: "contains",
        value: "",
      },
    ]);
  };

  const removeFilterRow = (id) => {
    setPropertyFilters((prev) => prev.filter((r) => r.id !== id));
  };

  const updateFilterRow = (id, field, val) => {
    setPropertyFilters((prev) =>
      prev.map((r) => (r.id === id ? { ...r, [field]: val } : r))
    );
  };

  const handleReset = () => {
    setQuickQuery("");
    setPropertyFilters([]);
    onApplyFilter?.({ quickQuery: "", propertyFilters: [], matchMode: "AND" });
  };

  const handleApply = () => {
    onApplyFilter?.({
      quickQuery: quickQuery.trim(),
      propertyFilters,
      matchMode,
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="crimenet-modal-backdrop">
      <div className="crimenet-modal-window search-modal">
        <div className="crimenet-modal-header">
          <div className="crimenet-modal-title">
            <Search size={15} /> Search & Filter Network
          </div>
          <button className="crimenet-modal-close" onClick={onClose}>
            <X size={15} />
          </button>
        </div>

        <div className="crimenet-modal-body">
          {/* Quick Search */}
          <div className="crimenet-modal-section">
            <label className="crimenet-field-label">
              Quick Search (Name, ID, or Keyword):
            </label>
            <div className="crimenet-input-with-icon">
              <Search size={14} className="input-icon" />
              <input
                type="text"
                className="crimenet-text-input"
                placeholder="Type name, ID, or keyword to search..."
                value={quickQuery}
                onChange={(e) => setQuickQuery(e.target.value)}
                autoFocus
              />
            </div>
            <div className="crimenet-field-hint">
              Leave blank to use property-specific filters below.
            </div>
          </div>

          <div className="crimenet-modal-divider" />

          {/* Property Filters */}
          <div className="crimenet-modal-section">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <label className="crimenet-field-label" style={{ margin: 0 }}>
                Property Filters:
              </label>
              {propertyFilters.length > 1 && (
                <div className="crimenet-match-mode">
                  <span style={{ fontSize: 11, color: "#666", marginRight: 4 }}>Match:</span>
                  <select
                    value={matchMode}
                    onChange={(e) => setMatchMode(e.target.value)}
                    className="crimenet-select-xs"
                  >
                    <option value="AND">ALL (AND)</option>
                    <option value="OR">ANY (OR)</option>
                  </select>
                </div>
              )}
            </div>

            {propertyFilters.length === 0 ? (
              <div className="crimenet-empty-filter-state">
                No property criteria added. Click "+ Add Filter Property" to filter by specific attributes like flight, cases, role, location, etc.
              </div>
            ) : (
              <div className="crimenet-filter-rows">
                {propertyFilters.map((row) => (
                  <div key={row.id} className="crimenet-filter-row">
                    <select
                      className="crimenet-select-sm"
                      value={row.property}
                      onChange={(e) => updateFilterRow(row.id, "property", e.target.value)}
                    >
                      {availableProperties.map((p) => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>

                    <select
                      className="crimenet-select-sm"
                      value={row.condition}
                      onChange={(e) => updateFilterRow(row.id, "condition", e.target.value)}
                    >
                      <option value="contains">contains</option>
                      <option value="equals">equals</option>
                      <option value="starts_with">starts with</option>
                      <option value="ends_with">ends with</option>
                      <option value="greater_than">&gt;</option>
                      <option value="less_than">&lt;</option>
                    </select>

                    <input
                      type="text"
                      className="crimenet-text-input-sm"
                      placeholder="Value..."
                      value={row.value}
                      onChange={(e) => updateFilterRow(row.id, "value", e.target.value)}
                    />

                    <button
                      className="crimenet-row-btn remove"
                      title="Remove condition"
                      onClick={() => removeFilterRow(row.id)}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button
              type="button"
              className="crimenet-btn-dashed"
              onClick={addFilterRow}
            >
              <Plus size={13} /> Add Filter Property
            </button>
          </div>
        </div>

        <div className="crimenet-modal-footer">
          <button
            type="button"
            className="crimenet-btn-secondary"
            onClick={handleReset}
            style={{ marginRight: "auto" }}
          >
            Reset
          </button>
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
