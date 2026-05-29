"""Sprint 56 — ERP Fingerprinting Plan.

Creates a plan-only artifact from a setup session + credential reference.
Does NOT call the ERP URL, perform login, inspect schemas, generate
capabilities, activate connectors, or expose credentials.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_erp_fingerprinting_audit_event,
    create_erp_fingerprinting_plan,
    get_connector_setup_session,
    get_credential_vault_entry_by_ref,
    get_erp_fingerprinting_plan_by_id,
    list_erp_fingerprinting_plans,
)


class AdapterType(str, Enum):
    ODOO = "odoo"
    HOLDED = "holded"
    SAP = "sap"
    DYNAMICS = "dynamics"
    NETSUITE = "netsuite"
    CUSTOM_REST = "custom_rest"
    UNKNOWN = "unknown"


class CheckMethod(str, Enum):
    PLAN_ONLY = "plan_only"


class CheckType(str, Enum):
    HOST_PATTERN = "host_pattern"
    LOGIN_PAGE_MARKER = "login_page_marker"
    METADATA_ENDPOINT_CANDIDATE = "metadata_endpoint_candidate"
    ROBOTS_SAFE_PROBE_FUTURE = "robots_safe_probe_future"
    FAVICON_MARKER_FUTURE = "favicon_marker_future"


class MatchedFrom(str, Enum):
    HOST_PATTERN = "host_pattern"
    URL_PATTERN = "url_pattern"
    CONNECTOR_NAME = "connector_name"
    MANUAL_HINT = "manual_hint"
    UNKNOWN = "unknown"


@dataclass
class FingerprintingCandidate:
    adapter_type: str
    reason: str
    confidence: float
    matched_from: str


@dataclass
class PlannedCheck:
    check_type: str
    method: str
    would_require_network: bool
    would_use_credentials: bool
    risk_level: str
    status: str


@dataclass
class RiskSummary:
    overall_risk: str
    highest_risk_check: str
    needs_network: bool
    uses_credentials: bool
    plan_only: bool


@dataclass
class FingerprintingPlanInput:
    setup_session_id: str
    credential_ref: str
    created_by: str = "operator_1"
    manual_hint: str | None = None


@dataclass
class FingerprintingPlanResult:
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    connector_name: str
    erp_url_host: str
    environment_type: str
    status: str
    adapter_candidates: list[dict[str, Any]]
    planned_checks: list[dict[str, Any]]
    risk_summary: dict[str, Any]
    next_safe_step: str | None
    confidence: float
    blocking_reasons: list[str]
    will_connect: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    fingerprint_performed: bool = False
    schema_inspection_performed: bool = False
    capability_generation_performed: bool = False
    read_only_activation_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


# --- Heuristics ---

_ADAPTER_RULES: list[tuple[str, str, float]] = [
    # (substring, adapter_type, confidence_if_matched)
    ("odoo", AdapterType.ODOO, 0.8),
    ("holded", AdapterType.HOLDED, 0.8),
    ("sap", AdapterType.SAP, 0.8),
    ("dynamics", AdapterType.DYNAMICS, 0.8),
    ("netsuite", AdapterType.NETSUITE, 0.8),
]

_MANUAL_HINT_MAP: dict[str, tuple[str, float]] = {
    "odoo": (AdapterType.ODOO, 0.75),
    "holded": (AdapterType.HOLDED, 0.75),
    "sap": (AdapterType.SAP, 0.75),
    "dynamics": (AdapterType.DYNAMICS, 0.75),
    "netsuite": (AdapterType.NETSUITE, 0.75),
    "custom_rest": (AdapterType.CUSTOM_REST, 0.7),
}


def _detect_candidates(
    erp_url_host: str,
    connector_name: str,
    manual_hint: str | None = None,
) -> list[FingerprintingCandidate]:
    """Static heuristic candidate detection — no network calls."""
    candidates: list[FingerprintingCandidate] = []
    seen: set[str] = set()
    search_text = f"{erp_url_host} {connector_name}".lower()

    for substring, adapter_type, confidence in _ADAPTER_RULES:
        if substring in search_text:
            matched_from = (
                MatchedFrom.HOST_PATTERN
                if substring in erp_url_host.lower()
                else MatchedFrom.CONNECTOR_NAME
            )
            candidates.append(
                FingerprintingCandidate(
                    adapter_type=adapter_type,
                    reason=f"Host/name contains '{substring}'",
                    confidence=confidence,
                    matched_from=matched_from,
                )
            )
            seen.add(adapter_type)

    if manual_hint:
        hint_lower = manual_hint.lower().strip()
        if hint_lower in _MANUAL_HINT_MAP:
            adapter_type, confidence = _MANUAL_HINT_MAP[hint_lower]
            if adapter_type not in seen:
                candidates.append(
                    FingerprintingCandidate(
                        adapter_type=adapter_type,
                        reason=f"Manual hint '{manual_hint}'",
                        confidence=confidence,
                        matched_from=MatchedFrom.MANUAL_HINT,
                    )
                )
                seen.add(adapter_type)

    if not candidates:
        candidates.append(
            FingerprintingCandidate(
                adapter_type=AdapterType.CUSTOM_REST,
                reason="No strong match; generic REST fallback",
                confidence=0.3,
                matched_from=MatchedFrom.UNKNOWN,
            )
        )
        candidates.append(
            FingerprintingCandidate(
                adapter_type=AdapterType.UNKNOWN,
                reason="No pattern matched",
                confidence=0.3,
                matched_from=MatchedFrom.UNKNOWN,
            )
        )

    return candidates


def _build_planned_checks(
    candidates: list[FingerprintingCandidate],
) -> list[PlannedCheck]:
    """All checks are plan_only — no network or credentials."""
    checks: list[PlannedCheck] = []
    for candidate in candidates:
        checks.append(
            PlannedCheck(
                check_type=CheckType.HOST_PATTERN,
                method=CheckMethod.PLAN_ONLY,
                would_require_network=True,
                would_use_credentials=False,
                risk_level="low",
                status="planned",
            )
        )
        checks.append(
            PlannedCheck(
                check_type=CheckType.LOGIN_PAGE_MARKER,
                method=CheckMethod.PLAN_ONLY,
                would_require_network=True,
                would_use_credentials=True,
                risk_level="medium",
                status="planned",
            )
        )
        checks.append(
            PlannedCheck(
                check_type=CheckType.METADATA_ENDPOINT_CANDIDATE,
                method=CheckMethod.PLAN_ONLY,
                would_require_network=True,
                would_use_credentials=False,
                risk_level="low",
                status="planned",
            )
        )
    checks.append(
        PlannedCheck(
            check_type=CheckType.ROBOTS_SAFE_PROBE_FUTURE,
            method=CheckMethod.PLAN_ONLY,
            would_require_network=True,
            would_use_credentials=False,
            risk_level="low",
            status="planned",
        )
    )
    checks.append(
        PlannedCheck(
            check_type=CheckType.FAVICON_MARKER_FUTURE,
            method=CheckMethod.PLAN_ONLY,
            would_require_network=True,
            would_use_credentials=False,
            risk_level="low",
            status="planned",
        )
    )
    return checks


def _build_risk_summary(
    candidates: list[FingerprintingCandidate],
    checks: list[PlannedCheck],
) -> RiskSummary:
    has_medium = any(c.risk_level == "medium" for c in checks)
    risk_level = "medium" if has_medium else "low"
    highest = "medium" if has_medium else "low"
    return RiskSummary(
        overall_risk=risk_level,
        highest_risk_check=highest,
        needs_network=True,
        uses_credentials=True,
        plan_only=True,
    )


class ERPFingerprintingPlanService:
    """Creates a plan-only fingerprinting artifact.
    No network calls, no login, no schema inspection, no capability generation.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_plan(
        self, plan_input: FingerprintingPlanInput
    ) -> FingerprintingPlanResult:
        setup_session = get_connector_setup_session(
            self.session, plan_input.setup_session_id
        )

        if setup_session is None:
            return FingerprintingPlanResult(
                fingerprint_plan_id="",
                setup_session_id=plan_input.setup_session_id,
                credential_ref=plan_input.credential_ref,
                connector_name="",
                erp_url_host="",
                environment_type="",
                status="blocked",
                adapter_candidates=[],
                planned_checks=[],
                risk_summary={},
                next_safe_step=None,
                confidence=0.0,
                blocking_reasons=["setup_session_not_found"],
            )

        if setup_session.status == "blocked":
            return FingerprintingPlanResult(
                fingerprint_plan_id="",
                setup_session_id=plan_input.setup_session_id,
                credential_ref=plan_input.credential_ref,
                connector_name=setup_session.connector_name,
                erp_url_host=setup_session.erp_url_host,
                environment_type=setup_session.environment_type,
                status="blocked",
                adapter_candidates=[],
                planned_checks=[],
                risk_summary={},
                next_safe_step=None,
                confidence=0.0,
                blocking_reasons=["setup_session_blocked"],
            )

        if not plan_input.credential_ref:
            return FingerprintingPlanResult(
                fingerprint_plan_id="",
                setup_session_id=plan_input.setup_session_id,
                credential_ref="",
                connector_name=setup_session.connector_name,
                erp_url_host=setup_session.erp_url_host,
                environment_type=setup_session.environment_type,
                status="blocked",
                adapter_candidates=[],
                planned_checks=[],
                risk_summary={},
                next_safe_step=None,
                confidence=0.0,
                blocking_reasons=["credential_ref_required"],
            )

        if setup_session.credential_ref != plan_input.credential_ref:
            return FingerprintingPlanResult(
                fingerprint_plan_id="",
                setup_session_id=plan_input.setup_session_id,
                credential_ref=plan_input.credential_ref,
                connector_name=setup_session.connector_name,
                erp_url_host=setup_session.erp_url_host,
                environment_type=setup_session.environment_type,
                status="blocked",
                adapter_candidates=[],
                planned_checks=[],
                risk_summary={},
                next_safe_step=None,
                confidence=0.0,
                blocking_reasons=["credential_ref_mismatch"],
            )

        cred_entry = get_credential_vault_entry_by_ref(
            self.session, plan_input.credential_ref
        )
        if cred_entry is None:
            return FingerprintingPlanResult(
                fingerprint_plan_id="",
                setup_session_id=plan_input.setup_session_id,
                credential_ref=plan_input.credential_ref,
                connector_name=setup_session.connector_name,
                erp_url_host=setup_session.erp_url_host,
                environment_type=setup_session.environment_type,
                status="blocked",
                adapter_candidates=[],
                planned_checks=[],
                risk_summary={},
                next_safe_step=None,
                confidence=0.0,
                blocking_reasons=["credential_not_found"],
            )

        if cred_entry.status == "revoked":
            return FingerprintingPlanResult(
                fingerprint_plan_id="",
                setup_session_id=plan_input.setup_session_id,
                credential_ref=plan_input.credential_ref,
                connector_name=setup_session.connector_name,
                erp_url_host=setup_session.erp_url_host,
                environment_type=setup_session.environment_type,
                status="blocked",
                adapter_candidates=[],
                planned_checks=[],
                risk_summary={},
                next_safe_step=None,
                confidence=0.0,
                blocking_reasons=["credential_revoked"],
            )

        # --- Build plan (static heuristics only) ---
        candidates = _detect_candidates(
            setup_session.erp_url_host,
            setup_session.connector_name,
            plan_input.manual_hint,
        )
        checks = _build_planned_checks(candidates)
        risk_summary = _build_risk_summary(candidates, checks)

        best_confidence = max(c.confidence for c in candidates) if candidates else 0.0

        plan_id = f"fplan_{uuid.uuid4().hex[:12]}"

        candidates_json = json.dumps([vars(c) for c in candidates])
        checks_json = json.dumps([vars(c) for c in checks])
        risk_json = json.dumps(vars(risk_summary))

        plan_row = create_erp_fingerprinting_plan(
            self.session,
            fingerprint_plan_id=plan_id,
            setup_session_id=plan_input.setup_session_id,
            credential_ref=plan_input.credential_ref,
            connector_name=setup_session.connector_name,
            erp_url_host=setup_session.erp_url_host,
            environment_type=setup_session.environment_type,
            status="planned",
            adapter_candidates_json=candidates_json,
            planned_checks_json=checks_json,
            risk_summary_json=risk_json,
            next_safe_step="safe_discovery_plan",
            confidence=best_confidence,
            created_by=plan_input.created_by,
            blocking_reasons_json="[]",
        )

        create_erp_fingerprinting_audit_event(
            self.session,
            fingerprint_plan_id=plan_id,
            setup_session_id=plan_input.setup_session_id,
            credential_ref=plan_input.credential_ref,
            event_type="fingerprinting_plan_created",
            status="planned",
            details_json=json.dumps(
                {
                    "connector_name": setup_session.connector_name,
                    "erp_url_host": setup_session.erp_url_host,
                    "adapter_candidates": [vars(c) for c in candidates],
                    "confidence": best_confidence,
                }
            ),
        )

        return FingerprintingPlanResult(
            fingerprint_plan_id=plan_row.fingerprint_plan_id,
            setup_session_id=plan_row.setup_session_id,
            credential_ref=plan_row.credential_ref,
            connector_name=plan_row.connector_name,
            erp_url_host=plan_row.erp_url_host,
            environment_type=plan_row.environment_type,
            status="planned",
            adapter_candidates=[vars(c) for c in candidates],
            planned_checks=[vars(c) for c in checks],
            risk_summary=vars(risk_summary),
            next_safe_step="safe_discovery_plan",
            confidence=best_confidence,
            blocking_reasons=[],
            will_connect=False,
            external_http_performed=False,
            login_attempted=False,
            fingerprint_performed=False,
            schema_inspection_performed=False,
            capability_generation_performed=False,
            read_only_activation_performed=False,
            credentials_exposed=False,
            raw_secret_accessed=False,
        )

    def get_plan(self, fingerprint_plan_id: str) -> dict[str, Any] | None:
        plan = get_erp_fingerprinting_plan_by_id(self.session, fingerprint_plan_id)
        if plan is None:
            return None
        return {
            "fingerprint_plan_id": plan.fingerprint_plan_id,
            "setup_session_id": plan.setup_session_id,
            "credential_ref": plan.credential_ref,
            "connector_name": plan.connector_name,
            "erp_url_host": plan.erp_url_host,
            "environment_type": plan.environment_type,
            "status": plan.status,
            "adapter_candidates": json.loads(plan.adapter_candidates_json),
            "planned_checks": json.loads(plan.planned_checks_json),
            "risk_summary": json.loads(plan.risk_summary_json),
            "next_safe_step": plan.next_safe_step,
            "confidence": plan.confidence,
            "blocking_reasons": json.loads(plan.blocking_reasons_json),
            "will_connect": False,
            "external_http_performed": False,
            "login_attempted": False,
            "fingerprint_performed": False,
            "schema_inspection_performed": False,
            "capability_generation_performed": False,
            "read_only_activation_performed": False,
            "credentials_exposed": False,
            "raw_secret_accessed": False,
        }

    def list_plans(self, limit: int = 50) -> list[dict[str, Any]]:
        plans = list_erp_fingerprinting_plans(self.session, limit=limit)
        result = []
        for plan in plans:
            result.append(
                {
                    "fingerprint_plan_id": plan.fingerprint_plan_id,
                    "setup_session_id": plan.setup_session_id,
                    "credential_ref": plan.credential_ref,
                    "connector_name": plan.connector_name,
                    "erp_url_host": plan.erp_url_host,
                    "status": plan.status,
                    "confidence": plan.confidence,
                }
            )
        return result
