from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import CanonicalAction, PreflightDecision, RiskLevel
from erpguard.core.preflight import run_preflight


ACTOR = {"type": "user", "id": "actor_1", "display_name": "Jairo"}


def test_valid_fake_order_returns_allow_preflight_result():
    result = run_preflight(
        adapter=FakeERPAdapter(),
        actor=ACTOR,
        canonical_action=CanonicalAction.VALIDATE_FORMULA,
        target_id="so_valid",
    )

    assert result.decision is PreflightDecision.ALLOW
    assert result.risk_level is RiskLevel.R0
    assert result.actor == ACTOR
    assert result.canonical_action is CanonicalAction.VALIDATE_FORMULA
    assert result.target_id == "so_valid"
    assert result.policy_id == "formula_guard"
    assert result.policy_version == "0.1.0"
    assert result.issues == []
    assert result.evidence["target"]["reference"] == "SO-VALID"


def test_invalid_fake_order_returns_block_preflight_result():
    result = run_preflight(
        adapter=FakeERPAdapter(),
        actor=ACTOR,
        canonical_action=CanonicalAction.CONFIRM_SALES_ORDER,
        target_id="so_formula_mismatch",
    )

    assert result.decision is PreflightDecision.BLOCK
    assert result.risk_level is RiskLevel.R3
    assert result.issues[0].code == "formula_ml_per_unit_mismatch"
    assert result.issues[0].line_id == "line_formula_mismatch"


def test_empty_line_fake_order_returns_block_preflight_result():
    result = run_preflight(
        adapter=FakeERPAdapter(),
        actor=ACTOR,
        canonical_action=CanonicalAction.CONFIRM_SALES_ORDER,
        target_id="so_empty_lines",
    )

    assert result.decision is PreflightDecision.BLOCK
    assert result.issues[0].code == "sales_order_has_no_lines"


def test_missing_order_fails_closed_without_raw_exception_leak():
    result = run_preflight(
        adapter=FakeERPAdapter(),
        actor=ACTOR,
        canonical_action=CanonicalAction.CONFIRM_SALES_ORDER,
        target_id="missing",
    )

    assert result.decision is PreflightDecision.BLOCK
    assert result.risk_level is RiskLevel.R3
    assert result.policy_id == "formula_guard"
    assert result.issues[0].code == "preflight_target_load_failed"
    assert "missing" in result.summary


def test_preflight_result_contains_action_target_and_policy_metadata():
    result = run_preflight(
        adapter=FakeERPAdapter(),
        actor=ACTOR,
        canonical_action=CanonicalAction.CONFIRM_SALES_ORDER,
        target_id="so_capacity_no_formula",
    )

    assert result.actor["id"] == "actor_1"
    assert result.canonical_action is CanonicalAction.CONFIRM_SALES_ORDER
    assert result.target_id == "so_capacity_no_formula"
    assert result.policy_id == "formula_guard"
    assert result.policy_version == "0.1.0"
    assert result.evidence["adapter"]["erp_type"] == "fake"
    assert result.evidence["policy"]["policy_id"] == "formula_guard"
