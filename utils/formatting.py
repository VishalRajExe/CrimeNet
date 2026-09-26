"""Formatting and parsing utilities for CrimeNet."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def format_utc_timestamp(dt: Optional[datetime] = None) -> str:
    """Return standard UTC ISO-formatted timestamp."""
    now = dt or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S UTC")


def format_currency_inr(amount: float | int) -> str:
    """Format numeric amount into INR currency representation."""
    val = float(amount)
    if val >= 10_000_000:
        return f"₹{val / 10_000_000:.2f} Cr"
    if val >= 100_000:
        return f"₹{val / 100_000:.2f} Lakh"
    return f"₹{val:,.2f}"


def clean_entity_id(raw_id: str) -> str:
    """Normalize raw entity ID to consistent format."""
    return str(raw_id).strip().lower().replace(" ", "_")
