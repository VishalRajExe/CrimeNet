"""CrimeNet Local Demo 22-Step Verification Test.

Validates that the entire end-to-end local demo workflow executes cleanly
in the exact specified 22-step sequence:
1. CREATE CASE
2. UPLOAD FIR / CDR / TRANSACTION / OTHER EVIDENCE
3. EXTRACT ENTITIES
4. NORMALIZE / RESOLVE ENTITIES
5. BUILD / UPDATE NEO4J GRAPH
6. OPEN INVESTIGATION WORKSPACE
7. SEARCH ENTITY OR ASK CRIMENET
8. RUN GRAPH ANALYSIS
9. COMMUNITY DETECTION
10. SOCIAL INFLUENCE
11. PATH / N-HOP
12. LINK PREDICTION
13. ANOMALY DETECTION
14. ENTITY DOSSIER
15. RELATIONSHIP EVIDENCE
16. GRAPHRAG EVIDENCE SEARCH
17. FOLLOW-THE-MONEY
18. TIMELINE
19. HUMAN FEEDBACK
20. AUDIT TRAIL
21. INTELLIGENCE REPORT
22. PDF
"""

import os
import sys
import uuid
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
ai_service_dir = ROOT_DIR / "repo" / "ai-service"
if str(ai_service_dir) not in sys.path:
    sys.path.insert(0, str(ai_service_dir))

from scripts.run_local_demo import run_demo


def test_22_step_local_demo_sequence():
    """Verify that all 22 steps of the local demo execute and succeed end-to-end."""
    success = run_demo()
    assert success is True, "Expected all 22 steps to complete with True return status"


def test_demo_generated_pdf_exists():
    """Verify that court-admissible PDF reports exist in generated_reports."""
    reports_dir = ROOT_DIR / "generated_reports"
    assert reports_dir.exists(), "generated_reports directory must exist"
    case_pdfs = sorted(reports_dir.glob("case-*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    assert len(case_pdfs) > 0, "At least one generated case PDF must exist from the demo execution"
    latest_pdf = case_pdfs[0]
    assert latest_pdf.stat().st_size > 5000, f"Latest PDF ({latest_pdf.name}) file size must indicate non-empty document"
