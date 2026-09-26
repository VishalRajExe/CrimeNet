"""CrimeNet Reports Package.

Generates court-admissible forensic briefs, dossiers, and audit reports.
"""

from reports.report_generator import (
    InvestigationReportCompiler,
    ReportFormat,
)

# Clean aliases
CrimeNetReportGenerator = InvestigationReportCompiler


def generate_case_report(case_id: str, report_format: str = "INVESTIGATION_BRIEF", **kwargs):
    """Convenience helper to generate a grounded case intelligence report."""
    compiler = InvestigationReportCompiler()
    return compiler.generate_pdf_report(case_id=case_id, report_format=report_format, **kwargs)


__all__ = [
    "InvestigationReportCompiler",
    "CrimeNetReportGenerator",
    "ReportFormat",
    "generate_case_report",
]
