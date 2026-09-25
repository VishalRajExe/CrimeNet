"""
CrimeNet AI - Configuration Settings
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "backend_storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
VECTOR_INDEX_DIR = STORAGE_DIR / "vector_indices"
AUDIT_LOG_PATH = STORAGE_DIR / "audit_ledger.jsonl"
CASES_METADATA_PATH = STORAGE_DIR / "cases_metadata.json"

for d in [STORAGE_DIR, UPLOADS_DIR, VECTOR_INDEX_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Load .env if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

# API Keys & LLM settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # "gemini", "openai", or "offline"

# API access control.  Keep the API key server-side in production; the local
# frontend may use VITE_CRIMENET_API_KEY only for development convenience.
CRIMENET_API_KEY = os.getenv("CRIMENET_API_KEY", "").strip()
_office_badges = os.getenv("CRIMENET_OFFICER_BADGES", "INSP-4409")
OFFICER_BADGES = tuple(
    badge.strip().upper()
    for badge in _office_badges.split(",")
    if badge.strip()
)

# RAG & Embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
SIMILARITY_TOP_K = int(os.getenv("SIMILARITY_TOP_K", "4"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.05"))

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_configured_origins = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in (_configured_origins.split(",") if _configured_origins else _default_origins)
    if origin.strip() and origin.strip() != "*"
]

