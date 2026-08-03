"""The Phase 11.5 public API route composition.

Modules in this package are the only routers mounted by the default app.
Several entries are temporary compatibility shims; each names the legacy
replacement wave in its module docstring.
"""

from . import approvals, candidates, connections, connectors, executions, evidence
from . import events, health, identity, processes, proofs, replays, skill_packages, skills, variants
from . import shadow
from . import decision_intelligence
from . import opportunity
from . import recommendations
from . import canary
from . import outcomes
from . import decision_outcome_evidence
from . import benchmark
from . import declared_capabilities


PUBLIC_ROUTERS = (
    health.router,
    identity.router,
    connections.router,
    connectors.router,
    events.router,
    processes.router,
    variants.router,
    candidates.router,
    replays.router,
    replays.processes_router,
    proofs.router,
    skills.router,
    skill_packages.router,
    skill_packages.candidates_router,
    skill_packages.processes_router,
    approvals.router,
    executions.router,
    evidence.router,
    shadow.router,
    decision_intelligence.router,
    opportunity.router,
    recommendations.opportunities_router,
    recommendations.router,
    recommendations.action_drafts_router,
    canary.router,
    outcomes.measurement_plans_router,
    outcomes.recommendation_plans_router,
    outcomes.outcome_reports_router,
    decision_outcome_evidence.recommendation_evidence_router,
    decision_outcome_evidence.evidence_router,
    benchmark.router,
    declared_capabilities.router,
)

__all__ = ["PUBLIC_ROUTERS"]
