import React from "react";
import { Loader2, ShieldAlert, Cpu, Activity, RefreshCw } from "lucide-react";

export default function DynamicActionLoader({ active, message = "Processing Intelligence Request..." }) {
  if (!active) return null;

  return (
    <div
      className="crimenet-loader-overlay crimenet-fade-in"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(0, 0, 0, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        className="crimenet-loader-card"
        style={{
          background: "var(--panel, #131313)",
          border: "1px solid var(--border-2, #3a3a3a)",
          borderRadius: 12,
          padding: "24px 32px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
          boxShadow: "0 25px 60px rgba(0,0,0,0.6), 0 0 20px rgba(79, 195, 247, 0.2)",
          minWidth: 280,
          maxWidth: "85vw",
          textAlign: "center",
        }}
      >
        {/* Animated 3D Ring Spinner */}
        <div style={{ position: "relative", width: 48, height: 48 }}>
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: "50%",
              border: "3px solid var(--border, #2a2a2a)",
              borderTopColor: "var(--teal, #4fc3f7)",
              borderRightColor: "var(--teal, #4fc3f7)",
              animation: "crimenet-spin 0.8s linear infinite",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 8,
              borderRadius: "50%",
              border: "2px dashed var(--blue, #5b9bd5)",
              animation: "crimenet-spin 1.4s linear infinite reverse",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "grid",
              placeItems: "center",
              color: "var(--teal, #4fc3f7)",
            }}
          >
            <Activity size={18} />
          </div>
        </div>

        {/* Action description text */}
        <div>
          <div
            style={{
              fontSize: 13.5,
              fontWeight: 700,
              color: "var(--text, #f0f0f0)",
              letterSpacing: "0.02em",
              marginBottom: 4,
            }}
          >
            {message}
          </div>
          <div
            style={{
              fontSize: 10.5,
              color: "var(--text-muted, #a0a0a0)",
              fontFamily: "var(--font-mono, monospace)",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            CrimeNet Operations Engine
          </div>
        </div>

        {/* Shimmer progress bar */}
        <div
          style={{
            width: "100%",
            height: 3,
            borderRadius: 2,
            background: "var(--panel-3, #222222)",
            overflow: "hidden",
            position: "relative",
          }}
        >
          <div
            style={{
              width: "100%",
              height: "100%",
              background: "linear-gradient(90deg, transparent, var(--teal, #4fc3f7), transparent)",
              backgroundSize: "200% 100%",
              animation: "crimenet-shimmer 1.2s ease-in-out infinite",
            }}
          />
        </div>
      </div>
    </div>
  );
}
