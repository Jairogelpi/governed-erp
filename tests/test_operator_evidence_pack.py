from __future__ import annotations

from erpguard.product.operator_evidence_pack import OperatorEvidencePackService


def test_assemble_returns_pack():
    svc = OperatorEvidencePackService()
    result = svc.assemble(created_by="test_op")
    assert result.pack_id.startswith("evpack_")
    assert result.evidence_status == "ready"
    assert result.sprint_chain == "20-26"


def test_assemble_with_seed_result():
    svc = OperatorEvidencePackService()
    seed = {"session_id": "rec_abc", "version_id": "ui_skv_xyz", "run_id": "run_123"}
    result = svc.assemble(seed_result=seed, created_by="test_op")
    assert result.seed_result["session_id"] == "rec_abc"
    assert result.seed_result["version_id"] == "ui_skv_xyz"


def test_assemble_safety_checks_in_pack():
    svc = OperatorEvidencePackService()
    result = svc.assemble()
    sc = result.safety_checks
    assert sc["verdict"] == "safe"
    assert sc["invariants_enforced"] > 0
    assert sc["invariants_violated"] == 0


def test_assemble_runbook_summary_in_pack():
    svc = OperatorEvidencePackService()
    result = svc.assemble()
    rb = result.runbook_summary
    assert rb["operation_count"] > 0
    assert len(rb["operations"]) == rb["operation_count"]


def test_assemble_test_evidence_in_pack():
    svc = OperatorEvidencePackService()
    result = svc.assemble()
    te = result.test_evidence
    assert te["total_sprints_covered"] >= 7
    assert te["all_invariants_enforced"] is True


def test_get_existing_pack():
    svc = OperatorEvidencePackService()
    created = svc.assemble(created_by="test_get")
    fetched = svc.get(created.pack_id)
    assert fetched is not None
    assert fetched.pack_id == created.pack_id
    assert fetched.created_by == "test_get"


def test_get_nonexistent_pack_returns_none():
    svc = OperatorEvidencePackService()
    result = svc.get("evpack_doesnotexist")
    assert result is None


def test_list_packs_includes_created():
    svc = OperatorEvidencePackService()
    created = svc.assemble(created_by="test_list")
    packs = svc.list_packs()
    ids = [p.pack_id for p in packs]
    assert created.pack_id in ids


def test_scenario_label_stored():
    svc = OperatorEvidencePackService()
    label = "Custom Scenario Label"
    result = svc.assemble(scenario_label=label)
    assert result.scenario_label == label


def test_timestamps_present():
    svc = OperatorEvidencePackService()
    result = svc.assemble()
    assert result.created_at
    assert result.updated_at
