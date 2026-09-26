"""CrimeNet GraphRAG Package.

Bridges CrimeNet forensic investigations and Microsoft GraphRAG.
Extends __path__ so that Microsoft GraphRAG subpackages (graphrag.config,
graphrag.query, etc.) are discovered alongside CrimeNet boundary abstractions.
"""
from __future__ import annotations

import sys
from pathlib import Path

# 1. Register Microsoft GraphRAG packages if available
_CURRENT_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _CURRENT_DIR.parent
_GRAPHRAG_ROOT = _WORKSPACE_ROOT / "graphrag-main" / "packages"
if not _GRAPHRAG_ROOT.exists():
    _ALT_ROOT = Path(r"C:\Users\visha\Downloads\CrimeNet-AI-main\graphrag-main\packages")
    if _ALT_ROOT.exists():
        _GRAPHRAG_ROOT = _ALT_ROOT

if _GRAPHRAG_ROOT.exists():
    for _pkg in [
        "graphrag",
        "graphrag-common",
        "graphrag-chunking",
        "graphrag-storage",
        "graphrag-cache",
        "graphrag-vectors",
        "graphrag-input",
        "graphrag-llm",
    ]:
        _p = str(_GRAPHRAG_ROOT / _pkg)
        if _p not in sys.path:
            sys.path.insert(0, _p)

    # Extend __path__ to allow submodules of graphrag (config, query, etc.) to be found
    _subpkg = _GRAPHRAG_ROOT / "graphrag" / "graphrag"
    if _subpkg.exists() and str(_subpkg) not in __path__:
        __path__.append(str(_subpkg))

from graphrag.boundary import (
    GraphRAGCrimeNetBoundary,
    RelationshipModality,
    AcceptanceStatus,
)

__all__ = [
    "GraphRAGCrimeNetBoundary",
    "RelationshipModality",
    "AcceptanceStatus",
]
