"""CrimeNet AI Investigation Agent Module."""

from __future__ import annotations

from analyzer.investigation_agent import (
    run_investigation,
    build_agent,
    find_shortest_path,
    extract_supporting_sources,
)

# Clean alias
InvestigationAgent = build_agent

__all__ = [
    "InvestigationAgent",
    "run_investigation",
    "build_agent",
    "find_shortest_path",
    "extract_supporting_sources",
]
