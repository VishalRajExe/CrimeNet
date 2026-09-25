"""Small, dependency-free request authentication helpers for CrimeNet.

The API intentionally uses two headers for the local/basic access layer:

* ``X-API-Key`` identifies the calling client.
* ``X-Officer-Badge`` identifies the investigator making the request.

The API key is compared with ``secrets.compare_digest`` and the badge is
validated against a configured allowlist.  This module does not log secrets.
"""

from __future__ import annotations

import re
import secrets
from typing import Iterable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .config import CRIMENET_API_KEY, OFFICER_BADGES

API_KEY_HEADER = "X-API-Key"
OFFICER_BADGE_HEADER = "X-Officer-Badge"
_BADGE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,31}$")


class AccessControlError(Exception):
    """An authentication/authorization failure safe to return to clients."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def normalize_badge(value: str) -> str:
    """Normalize badge formatting without changing its meaningful content."""
    return value.strip().upper()


def validate_api_key(value: str | None) -> None:
    """Require a configured API key and a matching request header."""
    if not CRIMENET_API_KEY:
        raise AccessControlError(
            503,
            "API access is not configured. Set CRIMENET_API_KEY on the server.",
        )

    supplied = (value or "").strip()
    if not supplied or not secrets.compare_digest(supplied, CRIMENET_API_KEY):
        raise AccessControlError(401, "Invalid or missing API credentials.")


def validate_officer_badge(value: str | None, allowed_badges: Iterable[str] = OFFICER_BADGES) -> str:
    """Validate the officer badge and return its canonical representation."""
    badge = normalize_badge(value or "")
    if not badge or not _BADGE_PATTERN.fullmatch(badge):
        raise AccessControlError(401, "A valid officer badge is required.")

    allowed = {normalize_badge(item) for item in allowed_badges if item and item.strip()}
    if not allowed:
        raise AccessControlError(
            503,
            "Officer access is not configured. Set CRIMENET_OFFICER_BADGES on the server.",
        )
    if badge not in allowed:
        raise AccessControlError(403, "Officer badge is not authorized for this service.")
    return badge


def validate_request_headers(request: Request) -> str:
    """Validate both required headers and return the canonical badge."""
    try:
        validate_api_key(request.headers.get(API_KEY_HEADER))
        return validate_officer_badge(request.headers.get(OFFICER_BADGE_HEADER))
    except AccessControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def require_matching_badge(request: Request, submitted_badge: str | None) -> str:
    """Ensure an optional body/form badge agrees with the authenticated header."""
    header_badge = getattr(request.state, "officer_badge", None)
    if not header_badge:
        # This should only be reachable if middleware was accidentally removed.
        raise HTTPException(status_code=401, detail="Officer badge was not authenticated.")

    if submitted_badge and normalize_badge(submitted_badge) != header_badge:
        raise HTTPException(
            status_code=403,
            detail="Officer badge in the request does not match X-Officer-Badge.",
        )
    return header_badge


async def api_access_middleware(request: Request, call_next):
    """Protect ``/api/*`` while allowing health, docs, and CORS preflight.

    This is middleware rather than a wildcard route dependency so every current
    and future API endpoint is covered automatically.  ``OPTIONS`` is left
    alone so the CORS layer can answer preflight requests before credentials
    are sent by the browser.
    """
    path = request.url.path
    if request.method == "OPTIONS" or not path.startswith("/api/"):
        return await call_next(request)

    try:
        badge = validate_officer_badge(request.headers.get(OFFICER_BADGE_HEADER))
        validate_api_key(request.headers.get(API_KEY_HEADER))
    except AccessControlError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    request.state.officer_badge = badge
    return await call_next(request)
