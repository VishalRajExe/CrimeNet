"""CrimeNet Database Layer - Case Repository & Connection Management.

Provides unified database operations across MySQL and SQLite without duplication.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from storage.case_data_service import CaseDataService


class CaseRepository(CaseDataService):
    """Authoritative Case Data Repository for CrimeNet."""
    pass


# Global singleton instance
default_case_repository = CaseRepository()
