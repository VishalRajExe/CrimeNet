"""
CrimeNet AI - Immutable Audit Ledger
Maintains a tamper-evident, append-only JSONL ledger for all investigative actions,
AI narrative parses, human feedback overrides, and police action dispatches.
Includes cryptographic SHA-256 hash chaining to guarantee integrity.
"""

import os
import json
import time
import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

from .config import AUDIT_LOG_PATH


@dataclass
class AuditEntry:
    audit_id: str
    timestamp: str
    action: str  # 'NARRATIVE_INGESTION', 'DOCUMENT_UPLOAD', 'FEEDBACK_OVERRIDE', 'ACTION_DISPATCH'
    officer_badge: str
    case_id: str
    target_entity: Optional[str]
    details: Dict[str, Any]
    prev_hash: str
    entry_hash: str


class ImmutableAuditLedger:
    """Tamper-evident append-only ledger for CrimeNet investigation audit trails."""

    def __init__(self, log_path: Path = AUDIT_LOG_PATH):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def _get_last_hash(self) -> str:
        """Reads the hash of the last entry in the ledger, or returns genesis hash."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return "0" * 64

        last_line = ""
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()

        if not last_line:
            return "0" * 64

        try:
            data = json.loads(last_line)
            return data.get("entry_hash", "0" * 64)
        except Exception:
            return "0" * 64

    def record_action(
        self,
        action: str,
        case_id: str,
        details: Dict[str, Any],
        officer_badge: str = "INSP-DEFAULT",
        target_entity: Optional[str] = None
    ) -> AuditEntry:
        """Records an action into the immutable audit ledger with hash chaining."""
        prev_hash = self._get_last_hash()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        audit_id = f"AUD_{int(time.time() * 1000)}_{action[:4]}"

        payload_to_hash = f"{prev_hash}|{audit_id}|{timestamp}|{action}|{officer_badge}|{case_id}|{json.dumps(details, sort_keys=True)}"
        entry_hash = hashlib.sha256(payload_to_hash.encode("utf-8")).hexdigest()

        entry = AuditEntry(
            audit_id=audit_id,
            timestamp=timestamp,
            action=action,
            officer_badge=officer_badge,
            case_id=case_id,
            target_entity=target_entity,
            details=details,
            prev_hash=prev_hash,
            entry_hash=entry_hash
        )

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

        return entry

    def get_recent_entries(self, case_id: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """Retrieves recent audit entries filtered optionally by case."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return []

        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        e = json.loads(line.strip())
                        if case_id is None or e.get("case_id") == case_id:
                            entries.append(e)
                    except Exception:
                        continue

        return entries[-limit:][::-1]  # Most recent first


# Global default instance
default_audit_ledger = ImmutableAuditLedger()
