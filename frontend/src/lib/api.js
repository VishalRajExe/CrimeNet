/**
 * api.js — authenticated CrimeNet REST client.
 *
 * The browser client sends the two headers required by the FastAPI gateway:
 *   X-API-Key and X-Officer-Badge
 *
 * For local development, values come from Vite environment variables. A
 * production deployment should preferably terminate authentication at a
 * same-origin gateway rather than expose a long-lived key in browser JavaScript.
 */

const defaultApiUrl = import.meta.env.DEV ? "http://127.0.0.1:8000/api" : "/api";
const configuredApiUrl = import.meta.env.VITE_API_URL || defaultApiUrl;
const API_URL = configuredApiUrl.replace(/\/+$/, "");
const API_ROOT = import.meta.env.VITE_API_ROOT || API_URL.replace(/\/api$/, "");
const configuredApiKey =
  import.meta.env.VITE_CRIMENET_API_KEY || import.meta.env.VITE_API_KEY || "";
const configuredOfficerBadge = import.meta.env.VITE_OFFICER_BADGE || "INSP-4409";

function readSessionValue(key) {
  if (typeof window === "undefined") return "";
  try {
    return window.sessionStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function getApiKey() {
  return readSessionValue("crimenet_api_key") || configuredApiKey;
}

function getOfficerBadge() {
  return readSessionValue("crimenet_officer_badge") || configuredOfficerBadge;
}

function authHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  const apiKey = getApiKey();
  if (apiKey) headers["X-API-Key"] = apiKey;
  headers["X-Officer-Badge"] = getOfficerBadge();
  return headers;
}

async function responseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.message || `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

async function request(path, options = {}) {
  if (!getApiKey()) {
    throw new Error(
      "CrimeNet API key is not configured. Set VITE_CRIMENET_API_KEY in frontend/.env.local.",
    );
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: authHeaders(options.headers),
  });

  if (!response.ok) {
    const error = new Error(await responseError(response));
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  // Public health check (the root endpoint does not expose case data).
  checkHealth: async () => {
    try {
      const healthUrl = API_ROOT ? `${API_ROOT}/health` : "/health";
      const response = await fetch(healthUrl, { headers: authHeaders() });
      if (!response.ok) return null;
      return await response.json();
    } catch (err) {
      console.warn("Backend not reachable:", err);
      return null;
    }
  },

  // 1. Cases
  getCases: async () => request("/cases"),

  createCase: async (caseData) =>
    request("/cases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...caseData,
        officer_badge: getOfficerBadge(),
      }),
    }),

  // 2. Graph
  getGraph: async (caseId) => request(`/graph/${encodeURIComponent(caseId)}`),

  // 3. Narrative ingestion
  submitNarrative: async (narrative, caseId = "CASE-2024-MH-088") =>
    request("/investigate/narrative", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        narrative,
        case_id: caseId,
        officer_badge: getOfficerBadge(),
      }),
    }),

  // 4. Evidence upload
  uploadEvidence: async (file, caseId = "CASE-2024-MH-088") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("case_id", caseId);
    formData.append("officer_badge", getOfficerBadge());

    return request("/investigate/upload", {
      method: "POST",
      body: formData,
    });
  },

  // 5. Entity dossier
  getEntityDossier: async (nodeId, caseId = "CASE-2024-MH-088") =>
    request(
      `/entity/${encodeURIComponent(nodeId)}/dossier?case_id=${encodeURIComponent(caseId)}`,
    ),

  // 6. Follow the Money
  followTheMoney: async (seedNodeId, caseId = "CASE-2024-MH-088", maxHops = 3) =>
    request("/analytics/follow-money", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        seed_node_id: seedNodeId,
        case_id: caseId,
        max_hops: maxHops,
      }),
    }),

  // 7. Human-in-the-loop feedback
  submitFeedback: async (feedbackPrompt, caseId = "CASE-2024-MH-088") =>
    request("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        feedback_prompt: feedbackPrompt,
        case_id: caseId,
        officer_badge: getOfficerBadge(),
      }),
    }),

  // 8. Action dispatch
  dispatchAction: async (actionId, entityId, caseId = "CASE-2024-MH-088", parameters = {}) =>
    request("/actions/dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action_id: actionId,
        entity_id: entityId,
        case_id: caseId,
        officer_badge: getOfficerBadge(),
        parameters,
      }),
    }),

  // 9. Timeline and alerts
  getTimeline: async (caseId = "CASE-2024-MH-088") =>
    request(`/cases/${encodeURIComponent(caseId)}/timeline`),

  getAlerts: async (caseId = "CASE-2024-MH-088") =>
    request(`/alerts?case_id=${encodeURIComponent(caseId)}`),

  // 10. Prosecutor report
  getProsecutorReport: async (caseId = "CASE-2024-MH-088") =>
    request(`/cases/${encodeURIComponent(caseId)}/report`),

  // 11. Python graph analytics
  runPythonAnalysis: async ({ nodes, edges, functionId, algoId }) =>
    request("/intelligence/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nodes, edges, functionId, algoId }),
    }),

  // 12. Isolation Forest anomalies
  getAnomalies: async ({ nodes, edges }) =>
    request("/intelligence/anomalies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nodes, edges }),
    }),

  // 13. GraphRAG query
  queryGraphRAG: async (caseId, query, topK = 5) =>
    request("/intelligence/graphrag/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_id: caseId, query, top_k: topK }),
    }),

  // 14. LangGraph workflow
  runAgenticWorkflow: async ({
    caseId = "CASE-2024-MH-088",
    query,
    targetEntity = null,
    nodes = null,
    edges = null,
  }) =>
    request("/intelligence/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        case_id: caseId,
        query,
        target_entity: targetEntity,
        nodes,
        edges,
      }),
    }),

  // 15. Relational store
  getDbCases: async () => request("/database/cases"),

  getDbEvidence: async (caseId) =>
    request(`/database/evidence/${encodeURIComponent(caseId)}`),

  // 16. Investigative copilot
  geminiChat: async ({
    message,
    caseId = "CASE-2024-MH-088",
    history = [],
    nodes = null,
    edges = null,
  }) =>
    request("/gemini/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        case_id: caseId,
        history,
        nodes,
        edges,
      }),
    }),
};
