import React, { useState, useMemo } from "react";
import {
  X, BookOpen, Shield, Network, Cpu, Terminal,
  Search, Check, Copy, ExternalLink, AlertTriangle,
  Info, Layers, Share2, Download, Eye, Plus, Edit3, Trash2, Merge,
  FolderOpen, Sliders
} from "lucide-react";

export default function UserDocumentationModal({ isOpen, onClose }) {
  const [activeSection, setActiveSection] = useState("getting-started");
  const [copiedId, setCopiedId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  if (!isOpen) return null;

  const handleCopy = (text, id) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const SECTIONS = [
    { id: "getting-started", label: "Getting Started", icon: Shield },
    { id: "ui-overview", label: "User Interface", icon: Layers },
    { id: "exploring-editing", label: "Exploring & Editing", icon: Network },
    { id: "analysis-algorithms", label: "Analysis Algorithms", icon: Cpu },
    { id: "server-data", label: "Server & Formats", icon: Terminal },
  ];

  return (
    <div
      className="crimenet-modal-backdrop"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 16,
      }}
    >
      <div
        className="crimenet-modal-window crimenet-fade-in"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 940,
          maxWidth: "96vw",
          height: "88vh",
          display: "flex",
          flexDirection: "column",
          background: "var(--panel)",
          border: "1px solid var(--border-2)",
          borderRadius: 12,
          boxShadow: "0 25px 60px rgba(0,0,0,0.6), 0 0 0 1px var(--border)",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 20px",
            background: "var(--panel-2)",
            borderBottom: "1px solid var(--border)",
            flexShrink: 0,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "var(--teal)",
                color: "#ffffff",
                display: "grid",
                placeItems: "center",
                boxShadow: "0 4px 12px rgba(2, 132, 199, 0.3)",
              }}
            >
              <BookOpen size={16} />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text)" }}>
                CrimeNet Visualizer User Documentation
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                Complete Technical Handbook & Operations Reference
              </div>
            </div>
          </div>

          {/* Search bar inside header */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                position: "relative",
                display: "flex",
                alignItems: "center",
                width: 220,
              }}
            >
              <Search
                size={13}
                style={{
                  position: "absolute",
                  left: 8,
                  color: "var(--text-muted)",
                  pointerEvents: "none",
                }}
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search handbook..."
                style={{
                  width: "100%",
                  padding: "5px 8px 5px 26px",
                  fontSize: 11.5,
                  borderRadius: 6,
                  border: "1px solid var(--border-2)",
                  background: "var(--bg-2)",
                  color: "var(--text)",
                  outline: "none",
                }}
              />
            </div>

            <button
              onClick={onClose}
              aria-label="Close documentation"
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                padding: 6,
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Layout: Left Navigation + Right Content */}
        <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
          {/* Navigation Sidebar */}
          <div
            style={{
              width: 220,
              background: "var(--panel-2)",
              borderRight: "1px solid var(--border)",
              padding: "12px 8px",
              display: "flex",
              flexDirection: "column",
              gap: 4,
              flexShrink: 0,
            }}
          >
            {SECTIONS.map((sec) => {
              const Icon = sec.icon;
              const active = activeSection === sec.id;
              return (
                <button
                  key={sec.id}
                  onClick={() => setActiveSection(sec.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "8px 12px",
                    borderRadius: 6,
                    border: active ? "1px solid var(--teal)" : "1px solid transparent",
                    background: active ? "var(--teal-s)" : "transparent",
                    color: active ? "var(--teal)" : "var(--text)",
                    fontWeight: active ? 700 : 500,
                    fontSize: 12,
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "all 0.15s ease",
                  }}
                >
                  <Icon size={14} />
                  <span>{sec.label}</span>
                </button>
              );
            })}

            <div style={{ marginTop: "auto", padding: "10px 8px", borderTop: "1px solid var(--border)" }}>
              <div style={{ fontSize: 10, color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>
                CRIMENET LE DOCS v2.0
              </div>
              <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
                Restructured in active theme
              </div>
            </div>
          </div>

          {/* Scrollable Content Body */}
          <div
            style={{
              flex: 1,
              padding: "24px 28px",
              overflowY: "auto",
              color: "var(--text)",
              fontSize: 13,
              lineHeight: 1.65,
            }}
          >
            {/* Note regarding vocabulary */}
            <div
              style={{
                marginBottom: 18,
                padding: "10px 14px",
                background: "var(--panel-3)",
                borderLeft: "4px solid var(--teal)",
                borderRadius: "0 6px 6px 0",
                fontSize: 12,
                color: "var(--text)",
              }}
            >
              <b>Vocabulary Note:</b> In this documentation and throughout the interface, the terms <i>entity</i> and <i>node</i> are interchangeable (entities in social network context; nodes in graph topology). Similarly, <i>link</i> and <i>edge</i> represent the identical relational connection.
            </div>

            {/* SECTION 1: GETTING STARTED */}
            {activeSection === "getting-started" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <div>
                  <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px 0", color: "var(--text)" }}>
                    1. Getting Started
                  </h2>
                  <p style={{ color: "var(--text-muted)", margin: 0 }}>
                    Follow these step-by-step instructions to initialize the server, load investigation datasets, and explore network relations.
                  </p>
                </div>

                {/* Step 1: Run Server */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px 0", color: "var(--teal)" }}>
                    Step 1: Run the Server
                  </h3>
                  <p style={{ margin: "0 0 10px 0", fontSize: 12.5, color: "var(--text)" }}>
                    Start the platform server using Python 3:
                  </p>
                  <div
                    style={{
                      position: "relative",
                      background: "var(--bg-2)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "8px 12px",
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      color: "var(--text)",
                    }}
                  >
                    <code>python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000</code>
                    <button
                      onClick={() => handleCopy("python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000", "c1")}
                      style={{
                        position: "absolute",
                        right: 8,
                        top: 8,
                        background: "transparent",
                        border: "none",
                        color: "var(--text-muted)",
                        cursor: "pointer",
                      }}
                    >
                      {copiedId === "c1" ? <Check size={14} color="var(--green)" /> : <Copy size={14} />}
                    </button>
                  </div>
                </div>

                {/* Step 2: Open Visualizer */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px 0", color: "var(--teal)" }}>
                    Step 2: Open the Visualizer
                  </h3>
                  <p style={{ margin: 0, fontSize: 12.5, color: "var(--text)" }}>
                    Launch the visualizer client in your web browser at <code>http://127.0.0.1:5173</code> (Vite development mode) or <code>http://127.0.0.1:8000</code> (Production deployment).
                  </p>
                </div>

                {/* Step 3: Load Network */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 8px 0", color: "var(--teal)" }}>
                    Step 3: Load a Network
                  </h3>
                  <ol style={{ margin: 0, paddingLeft: 20, fontSize: 12.5, color: "var(--text)", display: "flex", flexDirection: "column", gap: 6 }}>
                    <li>
                      <b>Select Network:</b> On the right sidebar under the <b>Network</b> tab, open the <code>Select network ...</code> dropdown and choose the target case (e.g., <i>UNBOUND — Indian Criminal Network 2026</i>, <i>Drug Trafficking Syndicate</i>, etc.).
                    </li>
                    <li>
                      <b>Select Entities (Optional Scoping):</b> In the entity selection list below, select specific suspects or bank accounts to narrow down the investigation scope. Leaving this unselected loads the complete network.
                    </li>
                    <li>
                      <b>Press LOAD NETWORK:</b> Click the <code>LOAD NETWORK</code> button. All selected entities and their direct 1-hop outgoing connections will render immediately on the interactive canvas.
                    </li>
                  </ol>
                </div>

                {/* Step 4: Explore & Export */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px 0", color: "var(--teal)" }}>
                    Step 4: Explore and Export Results
                  </h3>
                  <p style={{ margin: 0, fontSize: 12.5, color: "var(--text)" }}>
                    Click and drag nodes to reposition them. Double-click any operative to focus the canvas. To export results, use the <code>EXPORT IMAGE</code> button to download high-resolution PNG snapshots, or <code>EXPORT NETWORK</code> to export a JSON network file.
                  </p>
                </div>
              </div>
            )}

            {/* SECTION 2: USER INTERFACE */}
            {activeSection === "ui-overview" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <div>
                  <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px 0", color: "var(--text)" }}>
                    2. User Interface Breakdown
                  </h2>
                  <p style={{ color: "var(--text-muted)", margin: 0 }}>
                    Comprehensive guide to each primary screen division and functional panel.
                  </p>
                </div>

                {/* Top Tactical Command Bar */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px 0", color: "var(--teal)" }}>
                    Tactical Command Bar (Top Navigation)
                  </h3>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, color: "var(--text)", display: "flex", flexDirection: "column", gap: 4 }}>
                    <li><b>CrimeNet Brand:</b> Platform identifier.</li>
                    <li><b>Active Case Telemetry:</b> Displays the active investigation ID (e.g. <code>unbound_case_2026</code>), active entity count, and link count.</li>
                    <li><b>Theme Toggle:</b> 1-click switch between <b>Pitch Black</b> (Dark mode) and <b>Cream White</b> (Light mode).</li>
                  </ul>
                </div>

                {/* Left Sidebar: Control Boxes */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px 0", color: "var(--teal)" }}>
                    Left Sidebar: Control Boxes
                  </h3>
                  <p style={{ fontSize: 12.5, color: "var(--text)", margin: "0 0 8px 0" }}>
                    The Left Sidebar provides 3 dedicated, collapsible control boxes for granular filtering:
                  </p>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, color: "var(--text)", display: "flex", flexDirection: "column", gap: 4 }}>
                    <li><b>NODES Box:</b> Table listing all node types (Person, Location, Vehicle, Bank, UPI, etc.) with checkboxes to hide or highlight specific entity classes.</li>
                    <li><b>EDGES Box:</b> Table listing all relationship types (COMMUNICATED_WITH, TRANSFERRED_FUNDS, ASSOCIATE_OF, etc.) with visibility toggles.</li>
                    <li><b>LABELS Box:</b> Checkbox selectors to control which properties (e.g. Name, Type, Phone, Registration ID) are rendered as labels above nodes.</li>
                  </ul>
                </div>

                {/* Right Sidebar: Tabs */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px 0", color: "var(--teal)" }}>
                    Right Sidebar: Tabs (Network, Analysis, Intelligence)
                  </h3>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, color: "var(--text)", display: "flex", flexDirection: "column", gap: 4 }}>
                    <li><b>Network Tab:</b> Dataset selection dropdown, entity scoping list, network loading, local file import, save state, and image export.</li>
                    <li><b>Analysis Tab:</b> Cascading 2-tier dropdown selectors to execute algorithmic community detection, social influence centrality, link prediction, and node embeddings.</li>
                    <li><b>Intelligence Tab:</b> Multi-source intelligence synthesis including explainable AI summaries, hidden link prediction leads, anomaly alerts, N-hop neighborhood exploration, and timeline visualization.</li>
                  </ul>
                </div>
              </div>
            )}

            {/* SECTION 3: EXPLORING & EDITING */}
            {activeSection === "exploring-editing" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <div>
                  <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px 0", color: "var(--text)" }}>
                    3. Exploring & Editing Networks
                  </h2>
                  <p style={{ color: "var(--text-muted)", margin: 0 }}>
                    Operational commands for expanding connections, modifying attributes, merging duplicate operatives, and comparing states.
                  </p>
                </div>

                {/* Exploring Commands */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 8px 0", color: "var(--green)" }}>
                    Exploration Commands (Non-destructive)
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12.5 }}>
                    <div>
                      <b>EXPAND NODE(S):</b> Expands all currently selected nodes. When a node is expanded, all outgoing connections and unrendered target entities are added to the canvas.
                    </div>
                    <div>
                      <b>EXPAND ALL NODES:</b> Concurrently expands every expandable node across the entire network topology.
                    </div>
                    <div>
                      <b>EXCLUDE ELEMENTS:</b> Temporarily removes selected nodes or links from the visible canvas without deleting them from the underlying case data.
                    </div>
                    <div>
                      <b>CLEAR VIEW:</b> Empties the canvas to allow targeted re-scoping.
                    </div>
                    <div>
                      <b>SHOW ALL NODES:</b> Restores all hidden and unexpanded elements to the canvas.
                    </div>
                  </div>
                </div>

                {/* Editing Commands */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 8px 0", color: "var(--rose)" }}>
                    Editing Commands (Permanent Case Modifications)
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12.5 }}>
                    <div>
                      <b>EDIT ELEMENT:</b> Opens an inspector dialog to modify properties, change the operative's alias, or add custom intelligence tags (e.g. <i>risk_level: High</i>).
                    </div>
                    <div>
                      <b>ADD ELEMENT:</b> Creates a new entity (Node) or registers a new relational link (Edge) between two existing entities by selecting source and target.
                    </div>
                    <div>
                      <b>DELETE ELEMENTS:</b> Permanently removes the selected entities and all incident links from the active network.
                    </div>
                    <div>
                      <b>MERGE ELEMENTS:</b> Combines two or more duplicate or aliased nodes into a single consolidated operative, merging all incoming and outgoing connections.
                    </div>
                  </div>
                </div>

                {/* Original Network Comparison */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px 0", color: "var(--teal)" }}>
                    Original Network Comparison View
                  </h3>
                  <p style={{ margin: 0, fontSize: 12.5, color: "var(--text)" }}>
                    Clicking <b>OPEN ORIGINAL NETWORK</b> restores the unedited baseline network state so investigators can compare current modified topologies against the initial FIR data.
                  </p>
                </div>
              </div>
            )}

            {/* SECTION 4: ANALYSIS & ALGORITHMS */}
            {activeSection === "analysis-algorithms" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <div>
                  <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px 0", color: "var(--text)" }}>
                    4. Graph Analysis & Algorithms
                  </h2>
                  <p style={{ color: "var(--text-muted)", margin: 0 }}>
                    Technical explanation of mathematical models and centrality algorithms implemented in the Analysis engine.
                  </p>
                </div>

                {[
                  {
                    title: "Community Detection (Modularity & Louvain)",
                    desc: "Partitions the network into densely connected subgroups or syndicates. Nodes belonging to the same criminal module share identical visual color clusters. Supports Louvain, Modularity Maximization, Label Propagation, and Spectral Clustering.",
                    badge: "SYNDICATE PARTITIONING",
                  },
                  {
                    title: "Social Influence Analysis (PageRank & Centrality)",
                    desc: "Evaluates the structural prominence of operatives. PageRank highlights syndicate kingpins based on transitive influence. Betweenness Centrality identifies bridge operatives whose interdiction severs communication lines.",
                    badge: "KEY ACTOR IDENTIFICATION",
                  },
                  {
                    title: "Link Prediction (Jaccard & Adamic-Adar)",
                    desc: "Calculates the statistical likelihood of covert associations between suspects based on shared mutual associates and transaction patterns. Most probable hidden links are rendered as dashed indicator paths.",
                    badge: "COVERT LINK DISCOVERY",
                  },
                  {
                    title: "Node Embedding (Node2Vec & DeepWalk)",
                    desc: "Generates continuous vector representations of nodes preserving local and global neighborhood structure, enabling clustering of operatives with similar behavioral profiles.",
                    badge: "AI EMBEDDINGS",
                  },
                ].map((item, i) => (
                  <div key={i} style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontWeight: 700, color: "var(--text)", fontSize: 13.5 }}>{item.title}</span>
                      <span style={{ fontSize: 9.5, fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: "var(--teal-s)", color: "var(--teal)", border: "1px solid var(--teal)" }}>
                        {item.badge}
                      </span>
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--text)" }}>{item.desc}</div>
                  </div>
                ))}
              </div>
            )}

            {/* SECTION 5: SERVER & FORMATS */}
            {activeSection === "server-data" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <div>
                  <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px 0", color: "var(--text)" }}>
                    5. Server Arguments & Data Formats
                  </h2>
                  <p style={{ color: "var(--text-muted)", margin: 0 }}>
                    Command-line options, file schemas, and persistent state storage.
                  </p>
                </div>

                {/* CLI Arguments */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px 0", color: "var(--teal)" }}>
                    Command Line Arguments
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12.5 }}>
                    <div><code>--data &lt;DIR&gt;</code>: Path to local directory containing criminal network files in JSON or L3S format.</div>
                    <div><code>--host &lt;IP&gt;</code>: Network host interface to bind (e.g. <code>127.0.0.1</code> or <code>0.0.0.0</code>).</div>
                    <div><code>--port &lt;PORT&gt;</code>: Port number (defaults to 8000 for FastAPI / 5173 for Vite).</div>
                    <div><code>--debug</code>: Starts the engine in hot-reloading development mode.</div>
                  </div>
                </div>

                {/* Schema Structure */}
                <div style={{ padding: "14px 16px", background: "var(--panel-2)", border: "1px solid var(--border-2)", borderRadius: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 6px 0", color: "var(--teal)" }}>
                    JSON Network Schema Specification
                  </h3>
                  <pre
                    style={{
                      background: "var(--bg-2)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: 12,
                      fontSize: 11.5,
                      fontFamily: "var(--font-mono)",
                      color: "var(--text)",
                      overflowX: "auto",
                      margin: 0,
                    }}
                  >
{`{
  "nodes": [
    { "id": "suspect_01", "label": "Rohit Malhotra", "type": "person", "properties": { "role": "Handler" } },
    { "id": "acc_9921", "label": "Mule Acct #9921", "type": "bank", "properties": { "bank_name": "SBI" } }
  ],
  "edges": [
    { "source": "suspect_01", "target": "acc_9921", "type": "TRANSFERRED_FUNDS", "weight": 250000 }
  ]
}`}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "10px 20px",
            background: "var(--panel-2)",
            borderTop: "1px solid var(--border)",
            flexShrink: 0,
          }}
        >
          <div style={{ fontSize: 11, color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>
            CrimeNet Investigative Intelligence Platform • Law Enforcement Operations Edition
          </div>
          <button
            onClick={onClose}
            className="crimenet-btn-secondary"
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border: "1px solid var(--border-2)",
              background: "var(--panel-3)",
              color: "var(--text)",
              fontWeight: 600,
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            Close Documentation
          </button>
        </div>
      </div>
    </div>
  );
}
