from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_clean_install_validation_and_fix_log_docs_exist_with_required_sections():
    validation = ROOT / "docs" / "release" / "05_clean_install_vps_validation.md"
    fix_log = ROOT / "docs" / "release" / "06_release_fix_log.md"

    assert validation.exists()
    assert fix_log.exists()

    validation_text = validation.read_text(encoding="utf-8")
    for required in [
        "machine/OS",
        "Python version",
        "release endpoint results",
        "demo UI result",
        "smoke test result",
        "final status",
        "validated_with_fixes",
    ]:
        assert required in validation_text

    fix_log_text = fix_log.read_text(encoding="utf-8")
    for required in [
        "problem",
        "root cause",
        "file changed",
        "fix applied",
        "test/validation command",
    ]:
        assert required in fix_log_text


def test_install_docs_reference_clean_vps_flow_and_release_scripts():
    install_doc = _read("docs/release/01_install_and_run.md")
    validation_doc = _read("docs/release/05_clean_install_vps_validation.md")

    for text in (install_doc, validation_doc):
        assert 'pip install -e ".[dev]"' in text
        assert "uvicorn apps.api.main:app" in text
        assert "/v1/release/health" in text
        assert "/v1/release/readiness-report" in text
        assert "/v1/release/demo-seed" in text
        assert "/v1/release/operator-smoke" in text
        assert "/v1/release/safety-boundaries" in text
        assert "/demo" in text

    assert "scripts/start_release_candidate.sh" in install_doc
    assert "scripts/start_release_candidate.ps1" in install_doc
    assert "scripts/check_release_install.py" in install_doc


def test_env_example_documents_safe_defaults_without_secrets():
    env_example = ROOT / ".env.example"
    assert env_example.exists()

    text = env_example.read_text(encoding="utf-8")
    assert "ERPGUARD_DATABASE_URL=sqlite:///./erpguard_release_candidate.db" in text
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES=false" in text
    assert "ALLOW_R3_R4_REAL_WRITES=false" in text
    assert "your-api-key" not in text.lower()
    assert "password" not in text.lower()


def test_release_docs_do_not_claim_expanded_product_capability():
    combined = "\n".join(
        _read(path)
        for path in [
            "docs/release/05_clean_install_vps_validation.md",
            "docs/release/06_release_fix_log.md",
            "README.md",
        ]
    ).lower()

    forbidden_claims = [
        "r3/r4 writes enabled",
        "generic erp modification runtime enabled",
        "mcp execution gateway",
        "browser automation added",
    ]
    for forbidden in forbidden_claims:
        assert forbidden not in combined
