# CrimeNet AI — Team Handover & Architecture Guide

> **Target Audience:** Engineering Teammates & Collaborators  
> **Repository:** [CrimeNet (Branch: `big-updates`)](https://github.com/PG300604/CrimeNet)  
> **Status:** ✅ Core Multi-Tier Architecture, Gemini 2.5 Flash Copilot, Left Sidebar UI & 6 Tactical Tasks Fully Operational

---

## 1. Executive Summary

CrimeNet AI is an Explainable Intelligence & Criminal Network Analysis Platform tailored for Indian Law Enforcement. It transforms unstructured narratives (FIRs, suspect interrogations, CDR call logs, bank transaction ledgers) into interactive, topological intelligence graphs backed by Google Gemini 2.5 Flash, GraphRAG, and machine learning anomaly detection.

---

## 2. Multi-Tier Architecture

```
                          ┌───────────────────────────┐
                          │   React 18 + Cytoscape    │
                          │   Left Gemini Copilot UI  │
                          └─────────────┬─────────────┘
                                        │ REST / JSON
                                        ▼
                          ┌───────────────────────────┐
                          │   FastAPI Gateway (:8000) │
                          └─────────────┬─────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
┌──────────────────┐          ┌───────────────────┐          ┌──────────────────┐
│ Relational Store │          │  Neo4j / NetworkX │          │     GraphRAG     │
│  (SQLite/MySQL)  │          │ Operational Graph │          │  (Vector Store   │
│ Cases & Evidence │          │  Adjacency & Paths│          │ + Sentence Trans)│
└──────────────────┘          └───────────────────┘          └──────────────────┘
         │                              │                              │
         └──────────────────────────────┼──────────────────────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │    Python Intelligence    │
                          │ - PageRank / Centralities │
                          │ - 3-Hop Mule Tracing      │
                          │ - Isolation Forest ML     │
                          │ - Bridges & Cut Vertices  │
                          └─────────────┬─────────────┘
                                        │ Grounded Prompts
                                        ▼
                          ┌───────────────────────────┐
                          │   Google Gemini Agent     │
                          │    (gemini-2.5-flash)     │
                          │ - Statutory Legal Notices │
                          │ - Syndicate Dossiers      │
                          │ - Evidence Ingestion NER  │
                          └───────────────────────────┘
```

---

## 3. Work Completed Till Now

### A. AI Agent & Reasoning Engine (`backend/agentic/gemini_agent.py`)
- **Direct Gemini 2.5 Flash REST Integration**: Connects via `httpx` to Google Generative Language API (`v1beta/models/gemini-2.5-flash:generateContent`).
- **6 Built-in Tactical Intelligence Tasks**:
  1. **🎯 Syndicate Hierarchy & Kingpin Identification**: Computes Degree, Betweenness, and PageRank centralities on active graphs using NetworkX to pinpoint kingpins, lieutenants, and mules.
  2. **💸 3-Hop Money Trail & Mule Account Tracing**: Traverses multi-hop financial transactions (UPI -> Mule Account -> Shell Company -> Cash Withdrawal), identifies suspicious flow volume, and flags intermediary laundering nodes.
  3. **🌲 Isolation Forest Anomaly Detection**: Uses `scikit-learn` `IsolationForest` on feature vectors (degree, edge weight volume, threat score, betweenness) to compute anomaly scores and detect stealthy outlier nodes.
  4. **⚖️ Section 102 CrPC Account Freeze Order**: Automatically generates formal, court-admissible legal orders citing Section 102 of the Code of Criminal Procedure (CrPC), 1973 for freezing mule and shell bank accounts.
  5. **💥 Communication Bridges & Cut Vertices**: Computes articulation points (`nx.articulation_points`) and bridge edges (`nx.bridges`) whose neutralization fragments the criminal syndicate.
  6. **📜 GraphRAG Evidence Citations**: Performs similarity retrieval over chunked case evidence files with verifiable source metadata and paragraph citations.
- **Narrative Entity & Relation Extraction**: If natural language text describes criminal incidents (names, phone numbers, UPI IDs, locations), Gemini extracts entities and merges them directly into the live graph.

### B. Left Sidebar Gemini Copilot UI (`frontend/src/`)
- **Left Panel Redesign (`frontend/src/components/GeminiLeftChatbot.jsx`)**:
  - Embedded seamlessly on the left side of the dashboard.
  - Tab Switcher: Seamlessly toggle between **Gemini Copilot** (`gemini-mode`, 420px width) and traditional **Control Boxes** (Nodes, Edges, Labels).
  - Quick Action Chips for all 6 core tasks with one-click execution.
  - Evidence attachment button to upload files (PDFs, TXT, CSVs) directly into GraphRAG and update the canvas in real time.
  - Markdown message rendering with copyable code blocks, legal notices, and entity badges.
- **Top Command Bar Streamlining (`frontend/src/components/TacticalCommandBar.jsx`)**:
  - Removed cluttered top search inputs.
  - Replaced with a sleek telemetry bar: Active Case badge, Live Node/Edge counters, Gemini 2.5 Flash status indicator, and Theme Toggle.

### C. Backend Configuration & Security (`backend/config.py`, `.env`)
- Added zero-dependency `.env` file loader in `backend/config.py`.
- Removed hardcoded credentials to comply with GitHub Secret Scanning push protection.
- Created `.env.example` template.

---

## 4. How to Set Up & Run Locally

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Node.js 18+ & npm
- Git

### Step 1: Environment Variables
Create a `.env` file in the project root (`p:\CrimeNet\.env`):
```env
CRIMENET_API_KEY=replace_with_a_long_random_api_key
CRIMENET_OFFICER_BADGES=INSP-4409
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
LLM_PROVIDER=gemini
OPENAI_API_KEY=
HOST=127.0.0.1
PORT=8000
```

Every `/api/*` request must include `X-API-Key` and `X-Officer-Badge`.
For local frontend development, copy the same key and badge into
`frontend/.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000/api
VITE_CRIMENET_API_KEY=replace_with_the_same_key_as_backend/.env
VITE_OFFICER_BADGE=INSP-4409
```

The API key is intended for the basic local access layer. A production
deployment should use a same-origin gateway or session-based authentication
instead of exposing a long-lived key in browser JavaScript.

### Step 2: Start the FastAPI Backend
```powershell
# From the repository root
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
*API Swagger Documentation will be accessible at: `http://127.0.0.1:8000/docs`*

### Step 3: Start the React Frontend
```powershell
cd frontend
npm install   # If dependencies are not already installed
npm run dev -- --host 127.0.0.1 --port 5173
```
*Frontend UI will be accessible at: `http://127.0.0.1:5173`*

---

## 5. Teammate Roadmap & Planned Next Steps

Here is the prioritized backlog for the next phase of development:

### 1. Neo4j & MySQL Live Persistence (Optional Enterprise Tier)
- **Current State**: Uses in-memory graph store with JSON persistence (`backend_storage/`) and fallback SQLite relational store.
- **Next Task**: Enable live Neo4j driver connection in `backend/storage/graph_store.py` and MySQL in `backend/storage/relational_store.py` for multi-analyst concurrent collaboration.

### 2. Multi-Format Evidence Parsers
- **Current State**: GraphRAG ingestion parses plain text, markdown, and basic CSV logs.
- **Next Task**: Enhance `backend/rag/document_loader.py` with `pypdf` / `pdfplumber` for official Indian FIR scan parsing and bank statement OCR.

### 3. Canvas Visual Graph Highlighting on Copilot Clicks
- **Current State**: Nodes mentioned by the Gemini Agent can be clicked to center on the canvas.
- **Next Task**: Add visual pulse/glow animations on the Cytoscape canvas when selecting nodes or highlighting money trails (e.g. coloring path nodes in amber/red).

### 4. Exportable Investigation Reports
- **Current State**: Gemini generates structured Markdown legal orders and dossiers.
- **Next Task**: Add a "Download PDF Dossier" button in `GeminiLeftChatbot.jsx` that compiles the current case summary, topological charts, and Section 102 orders into a signed PDF export.

---

## 6. Key Files Quick Reference

| File | Purpose |
|------|---------|
| `backend/agentic/gemini_agent.py` | Google Gemini 2.5 Flash agent, prompts, topological analysis & NER extraction |
| `backend/main.py` | REST API routes (`/api/gemini/chat`, `/api/investigate/*`, `/api/rag/*`) |
| `backend/config.py` | Environment config, API keys, paths |
| `frontend/src/App.jsx` | Main state controller, tab switcher, canvas layout |
| `frontend/src/components/GeminiLeftChatbot.jsx` | Left sidebar Gemini chatbot with prompt chips & evidence uploader |
| `frontend/src/components/TacticalCommandBar.jsx` | Top telemetry navigation bar |
| `frontend/src/styles/App.css` | Styles for left sidebar `.gemini-mode`, chat bubbles, and layout |
| `.env.example` | Template for environment variables |
