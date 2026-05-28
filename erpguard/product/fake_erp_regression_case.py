from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import uuid4

from erpguard.db.repositories import create_fake_erp_regression_case, get_fake_erp_regression_case
from erpguard.db.repositories import get_ui_skill_version_record


@dataclass(frozen=True)
class FakeERPRegressionCaseCreateRequest:
    version_id: str
    dry_run_id: str
    name: str
    execution_target: str = "fake_erp"
    inputs: dict = field(default_factory=dict)
    expected_outcomes: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FakeERPRegressionCaseResult:
    case_id: str
    version_id: str
    dry_run_id: str
    name: str
    execution_target: str
    inputs: dict
    expected_outcomes: dict
    created: bool
    blocking_reasons: list[str]


def create_manual_fake_erp_regression_case(req: FakeERPRegressionCaseCreateRequest, session) -> FakeERPRegressionCaseResult:
    version = get_ui_skill_version_record(session, req.version_id)
    if version is None:
        return FakeERPRegressionCaseResult(
            case_id="",
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            name=req.name,
            execution_target=req.execution_target,
            inputs=req.inputs,
            expected_outcomes=req.expected_outcomes,
            created=False,
            blocking_reasons=["version_not_found"],
        )
    if req.execution_target != "fake_erp":
        return FakeERPRegressionCaseResult(
            case_id="",
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            name=req.name,
            execution_target=req.execution_target,
            inputs=req.inputs,
            expected_outcomes=req.expected_outcomes,
            created=False,
            blocking_reasons=[f"execution_target_not_allowed:{req.execution_target}"],
        )
    row = create_fake_erp_regression_case(
        session,
        case_id=f"fregcase_{uuid4().hex[:16]}",
        version_id=req.version_id,
        dry_run_id=req.dry_run_id,
        name=req.name,
        execution_target="fake_erp",
        inputs_json=json.dumps(req.inputs),
        expected_outcomes_json=json.dumps(req.expected_outcomes),
    )
    return FakeERPRegressionCaseResult(
        case_id=row.id,
        version_id=row.version_id,
        dry_run_id=row.dry_run_id,
        name=row.name,
        execution_target=row.execution_target,
        inputs=json.loads(row.inputs_json or "{}"),
        expected_outcomes=json.loads(row.expected_outcomes_json or "{}"),
        created=True,
        blocking_reasons=[],
    )


def get_manual_fake_erp_regression_case(*, case_id: str, session) -> FakeERPRegressionCaseResult | None:
    row = get_fake_erp_regression_case(session, case_id)
    if row is None:
        return None
    return FakeERPRegressionCaseResult(
        case_id=row.id,
        version_id=row.version_id,
        dry_run_id=row.dry_run_id,
        name=row.name,
        execution_target=row.execution_target,
        inputs=json.loads(row.inputs_json or "{}"),
        expected_outcomes=json.loads(row.expected_outcomes_json or "{}"),
        created=True,
        blocking_reasons=[],
    )
