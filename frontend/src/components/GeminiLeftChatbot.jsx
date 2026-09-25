/**
 * GeminiLeftChatbot.jsx — Embedded Google Gemini 2.5 Flash AI Chatbot
 * Housed directly inside the Left Sidebar alongside the Control Boxes.
 * 
 * Features:
 * - Direct execution of 6 Core Tactical Intelligence Tasks:
 *   1. 🎯 Identify syndicate hierarchy & kingpin
 *   2. 💸 Trace 3-hop money trail & mule accounts
 *   3. 🌲 Run Isolation Forest anomaly detection
 *   4. ⚖️ Draft Section 102 CrPC account freeze order
 *   5. 💥 Find critical communication bridges (cut vertices)
 *   6. 📜 Summarize GraphRAG evidence citations
 * - Natural Language Narrative Ingestion (extracts nodes & edges directly into active graph)
 * - Evidence attachment upload (PDF, CSV, TXT)
 * - 1-Click Copy, markdown formatting, and interactive clickable entity chips
 */

import React, { useState, useRef, useEffect } from "react";
import {
  Sparkles, Send, Bot, User, Trash2, Copy, Check, Paperclip,
  ArrowUpRight, Loader2, ShieldAlert, FileText, CheckCircle2
} from "lucide-react";
import { api } from "../lib/api";

const SUGGESTED_PROMPTS = [
  { label: "Syndicate hierarchy", prompt: "Identify syndicate hierarchy & kingpin" },
  { label: "3-hop money trail", prompt: "Trace 3-hop money trail & mule accounts" },
  { label: "Isolation Forest anomalies", prompt: "Run Isolation Forest anomaly detection" },
  { label: "Section 102 freeze order", prompt: "Draft Section 102 CrPC account freeze order" },
  { label: "Critical bridges", prompt: "Find critical communication bridges (cut vertices)" },
  { label: "Evidence citations", prompt: "Summarize GraphRAG evidence citations" },
];

export default function GeminiLeftChatbot({
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
      text: `### CrimeNet Intelligence\n\nI am your investigative analysis assistant, grounded in the active network topology (**${nodes.length} entities**, **${edges.length} edges**), anomaly metrics, and indexed evidence.\n\nChoose an inquiry below or paste suspect facts to extend the graph:`,
      timestamp: "Just now",
      model: "AI Assistant",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [attachedFile, setAttachedFile] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAttachedFile(file);
      onToast?.(`Evidence attached: ${file.name}`);
    }
  };

  const handleSend = async (overridePrompt) => {
    const query = (overridePrompt || input).trim();
    if (!query && !attachedFile) return;

    const userText = query || (attachedFile ? `Uploaded evidence file: ${attachedFile.name}` : "");
    const userMsgId = `usr_${Date.now()}`;
    const userMsg = {
      id: userMsgId,
      sender: "user",
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      // 1. If file attached, upload and index via RAG
      if (attachedFile) {
        onToast?.(`Indexing evidence: ${attachedFile.name}...`);
        const uploadRes = await api.uploadEvidence(attachedFile, caseId);
        if (uploadRes?.graph?.nodes) {
          onGraphUpdate?.(uploadRes.graph.nodes, uploadRes.graph.edges);
        }
        setAttachedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }

      // 2. Query Gemini Agent with contextual grounding
      const historyPayload = messages.slice(-6).map((m) => ({
        role: m.sender === "user" ? "user" : "model",
        text: m.text,
      }));

      const res = await api.geminiChat({
        message: query || "Analyze the attached evidence document",
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
        model: "CrimeNet AI",
        extractedCount: res.extractedCount || 0,
        newNodes: res.newNodes || [],
      };

      setMessages((prev) => [...prev, geminiMsg]);

      // If narrative ingestion yielded new nodes/edges, notify canvas!
      if (res.newNodes && res.newNodes.length > 0) {
        onToast?.(`[AI Extraction] Added ${res.newNodes.length} entities to operational graph.`);
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
      console.error("Gemini Left Chatbot Error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: "gemini",
          text: `⚠️ **Service Notice**: ${err.message || "Backend offline"}. Please verify connection to port 8000.`,
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
        text: "Chat cleared. The active graph context and indexed evidence remain available.", 
        timestamp: "Just now",
        model: "AI Assistant",
      },
    ]);
  };

  return (
    <div
      className="gemini-copilot"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
        background: "var(--panel, #ffffff)",
        borderRadius: 6,
        overflow: "hidden",
      }}
    >
      {/* ── Subheader / Telemetry Bar ───────────────────────────────────────── */}
      <div
        className="gemini-subheader"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "7px 10px",
          background: "var(--panel-2)",
          borderBottom: "1px solid var(--border, #e2e8f0)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div
            className="gemini-avatar"
            style={{
              width: 22,
              height: 22,
              borderRadius: "50%",
              background: "var(--panel-3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 1px 4px rgba(66, 133, 244, 0.3)",
            }}
          >
            <Sparkles size={12} color="#ffffff" />
          </div>
          <div>
            <span className="gemini-subheader-title" style={{ fontSize: 11.5, fontWeight: 700, color: "var(--text-1, #0f172a)" }}>
              AI Chatbox
            </span>
            <span className="gemini-status" style={{ fontSize: 10, color: "#10b981", marginLeft: 6, fontWeight: 600 }}>
              ● Online
            </span>
          </div>
        </div>

        <button
          onClick={handleClearChat}
          aria-label="Clear chat history"
          title="Clear Chat History"
          style={{
            background: "transparent",
            border: "none",
            color: "#94a3b8",
            cursor: "pointer",
            padding: 4,
            borderRadius: 4,
          }}
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* ── Quick Tactical Prompt Chips ─────────────────────────────────────── */}
      <div
        className="gemini-prompt-strip"
        style={{
          padding: "6px 8px",
          background: "var(--panel)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          gap: 4,
          overflowX: "auto",
          whiteSpace: "nowrap",
          scrollbarWidth: "none",
          flexShrink: 0,
        }}
      >
        {SUGGESTED_PROMPTS.map((item, idx) => (
          <button
            key={idx}
            className="gemini-prompt-chip"
            onClick={() => handleSend(item.prompt)}
            disabled={loading}
            style={{
              padding: "3px 8px",
              borderRadius: 12,
              border: "1px solid var(--border-2)",
              background: "var(--panel-2)",
              color: "var(--text)",
              boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
              fontSize: 10.5,
              fontWeight: 500,
              cursor: "pointer",
              flexShrink: 0,
              transition: "all 0.15s ease",
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* ── Chat Messages Scroll Area ───────────────────────────────────────── */}
      <div
        className="gemini-messages"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "10px",
          display: "flex",
          flexDirection: "column",
          gap: 12,
          background: "var(--bg)",
        }}
      >
        {messages.map((m) => {
          const isUser = m.sender === "user";
          return (
            <div
              key={m.id}
              className="gemini-message-row"
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
                  gap: 6,
                  flexDirection: isUser ? "row-reverse" : "row",
                  maxWidth: "96%",
                }}
              >
                {!isUser ? (
                  <div
                    className="gemini-avatar"
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: "50%",
                      background: "var(--panel-3)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                  >
                    <Sparkles size={12} color="#ffffff" />
                  </div>
                ) : (
                  <div
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: "50%",
                      background: "#334155",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                  >
                    <User size={12} color="#ffffff" />
                  </div>
                )}

                <div
                  className={`gemini-message-bubble ${isUser ? "user" : "assistant"}`}
                  style={{
                    background: isUser ? "linear-gradient(135deg, var(--teal), #0284c7)" : "var(--panel-2)",
                    color: isUser ? "#ffffff" : "var(--text)",
                    padding: isUser ? "9px 13px" : "11px 14px",
                    borderRadius: isUser ? "14px 14px 3px 14px" : "14px 14px 14px 3px",
                    border: isUser ? "none" : "1px solid var(--border-2)",
                    boxShadow: isUser ? "0 4px 14px rgba(2, 132, 199, 0.3)" : "0 3px 12px rgba(0,0,0,0.15)",
                    fontSize: 12,
                    lineHeight: 1.5,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {m.text}

                  {m.newNodes && m.newNodes.length > 0 && (
                    <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {m.newNodes.map((nn) => (
                        <button
                          key={nn.id}
                          className="gemini-entity-chip"
                          onClick={() => onSelectNode?.(nn.id)}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 3,
                            padding: "2px 6px",
                            borderRadius: 10,
                            background: "#ecfdf5",
                            color: "#059669",
                            border: "1px solid #a7f3d0",
                            fontSize: 10.5,
                            cursor: "pointer",
                            fontWeight: 600,
                          }}
                        >
                          <span>{nn.label}</span>
                          <ArrowUpRight size={10} />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Message metadata & copy button */}
              <div
                className="gemini-message-meta"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginTop: 3,
                  marginRight: isUser ? 28 : 0,
                  marginLeft: !isUser ? 28 : 0,
                  fontSize: 9.5,
                  color: "#94a3b8",
                }}
              >
                <span>{m.timestamp}</span>
                {!isUser && (
                  <>
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
                          <Check size={10} color="#16a34a" /> <span style={{ color: "#16a34a" }}>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={10} /> Copy
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
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div
              className="gemini-avatar"
              style={{
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: "var(--panel-3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Sparkles size={12} color="#ffffff" />
            </div>
            <div
              className="gemini-message-bubble assistant"
              style={{
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                padding: "6px 10px",
                borderRadius: "14px 14px 14px 3px",
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                color: "#64748b",
              }}
            >
              <Loader2 size={12} className="spin" />
              <span>Analyzing your request...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Attached File Indicator ─────────────────────────────────────────── */}
      {attachedFile && (
        <div
          className="gemini-attachment"
          style={{
            padding: "4px 10px",
            background: "#eff6ff",
            borderTop: "1px solid #bfdbfe",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: 11,
            color: "#1d4ed8",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <FileText size={12} />
            <span>Attached: {attachedFile.name}</span>
          </div>
          <button
            onClick={() => setAttachedFile(null)}
            style={{
              background: "none",
              border: "none",
              color: "#6b7280",
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Bottom Input & Action Bar ───────────────────────────────────────── */}
      <div
        className="gemini-composer"
        style={{
          padding: "8px 10px",
          background: "var(--panel)",
          borderTop: "1px solid var(--border)",
          flexShrink: 0,
        }}
      >
        <form
          className="gemini-composer-form"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          style={{
            display: "flex",
            alignItems: "center",
            background: "var(--bg-2)",
            borderRadius: 20,
            padding: "3px 6px 3px 10px",
            border: "1px solid var(--border-2)",
            boxShadow: "inset 0 1px 3px rgba(0,0,0,0.1)",
          }}
        >
          {/* File Attachment Input */}
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            aria-label="Upload evidence file"
            accept=".pdf,.csv,.txt"
            onChange={handleFileChange}
          />
          <button
            type="button"
            className={`gemini-composer-attach ${attachedFile ? "active" : ""}`}
            onClick={() => fileInputRef.current?.click()}
            title="Attach FIR PDF / CDR CSV"
            style={{
              background: "none",
              border: "none",
              color: attachedFile ? "#2563eb" : "#64748b",
              cursor: "pointer",
              padding: 4,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginRight: 4,
            }}
          >
            <Paperclip size={14} />
          </button>

          <input
            type="text"
            className="gemini-composer-input"
            aria-label="Ask the AI Chatbox"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message here..."
            disabled={loading}
            style={{
              flex: 1,
              border: "none",
              background: "transparent",
              outline: "none",
              fontSize: 11.5,
              color: "var(--text)",
            }}
          />

          <button
            type="submit"
            className="gemini-send-button"
            aria-label="Send message"
            disabled={(!input.trim() && !attachedFile) || loading}
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              border: "none",
              background: (input.trim() || attachedFile) && !loading
                ? "#4fc3f7"
                : "#cbd5e1",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: (input.trim() || attachedFile) && !loading ? "pointer" : "default",
              transition: "transform 0.15s ease",
            }}
          >
            <Send size={12} />
          </button>
        </form>
      </div>
    </div>
  );
}
