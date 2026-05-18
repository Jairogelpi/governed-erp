from pathlib import Path

import pytest

from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import PreflightDecision, RiskLevel
from erpguard.core.errors import PolicyLoadError, PolicyValidationError
from erpguard.policies.engine import PolicyEngine
from erpguard.policies.loader import load_policy_file


def test_formula_guard_yaml_loads_successfully():
    policy = load_policy_file(Path("policies/odoo/formula_guard.yaml"))

    assert policy.policy == "formula_guard"
    assert policy.version == "0.1.0"
    assert policy.status == "active"
    assert policy.applies_to.canonical_object == "SalesOrder"
    assert policy.applies_to.canonical_action == "confirm_sales_order"
    assert policy.risk_level_on_fail is RiskLevel.R3
    assert policy.decision_on_fail is PreflightDecision.BLOCK
    assert [check.id for check in policy.checks] == [
        "formula_exists_for_capacity_products",
        "formula_ml_per_unit_matches_capacity",
        "formula_total_ml_matches_quantity",
    ]


def test_policy_schema_requires_required_fields():
    invalid_policy = Path("tests/fixtures/invalid_policy_missing_applies_to.yaml")

    with pytest.raises(PolicyValidationError) as exc_info:
        load_policy_file(invalid_policy)

    assert "applies_to" in str(exc_info.value)


def test_invalid_policy_path_raises_controlled_error():
    with pytest.raises(PolicyLoadError) as exc_info:
        load_policy_file(Path("policies/odoo/missing.yaml"))

    assert "missing.yaml" in str(exc_info.value)


def test_policy_engine_uses_yaml_version_in_result():
    order = FakeERPAdapter().get_sales_order("so_valid")

    result = PolicyEngine().evaluate("formula_guard", order)

    assert result.policy_id == "formula_guard"
    assert result.policy_version == "0.1.0"


def test_policy_engine_uses_yaml_fail_metadata_for_invalid_formula():
    order = FakeERPAdapter().get_sales_order("so_formula_mismatch")

    result = PolicyEngine().evaluate("formula_guard", order)

    assert result.decision is PreflightDecision.BLOCK
    assert result.risk_level is RiskLevel.R3
