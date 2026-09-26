"""Cryptographic and hashing utilities for CrimeNet non-repudiation."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Union


def sha256_hash(data: Union[str, bytes]) -> str:
    """Compute standard SHA-256 hexadecimal digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def compute_evidence_hash(content: Union[str, bytes]) -> str:
    """Compute standardized SHA-256 hash for evidence documents and exhibits."""
    return sha256_hash(content)


def compute_audit_block_hash(prev_hash: str, entry_data: Any) -> str:
    """Compute chained SHA-256 block hash for non-repudiation audit ledger."""
    serialized = json.dumps(entry_data, sort_keys=True, default=str)
    payload = f"{prev_hash}|{serialized}"
    return sha256_hash(payload)
