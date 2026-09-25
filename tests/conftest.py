"""Shared test configuration for the authenticated backend."""

import os

# Set these before backend modules are imported by test modules.
os.environ.setdefault("CRIMENET_API_KEY", "test-crimenet-api-key-please-change")
os.environ.setdefault("CRIMENET_OFFICER_BADGES", "INSP-4409")
os.environ.setdefault(
    "CORS_ORIGINS",
    "http://testserver,http://127.0.0.1:5173",
)
