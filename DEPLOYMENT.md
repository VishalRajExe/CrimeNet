# CrimeNet AI Deployment Guide

This repository contains two different applications:

- **Current prototype:** FastAPI backend + React/Vite frontend in `backend/` and `frontend/`
- **Legacy visualizer:** Dash application using the repository-root `requirements.txt`

The deployment files in this guide deploy the **current FastAPI + React prototype**, not the legacy Dash visualizer.

## Recommended deployment: Render

The included `render.yaml` builds and serves both parts as one web service:

1. Installs `backend/requirements.txt`
2. Builds `frontend/` with Vite
3. Starts FastAPI with Uvicorn
4. Serves `frontend/dist` from the FastAPI process

This avoids maintaining separate frontend and backend services for the reviewer prototype.

## 1. Push the current code

Push the current branch to the GitHub repository that Render can access. Make sure these files are included:

```text
render.yaml
Procfile
requirements-deploy.txt
backend/
frontend/
frontend/package-lock.json
```

Do not commit `.env` or `frontend/.env.local`.

## 2. Create the Render service

1. Sign in to [Render](https://render.com).
2. Choose **New + → Web Service**.
3. Connect the GitHub repository.
4. Render can use the repository's `render.yaml` blueprint, or you can enter these values manually:

| Setting | Value |
|---|---|
| Runtime | Python |
| Build command | See `render.yaml` |
| Start command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Instance | Free, for the prototype |

## 3. Set environment variables

Set these in Render:

### Required

```text
CRIMENET_API_KEY=<long random secret>
```

The build command passes this same value to Vite as `VITE_CRIMENET_API_KEY` so the prototype frontend can call the API.

### Optional

```text
GEMINI_API_KEY=<real Gemini key>
LLM_PROVIDER=gemini
```

For a no-key reviewer demo, leave:

```text
LLM_PROVIDER=offline
```

The copilot will use its deterministic local fallback.

### Officer access

The default prototype badge is:

```text
INSP-4409
```

To allow more badges, set a comma-separated list:

```text
CRIMENET_OFFICER_BADGES=INSP-4409,INSP-1234
```

## 4. CORS

The default Render configuration allows the Render service origin. CORS is not used for same-origin requests, but the explicit setting is kept for API clients and future separate frontend hosting.

Do not set `CORS_ORIGINS=*`.

## 5. After deployment

The service exposes:

```text
/                         React prototype
/health                   public health check
/docs                     Swagger API documentation
/openapi.json             OpenAPI schema
/api/*                    authenticated API endpoints
```

Example:

```text
https://crimenet-ai.onrender.com/
https://crimenet-ai.onrender.com/docs
```

## Local verification before pushing

From the repository root:

```powershell
python -m pytest tests/test_backend_auth.py tests/test_backend_rag.py -q
npm --prefix frontend run build
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal:

```powershell
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

## Prototype security note

The current API-key flow is appropriate for a reviewer prototype, but a Vite variable is embedded in browser JavaScript. Before handling real evidence or real users, replace it with an HttpOnly session/login flow, role-based access control, persistent storage, and a proper secret-management strategy.
