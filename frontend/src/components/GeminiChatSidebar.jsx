/**
 * GeminiChatSidebar.jsx — CrimeNet Google Gemini AI Agent Chat Interface
 * Styled exactly like the modern Google Gemini chat interface:
 * - Multimodal investigative copilot for Indian Law Enforcement.
 * - Contextually grounded in NetworkX graph metrics, scikit-learn Isolation Forest, and GraphRAG.
 * - Ingests suspect narrative into the graph canvas directly from chat.
 * - Suggestion prompt chips for quick tactical legal & financial inquiries.
 */

import React, { useState, useRef, useEffect } from "react";
import {
  Sparkles, Send, Bot, User, Trash2, X, ChevronRight, Copy, Check,
  AlertTriangle, Shield, ArrowUpRight, Loader2, Minimize2, Maximize2
} from "lucide-react";
import { api } from "../lib/api";

const SUGGESTED_PROMPTS = [
  "🎯 Identify syndicate hierarchy & kingpin",
  "💸 Trace 3-hop money trail & mule accounts",
  "🌲 Run Isolation Forest anomaly detection",
  "⚖️ Draft Section 102 CrPC account freeze order",
  "💥 Find critical communication bridges (cut vertices)",
  "📜 Summarize GraphRAG evidence citations",
];

export default function GeminiChatSidebar({
  isOpen,
  onClose,
  nodes = [],
  edges = [],
  caseId = "CASE-2024-MH-088",
  onGraphUpdate,
  onSelectNode,
  onToast,
}) {
  const [messages, setMessages] = useState([
    {
      id: "m0",
      sender: "gemini",
      text: `### 🛡️ CrimeNet Gemini Intelligence Copilot Active\n\nI am your AI investigative partner grounded in active network topology (**${nodes.length} entities**, **${edges.length} edges**), **scikit-learn Isolation Forest**, and **GraphRAG** evidence.\n\nYou can:\n- **Ask tactical questions** regarding syndicate structure, hawala routing, and legal actions.\n- **Paste suspect narratives** or interrogation excerpts — I will extract entities and auto-draw the network.\n- **Draft statutory notices** under Section 102 CrPC, Section 91 CrPC, or Lookout Circulars (LOC).`,
      timestamp: "Just now",
      model: "Google Gemini 1.5 Flash",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    const userMsgId = `usr_${Date.now()}`;
    const userMsg = {
      id: userMsgId,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const historyPayload = messages.slice(-6).map((m) => ({
        role: m.sender === "user" ? "user" : "model",
        text: m.text,
      }));

      const res = await api.geminiChat({
        message: query,
        caseId,
        history: historyPayload,
        nodes,
        edges,
      });

      const geminiMsg = {
        id: `gem_${Date.now()}`,
        sender: "gemini",
        text: res.reply || "No response received.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        model: res.model || "Gemini 1.5 Flash",
        extractedCount: res.extractedCount || 0,
        newNodes: res.newNodes || [],
      };

      setMessages((prev) => [...prev, geminiMsg]);

      // If narrative ingestion yielded new nodes/edges, notify canvas!
      if (res.newNodes && res.newNodes.length > 0) {
        onToast?.(`[Gemini Extraction] Added ${res.newNodes.length} entities to operational graph.`);
        if (onGraphUpdate) {
          const mergedNodes = [...nodes];
          const existIds = new Set(nodes.map((n) => n.id));
          res.newNodes.forEach((n) => {
            if (!existIds.has(n.id)) mergedNodes.push(n);
          });
          const mergedEdges = [...edges, ...(res.newEdges || [])];
          onGraphUpdate(mergedNodes, mergedEdges);
        }
      }
    } catch (err) {
      console.error("Gemini Chat Error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: "gemini",
          text: `⚠️ **Error connecting to Gemini Service**: ${err.message || "Backend offline"}. Please check your FastAPI connection.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          model: "System Notice",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: `m_${Date.now()}`,
        sender: "gemini",
        text: "🧹 Chat cleared. Operational graph context and GraphRAG knowledge base remain loaded.",
        timestamp: "Just now",
        model: "Google Gemini 1.5 Flash",
      },
    ]);
  };

  if (!isOpen) return null;

  return (
    <aside
      style={{
        position: "fixed",
        top: 48,
        right: 0,
        bottom: 0,
        width: isExpanded ? "640px" : "420px",
        maxWidth: "95vw",
        background: "#ffffff",
        borderLeft: "2px solid #e2e8f0",
        boxShadow: "-4px 0 24px rgba(0, 0, 0, 0.12)",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        transition: "width 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >
      {/* ── Top Header (Gemini Gradient Banner) ────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          borderBottom: "1px solid #e2e8f0",
          background: "var(--panel-2)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: "var(--panel-3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 2px 8px rgba(66, 133, 244, 0.35)",
            }}
          >
            <Sparkles size={18} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontWeight: 700, fontSize: 13.5, color: "#0f172a" }}>
                CrimeNet Gemini
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  padding: "1px 6px",
                  borderRadius: 10,
                  background: "#e0e7ff",
                  color: "#4338ca",
                }}
              >
                1.5 Flash
              </span>
            </div>
            <div style={{ fontSize: 10.5, color: "#64748b" }}>
              Grounded in {nodes.length} entities · {caseId}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? "Collapse width" : "Expand width"}
            style={{
              background: "transparent",
              border: "none",
              color: "#64748b",
              cursor: "pointer",
              padding: 6,
              borderRadius: 6,
            }}
          >
            {isExpanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
          <button
            onClick={handleClearChat}
            title="Clear Chat"
            style={{
              background: "transparent",
              border: "none",
              color: "#64748b",
              cursor: "pointer",
              padding: 6,
              borderRadius: 6,
            }}
          >
            <Trash2 size={15} />
          </button>
          <button
            onClick={onClose}
            title="Close Sidebar"
            style={{
              background: "transparent",
              border: "none",
              color: "#64748b",
              cursor: "pointer",
              padding: 6,
              borderRadius: 6,
            }}
          >
            <X size={17} />
          </button>
        </div>
      </div>

      {/* ── Chat Messages Scroll Area ───────────────────────────────────────── */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "14px 14px",
          display: "flex",
          flexDirection: "column",
          gap: 14,
          background: "#f8fafc",
        }}
      >
        {messages.map((m) => {
          const isUser = m.sender === "user";
          return (
            <div
              key={m.id}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: isUser ? "flex-end" : "flex-start",
                maxWidth: "100%",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  flexDirection: isUser ? "row-reverse" : "row",
                  maxWidth: "92%",
                }}
              >
                {!isUser ? (
                  <div
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: "50%",
                      background: "var(--panel-3)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                  >
                    <Sparkles size={14} color="#ffffff" />
                  </div>
                ) : (
                  <div
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: "50%",
                      background: "#334155",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                  >
                    <User size={14} color="#ffffff" />
                  </div>
                )}

                <div
                  style={{
                    background: isUser ? "#1e293b" : "#ffffff",
                    color: isUser ? "#f8fafc" : "#0f172a",
                    padding: isUser ? "9px 13px" : "12px 14px",
                    borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                    border: isUser ? "none" : "1px solid #e2e8f0",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                    fontSize: 12.5,
                    lineHeight: 1.55,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {m.text}

                  {m.newNodes && m.newNodes.length > 0 && (
                    <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {m.newNodes.map((nn) => (
                        <button
                          key={nn.id}
                          onClick={() => onSelectNode?.(nn.id)}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            padding: "2px 7px",
                            borderRadius: 12,
                            background: "#ecfdf5",
                            color: "#059669",
                            border: "1px solid #a7f3d0",
                            fontSize: 11,
                            cursor: "pointer",
                            fontWeight: 600,
                          }}
                        >
                          <span>{nn.label}</span>
                          <ArrowUpRight size={11} />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Message metadata / copy footer */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginTop: 3,
                  marginRight: isUser ? 34 : 0,
                  marginLeft: !isUser ? 34 : 0,
                  fontSize: 10,
                  color: "#94a3b8",
                }}
              >
                <span>{m.timestamp}</span>
                {!isUser && (
                  <>
                    <span>·</span>
                    <span>{m.model}</span>
                    <span>·</span>
                    <button
                      onClick={() => handleCopy(m.id, m.text)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#94a3b8",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: 2,
                        padding: 0,
                      }}
                    >
                      {copiedId === m.id ? (
                        <>
                          <Check size={11} color="#16a34a" /> <span style={{ color: "#16a34a" }}>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={11} /> Copy
                        </>
                      )}
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              style={{
                width: 26,
                height: 26,
                borderRadius: "50%",
                background: "var(--panel-3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Sparkles size={14} color="#ffffff" />
            </div>
            <div
              style={{
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                padding: "8px 14px",
                borderRadius: "16px 16px 16px 4px",
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 12,
                color: "#64748b",
              }}
            >
              <Loader2 size={14} className="spin" />
              <span>Gemini is synthesizing graph metrics & legal provisions...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Suggestion Prompt Chips ─────────────────────────────────────────── */}
      <div
        style={{
          padding: "6px 12px",
          background: "#ffffff",
          borderTop: "1px solid #f1f5f9",
          display: "flex",
          gap: 6,
          overflowX: "auto",
          whiteSpace: "nowrap",
          scrollbarWidth: "none",
        }}
      >
        {SUGGESTED_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(prompt)}
            disabled={loading}
            style={{
              padding: "4px 9px",
              borderRadius: 14,
              border: "1px solid #e2e8f0",
              background: "#f8fafc",
              color: "#334155",
              fontSize: 11,
              fontWeight: 500,
              cursor: "pointer",
              flexShrink: 0,
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "#eef2ff";
              e.currentTarget.style.borderColor = "#c7d2fe";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "#f8fafc";
              e.currentTarget.style.borderColor = "#e2e8f0";
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* ── Bottom Input Box ────────────────────────────────────────────────── */}
      <div
        style={{
          padding: "10px 12px",
          background: "#ffffff",
          borderTop: "1px solid #e2e8f0",
        }}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          style={{
            display: "flex",
            alignItems: "center",
            background: "#f1f5f9",
            borderRadius: 22,
            padding: "4px 8px 4px 14px",
            border: "1px solid #cbd5e1",
            boxShadow: "inset 0 1px 2px rgba(0,0,0,0.04)",
          }}
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Gemini or paste suspect narrative facts..."
            disabled={loading}
            style={{
              flex: 1,
              border: "none",
              background: "transparent",
              outline: "none",
              fontSize: 12.5,
              color: "#0f172a",
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              border: "none",
              background: input.trim() && !loading
                ? "#4fc3f7"
                : "#cbd5e1",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: input.trim() && !loading ? "pointer" : "default",
              transition: "transform 0.15s ease",
            }}
          >
            <Send size={14} />
          </button>
        </form>
        <div style={{ textAlign: "center", fontSize: 9.5, color: "#94a3b8", marginTop: 5 }}>
          CrimeNet Gemini provides decision-support intelligence for verified law enforcement officers.
        </div>
      </div>
    </aside>
  );
}
