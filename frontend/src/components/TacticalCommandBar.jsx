import React from "react";
import { Sun, Moon } from "lucide-react";

export default function TacticalCommandBar({
  caseId = "CASE-2024-MH-088",
  nodesCount = 0,
  edgesCount = 0,
  onToggleTheme,
  theme = "dark",
}) {
  return (
    <header className="tactical-command-bar">
      {/* Brand - strictly CrimeNet text only without false logo */}
      <div className="command-brand">
        <span className="command-brand-name">CrimeNet</span>
      </div>

      {/* Center: Active Case Telemetry */}
      <div className="command-telemetry" aria-label="Active investigation telemetry">
        <span className="command-telemetry-label">CASE</span>
        <span className="command-case-id" title={caseId}>{caseId}</span>
        <span className="command-divider" aria-hidden="true" />
        <span><strong>{nodesCount}</strong> Entities</span>
        <span className="command-divider" aria-hidden="true" />
        <span><strong>{edgesCount}</strong> Links</span>
      </div>

      {/* Right: Theme Toggle Only */}
      <div className="command-actions">
        <button
          type="button"
          className="command-theme-button"
          onClick={onToggleTheme}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
        </button>
      </div>
    </header>
  );
}
