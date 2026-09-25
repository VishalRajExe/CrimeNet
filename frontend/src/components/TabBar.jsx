import React from "react";
import { Share2, Network, Waypoints, ScanSearch } from "lucide-react";

const TABS = [
  { id: "network", label: "Network", icon: Network },
  { id: "analysis", label: "Analysis", icon: Waypoints },
  { id: "intelligence", label: "Intelligence", icon: ScanSearch },
];

export default function TabBar({ active, onChange, caseName }) {
  return (
    <div className="topbar">
      <div className="brand">
        <Share2 size={16} />
        {caseName}
      </div>
      <div className="tabs">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              className={`tab ${active === t.id ? "active" : ""}`}
              onClick={() => onChange(t.id)}
            >
              <Icon size={14} />
              {t.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
