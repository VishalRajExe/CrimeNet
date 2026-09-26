"""CrimeNet Central Configuration Module."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

# Base Project Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "backend_storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "generated_reports"
AUDIT_LOG_PATH = STORAGE_DIR / "audit_ledger.jsonl"

for d in [STORAGE_DIR, UPLOADS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Load .env file
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

# Database Settings
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "crimenet")
SQLITE_FALLBACK_PATH = BASE_DIR / "storage" / "crimenet_cases.db"

# Neo4j Settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "crimenet123")

# LLM & AI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GROK_API_KEY = os.getenv("GROK_API_KEY", os.getenv("XAI_API_KEY", ""))
GROK_API_BASE = os.getenv("GROK_API_BASE", os.getenv("GROK_BASE_URL", "https://api.x.ai/v1"))
GROK_MODEL = os.getenv("GROK_MODEL", "grok-2-latest")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "grok" if GROK_API_KEY else "gemini")

# Security & Access Control
CRIMENET_API_KEY = os.getenv("CRIMENET_API_KEY", "").strip()
_raw_badges = os.getenv("CRIMENET_OFFICER_BADGES", "INSP-4409,OFFICER-001,LEAD-INV")
OFFICER_BADGES: Tuple[str, ...] = tuple(
    b.strip().upper() for b in _raw_badges.split(",") if b.strip()
)

# API Server Settings
API_HOST = os.getenv("HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", "8000"))
API_BASE_URL = os.getenv("CRIMENET_API_URL", f"http://127.0.0.1:{API_PORT}")
CORS_ORIGINS: List[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8050",
    "http://127.0.0.1:8050",
]
