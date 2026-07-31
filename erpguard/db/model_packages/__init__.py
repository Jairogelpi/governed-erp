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
from erpguard.db.model_packages.skill_deployment import SkillDeploymentEvent
from erpguard.db.model_packages.opportunity import MarginOpportunity
from erpguard.db.model_packages.recommendations import GovernedActionDraft, GovernedRecommendation

__all__ = [
    "GovernedActionDraft",
    "GovernedRecommendation",
    "ProcessDefinition",
    "AnalyticalSnapshot",
    "DataQualityReport",
    "MarginAnalysis",
    "ShadowCaseResult",
    "ShadowCaseReview",
    "ShadowDeployment",
    "ShadowFeedRun",
    "ShadowOutcomeObservation",
    "SkillDeploymentEvent",
]
