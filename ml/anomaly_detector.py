"""CrimeNet Machine Learning Anomaly Detection."""

from __future__ import annotations

from backend.intelligence.anomaly_detector import (
    IsolationForestAnomalyDetector,
    default_anomaly_detector,
)

# Alias for clean architecture
AnomalyDetector = IsolationForestAnomalyDetector

__all__ = [
    "AnomalyDetector",
    "IsolationForestAnomalyDetector",
    "default_anomaly_detector",
]
