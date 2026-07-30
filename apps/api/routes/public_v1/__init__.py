"""The Phase 11.5 public API route composition.

Modules in this package are the only routers mounted by the default app.
Several entries are temporary compatibility shims; each names the legacy
replacement wave in its module docstring.
"""

from . import approvals, candidates, connections, connectors, executions, evidence
from . import events, health, identity, processes, proofs, replays, skill_packages, skills, variants
from . import shadow


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
    approvals.router,
    executions.router,
    evidence.router,
    shadow.router,
)

__all__ = ["PUBLIC_ROUTERS"]
