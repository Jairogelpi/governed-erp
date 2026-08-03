"""Skill compiler service (master spec section 18 / Phase 14).

Only `draft -> compiled -> approved` is implemented. `shadow`/`canary`/
`active`/`rolled_back`/`deprecated` (spec 18.4) require a live execution/
deployment runtime that doesn't exist in this codebase yet -- that's
Phase 15+ territory, not faked here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.application.connectors.service import ConnectorApplicationService
from erpguard.db.model_packages.candidate import ProcessCandidate
from erpguard.db.model_packages.proof import ProcessProof
from erpguard.db.model_packages.replay import ProcessReplay
from erpguard.db.model_packages.skill_package import SkillPackage
from erpguard.domain.processes.models import ProcessDefinitionDocument
from erpguard.domain.skills.compiler import SkillCompilationError, compile_skill_package
from erpguard.domain.skills.types import WorkflowStep


class CandidateNotCompilable(ValueError):
    pass


class NoAcceptableProof(ValueError):
    pass


class SkillPackageNotFound(KeyError):
    pass


class SkillPackageValidationError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _find_acceptable_proof(session: Session, *, tenant_id: str, process_key: str, candidate_version: str) -> ProcessProof:
    proofs = (
        session.query(ProcessProof)
        .join(ProcessReplay, ProcessReplay.id == ProcessProof.candidate_replay_id)
        .filter(
            ProcessProof.tenant_id == tenant_id,
            ProcessReplay.process_key == process_key,
            ProcessReplay.version == candidate_version,
            ProcessProof.recommendation.notin_(("reject", "needs_changes")),
        )
        .order_by(ProcessProof.generated_at.desc())
        .all()
    )
    if not proofs:
        raise NoAcceptableProof(f"no_acceptable_proof_for:{process_key}:{candidate_version}")
    return proofs[0]


class SkillCompilerService:
    def __init__(self, session: Session):
        self.session = session

    def compile(
        self,
        *,
        tenant_id: str,
        candidate_id: str,
        connector_id: str,
        workflow_steps: list[dict],
    ) -> SkillPackage:
        candidate = (
            self.session.query(ProcessCandidate)
            .filter_by(tenant_id=tenant_id, id=candidate_id)
            .one_or_none()
        )
        if candidate is None:
            raise CandidateNotCompilable("candidate_not_found")
        if candidate.status != "submitted":
            raise CandidateNotCompilable("candidate_not_submitted")

        proof = _find_acceptable_proof(
            self.session,
            tenant_id=tenant_id,
            process_key=candidate.process_key,
            candidate_version=candidate.candidate_version,
        )

        connector = ConnectorApplicationService(self.session).registry.get(connector_id)
        candidate_definition = ProcessDefinitionDocument.model_validate(
            json.loads(candidate.candidate_definition_json)
        )
        steps = [WorkflowStep.model_validate(item) for item in workflow_steps]

        from erpguard.db.model_packages.declared_capabilities import DeclaredWriteCapability

        active_declared_capability_names = frozenset(
            row.id
            for row in self.session.query(DeclaredWriteCapability.id)
            .filter_by(tenant_id=tenant_id, status="active")
            .all()
        )
        # capability names for declared capabilities are `declared.<id>` --
        # the workflow step names them that way, so intersect on that shape.
        active_declared_capability_names = frozenset(
            step.capability
            for step in steps
            if step.capability.startswith("declared.")
            and step.capability.removeprefix("declared.") in active_declared_capability_names
        )

        try:
            content, validation_result, package_hash = compile_skill_package(
                process_key=candidate.process_key,
                candidate_version=candidate.candidate_version,
                candidate_definition=candidate_definition,
                workflow_steps=steps,
                connector=connector,
                proof_id=proof.id,
                proof_recommendation=proof.recommendation,
                active_declared_capability_names=active_declared_capability_names,
            )
        except SkillCompilationError as exc:
            raise SkillPackageValidationError(str(exc)) from exc

        row = SkillPackage(
            id=f"skillpkg_{uuid4().hex}",
            tenant_id=tenant_id,
            candidate_id=candidate.id,
            proof_id=proof.id,
            process_key=candidate.process_key,
            candidate_version=candidate.candidate_version,
            connector_id=connector_id,
            status="compiled",
            package_json=json.dumps(content.model_dump(mode="json"), sort_keys=True, separators=(",", ":")),
            validation_result_json=json.dumps(
                validation_result.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ),
            package_hash=package_hash,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get_skill_package(self, *, tenant_id: str, skill_id: str, version: str) -> SkillPackage:
        row = (
            self.session.query(SkillPackage)
            .filter_by(tenant_id=tenant_id, id=skill_id, candidate_version=version)
            .one_or_none()
        )
        if row is None:
            raise SkillPackageNotFound(skill_id)
        return row

    def get_by_id(self, *, tenant_id: str, skill_id: str) -> SkillPackage:
        row = self.session.query(SkillPackage).filter_by(tenant_id=tenant_id, id=skill_id).one_or_none()
        if row is None:
            raise SkillPackageNotFound(skill_id)
        return row

    def approve(self, *, tenant_id: str, skill_id: str) -> SkillPackage:
        row = self.get_by_id(tenant_id=tenant_id, skill_id=skill_id)
        if row.status == "approved":
            raise SkillPackageValidationError("skill_package_already_approved")
        if row.status != "compiled":
            raise SkillPackageValidationError("skill_package_not_compiled")
        row.status = "approved"
        row.approved_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row
