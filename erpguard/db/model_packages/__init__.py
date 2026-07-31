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
from erpguard.db.model_packages.canary import CanaryPolicy, CanaryRoutingDecision, CanarySafetyIncident
from erpguard.db.model_packages.outcomes import OutcomeMeasurementPlan, OutcomeObservation, RealizedOutcomeReport
from erpguard.db.model_packages.decision_outcome_evidence import DecisionOutcomeEvidenceBundle

__all__ = [
    "DecisionOutcomeEvidenceBundle",
    "GovernedActionDraft",
    "GovernedRecommendation",
    "CanaryPolicy",
    "CanaryRoutingDecision",
    "CanarySafetyIncident",
    "OutcomeMeasurementPlan",
    "OutcomeObservation",
    "RealizedOutcomeReport",
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
    "MarginOpportunity",
]
