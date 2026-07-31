"""Bounded persistence model packages introduced during the migration."""

from erpguard.db.model_packages.process import ProcessDefinition
from erpguard.db.model_packages.decision_intelligence import (
    AnalyticalSnapshot,
    DataQualityReport,
    MarginAnalysis,
)
from erpguard.db.model_packages.shadow import (
    ShadowCaseResult,
    ShadowCaseReview,
    ShadowDeployment,
    ShadowFeedRun,
    ShadowOutcomeObservation,
)

__all__ = [
    "ProcessDefinition",
    "AnalyticalSnapshot",
    "DataQualityReport",
    "MarginAnalysis",
    "ShadowCaseResult",
    "ShadowCaseReview",
    "ShadowDeployment",
    "ShadowFeedRun",
    "ShadowOutcomeObservation",
]
