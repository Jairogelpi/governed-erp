from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase0_freeze_artifacts_exist_and_name_the_baseline():
    spec = ROOT / "docs" / "specs" / "84_erpguard_evolution_master_spec.md"
    inventory = ROOT / "docs" / "architecture" / "current_inventory.md"
    matrix = ROOT / "docs" / "architecture" / "capability_reality_matrix.md"
    adr = ROOT / "docs" / "adr" / "0001-erpguard-evolution.md"

    for artifact in (spec, inventory, matrix, adr):
        assert artifact.is_file(), artifact

    baseline = "e483f5c5f272139c65a02ebc32ab11f5e323b6a4"
    assert baseline in spec.read_text(encoding="utf-8")
    assert baseline in inventory.read_text(encoding="utf-8")
    assert baseline in matrix.read_text(encoding="utf-8")
    assert baseline in adr.read_text(encoding="utf-8")


def test_phase0_reality_matrix_preserves_raw_erp_execution_boundary():
    matrix = (ROOT / "docs" / "architecture" / "capability_reality_matrix.md").read_text(
        encoding="utf-8"
    )
    assert "No capability in this matrix authorizes an agent to call a raw ERP method." in matrix
    assert "Odoo order confirmation | `staging_only` / `blocked_by_default`" in matrix
    assert "no generic RPC" in matrix
