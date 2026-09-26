"""CrimeNet AI Package."""

from ai.agent import (
    InvestigationAgent,
    run_investigation,
    build_agent,
    find_shortest_path,
    extract_supporting_sources,
)

get_agent = build_agent

__all__ = [
    "InvestigationAgent",
    "run_investigation",
    "build_agent",
    "get_agent",
    "find_shortest_path",
    "extract_supporting_sources",
]
