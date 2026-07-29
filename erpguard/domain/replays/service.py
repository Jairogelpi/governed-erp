"""Historical replay service (master spec section 15 / Phase 12)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.events import CanonicalObject
from erpguard.db.model_packages.replay import ProcessReplay, ProcessReplayCase
from erpguard.domain.processes.models import ProcessDefinitionDocument
from erpguard.domain.processes.registry import ProcessRegistry
from erpguard.domain.replays.engine import CONNECTOR_SIMULATOR_VERSION, ReplayEngine
from erpguard.domain.replays.types import ReplayCaseResult
from erpguard.domain.variants.discovery import VariantDiscoveryService
from erpguard.policies.engine import FORMULA_GUARD_POLICY_VERSION


class ReplayValidationError(ValueError):
    pass


class ProcessDefinitionNotFound(KeyError):
    pass


class ReplayNotFound(KeyError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class ReplayService:
    def __init__(self, session: Session):
        self.session = session
        self.engine = ReplayEngine()

    def create_replay(
        self,
        *,
        tenant_id: str,
        process_key: str,
        version: str,
        object_type: str,
    ) -> ProcessReplay:
        definition_row = ProcessRegistry(self.session).get(process_key, version)
        if definition_row is None:
            raise ProcessDefinitionNotFound("process_definition_not_found")
        definition = ProcessDefinitionDocument.model_validate(json.loads(definition_row.definition_json))

        variants = VariantDiscoveryService(self.session)
        case_ids = sorted(
            {
                case_id
                for summary in variants.discover(tenant_id=tenant_id, object_type=object_type)
                for case_id in summary.case_ids
            }
        )

        results: list[ReplayCaseResult] = []
        for case_id in case_ids:
            case_trace = variants.case_trace(tenant_id=tenant_id, case_id=case_id, object_type=object_type)
            object_row = (
                self.session.query(CanonicalObject)
                .filter_by(tenant_id=tenant_id, object_key=case_id)
                .one_or_none()
            )
            object_attributes = json.loads(object_row.attributes_json) if object_row else {}
            results.append(
                self.engine.run_case(
                    process_key=process_key,
                    version=version,
                    object_type=object_type,
                    case_trace=case_trace,
                    definition=definition,
                    object_attributes=object_attributes,
                )
            )

        replay = ProcessReplay(
            id=f"replay_{uuid4().hex}",
            tenant_id=tenant_id,
            process_key=process_key,
            version=version,
            object_type=object_type,
            status="completed",
            policy_version=FORMULA_GUARD_POLICY_VERSION,
            connector_simulator_version=CONNECTOR_SIMULATOR_VERSION,
            case_count=len(results),
            completed_at=_utc_now(),
        )
        self.session.add(replay)
        self.session.flush()

        for result in results:
            self.session.add(
                ProcessReplayCase(
                    id=f"replaycase_{uuid4().hex}",
                    tenant_id=tenant_id,
                    replay_id=replay.id,
                    case_id=result.case_id,
                    status=result.status,
                    decision_trace_json=_dump([item.model_dump(mode="json") for item in result.decision_trace]),
                    predicted_effects_json=_dump([item.model_dump(mode="json") for item in result.predicted_effects]),
                    safety_violations_json=_dump([item.model_dump(mode="json") for item in result.safety_violations]),
                    regressions_json=_dump([item.model_dump(mode="json") for item in result.regressions]),
                    metrics_json=_dump(result.metrics),
                    deterministic_trace_hash=result.deterministic_trace_hash,
                    declared_decision_count=result.declared_decision_count,
                    evaluated_decision_count=result.evaluated_decision_count,
                    unsupported_decisions_json=_dump(result.unsupported_decisions),
                    decision_coverage_rate=result.decision_coverage_rate,
                )
            )
        self.session.commit()
        self.session.refresh(replay)
        return replay

    def get_replay(self, *, tenant_id: str, replay_id: str) -> ProcessReplay:
        row = (
            self.session.query(ProcessReplay)
            .filter_by(tenant_id=tenant_id, id=replay_id)
            .one_or_none()
        )
        if row is None:
            raise ReplayNotFound(replay_id)
        return row

    def list_cases(self, *, tenant_id: str, replay_id: str) -> list[ProcessReplayCase]:
        self.get_replay(tenant_id=tenant_id, replay_id=replay_id)
        return (
            self.session.query(ProcessReplayCase)
            .filter_by(tenant_id=tenant_id, replay_id=replay_id)
            .order_by(ProcessReplayCase.case_id.asc())
            .all()
        )

    def freeze(self, *, tenant_id: str, replay_id: str) -> ProcessReplay:
        row = self.get_replay(tenant_id=tenant_id, replay_id=replay_id)
        if row.status == "frozen":
            raise ReplayValidationError("replay_already_frozen")
        if row.status != "completed":
            raise ReplayValidationError("replay_not_completed")
        row.status = "frozen"
        row.frozen_at = _utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row

    def compare(
        self,
        *,
        tenant_id: str,
        baseline_replay_id: str,
        candidate_replay_id: str,
    ) -> dict:
        """Minimal hash/status diff between two replay runs' matching case_ids.

        This does not compute a regression taxonomy (master spec section 16)
        -- that is Phase 13's job. It only reports, per matching case_id,
        whether the deterministic trace hash and status are identical.
        """

        baseline = self.get_replay(tenant_id=tenant_id, replay_id=baseline_replay_id)
        candidate = self.get_replay(tenant_id=tenant_id, replay_id=candidate_replay_id)
        baseline_cases = {
            row.case_id: row for row in self.list_cases(tenant_id=tenant_id, replay_id=baseline.id)
        }
        candidate_cases = {
            row.case_id: row for row in self.list_cases(tenant_id=tenant_id, replay_id=candidate.id)
        }

        case_ids = sorted(set(baseline_cases) & set(candidate_cases))
        only_in_baseline = sorted(set(baseline_cases) - set(candidate_cases))
        only_in_candidate = sorted(set(candidate_cases) - set(baseline_cases))

        cases = []
        matched_count = 0
        for case_id in case_ids:
            b = baseline_cases[case_id]
            c = candidate_cases[case_id]
            hash_matches = b.deterministic_trace_hash == c.deterministic_trace_hash
            status_changed = b.status != c.status
            if hash_matches:
                matched_count += 1
            cases.append(
                {
                    "case_id": case_id,
                    "baseline_status": b.status,
                    "candidate_status": c.status,
                    "status_changed": status_changed,
                    "hash_matches": hash_matches,
                }
            )

        return {
            "baseline_replay_id": baseline.id,
            "candidate_replay_id": candidate.id,
            "matched_case_count": matched_count,
            "compared_case_count": len(case_ids),
            "only_in_baseline_case_ids": only_in_baseline,
            "only_in_candidate_case_ids": only_in_candidate,
            "cases": cases,
        }
