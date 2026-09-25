import React from "react";
import { Trash2, X, AlertTriangle } from "lucide-react";

export default function DeleteConfirmModal({
  isOpen,
  onClose,
  elementName,
  onConfirm,
}) {
  if (!isOpen) return null;

  return (
    <div className="crimenet-modal-backdrop">
      <div className="crimenet-modal-window delete-modal">
        <div className="crimenet-modal-header">
          <div className="crimenet-modal-title" style={{ color: "#dc2626" }}>
            <AlertTriangle size={15} /> Delete Selected Element(s)?
          </div>
          <button className="crimenet-modal-close" onClick={onClose}>
            <X size={15} />
          </button>
        </div>

        <div className="crimenet-modal-body">
          <div style={{ fontSize: 13, color: "#333", lineHeight: 1.5 }}>
            {elementName ? (
              <p>Are you sure you want to permanently delete <b>{elementName}</b> and all its associated connections?</p>
            ) : (
              <p>Are you sure you want to delete the selected element(s)?</p>
            )}
            <p style={{ fontSize: 12, color: "#666", marginTop: 8 }}>
              Element(s) are permanently deleted from this session. If you want to hide elements from the visualization only, use <b>Exclude</b> instead.
            </p>
          </div>
        </div>

        <div className="crimenet-modal-footer">
          <button
            type="button"
            className="crimenet-btn-secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="crimenet-btn-danger"
            onClick={() => {
              onConfirm?.();
              onClose();
            }}
          >
            <Trash2 size={13} /> Delete
          </button>
        </div>
      </div>
    </div>
  );
}
