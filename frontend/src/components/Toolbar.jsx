import React from "react";
import {
  Search, Pencil, PlusCircle, Trash2, GitMerge,
  EyeOff, Eraser, Eye, Maximize
} from "lucide-react";

const ACTIONS = [
  { key: "edit", label: "Edit", icon: Pencil },
  { key: "add", label: "Add", icon: PlusCircle },
  { key: "delete", label: "Delete", icon: Trash2, danger: true },
  { key: "merge", label: "Merge", icon: GitMerge },
  { key: "exclude", label: "Exclude", icon: EyeOff },
  { key: "clear", label: "Clear view", icon: Eraser },
  { key: "showAll", label: "Show all", icon: Eye },
  { key: "expandAll", label: "Expand all", icon: Maximize },
];

export default function Toolbar({ query, setQuery, onAction }) {
  return (
    <div>
      <div className="search-field">
        <Search size={14} />
        <input
          className="field"
          placeholder="Search entity…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {ACTIONS.map((a) => {
        const Icon = a.icon;
        return (
          <button
            key={a.key}
            className={`btn ${a.danger ? "danger" : ""}`}
            onClick={() => onAction(a.key)}
            title={a.label}
          >
            <Icon size={14} /> {a.label}
          </button>
        );
      })}
    </div>
  );
}
