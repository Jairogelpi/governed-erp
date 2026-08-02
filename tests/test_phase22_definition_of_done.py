"""Spec 95 (Phase 22) -- Definition of Done (TFM), Sec 41.

Runs every checklist item as an assertion where it is mechanically
checkable from the repository state alone, and documents the rest here
as manual-verification steps -- never silently skipped, never assumed.

Mechanically checkable in this test:
    - Full test suite exists and is non-trivially sized (a proxy for
      "full tests reproducible" -- the actual reproduction is CI itself,
      not this test asserting its own success recursively).
    - PostgreSQL migration coverage exists (the CI job, not re-run here
      -- see `.github/workflows/ci.yml`'s `postgres-migrations` job).
    - Every phase's key capability module/route exists (a structural
      proxy for "X exists", not a functional guarantee -- functional
      correctness is what the rest of the test suite is for).
    - The annex/doc set from `test_phase22_docs_contract.py` exists
      (re-asserted here at the DoD level intentionally -- redundancy
      between a docs contract and a DoD checklist is acceptable; they
      answer different questions: "does the file exist" vs. "is the
      release ready").
    - The `v1.0.0-tfm` tag: checked, but ABSENCE IS NOT A TEST FAILURE.
      Tagging the immutable TFM release is a deliberate, one-way human
      decision (see `docs/tfm/annexes/code_and_repository.md`) --
      this test reports its status via a print, never fails the suite
      on it, and must never be modified to auto-create the tag.

Documented here as MANUAL, not mechanically checkable, and NOT skipped
silently -- someone has to actually do these before `v1.0.0-tfm`:
    - Baseline frozen (human judgment: "is this branch actually frozen").
    - Real secret provider exists (this project uses
      `EncryptedLocalSecretProvider`; whether that satisfies "real
      secret provider" for a given deployment context is a judgment
      call, not a boolean this test can compute).
    - Memory is within 20 pages -- `docs/tfm/memoria_draft.md` is a
      Markdown draft; page count depends on the final typeset document,
      not this file's line count.
    - Video is within 5 minutes -- no video exists yet; see
      `docs/demo/five_minute_demo_script.md` for the runbook.
    - Annexes and repository permissions are correct -- "correct" here
      means "the thesis committee/university's actual submission
      requirements are met," which this codebase cannot know.
    - Clean install works -- `scripts/validate_demo_install.py` is the
      mechanical tool for this, but running it against a live
      `docker compose` stack is an integration action, not a unit test
      (it needs Docker and a running container) -- run it manually
      before submission, don't infer its result from this file passing.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_test_suite_exists_and_is_non_trivially_sized():
    test_files = list((ROOT / "tests").glob("test_*.py"))
    assert len(test_files) > 100, "expected a large, phase-spanning test suite, not a token handful of files"


def test_postgres_migration_ci_job_is_configured():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "postgres-migrations" in ci
    assert "alembic downgrade -1" in ci, "downgrade/upgrade cycle must be part of the migration gate, not just upgrade"


def test_key_phase_capabilities_are_structurally_present():
    expected_modules = [
        "erpguard/domain/identity/auth.py",
        "erpguard/connectors/sdk",
        "erpguard/domain/events/ocel_service.py",
        "erpguard/domain/processes/candidates.py",
        "erpguard/domain/replays/service.py",
        "erpguard/domain/proofs",
        "erpguard/domain/skills",
        "erpguard/domain/execution/permit_service.py",
        "erpguard/domain/shadow/service.py",
        "erpguard/domain/recommendations",
        "erpguard/domain/canary/routing.py",
        "erpguard/domain/outcomes/interpretation.py",
        "erpguard/domain/evidence/decision_outcome_bundle.py",
        "erpguard/benchmark",
        "web/src/app",
    ]
    missing = [path for path in expected_modules if not (ROOT / path).exists()]
    assert missing == [], f"Missing structural presence for: {missing}"


def test_release_gate_blocking_docs_exist():
    """Sec 32.3's release-gate criteria this test CAN check the existence
    prerequisite for (not the semantic correctness of): capability
    reality matrix, SBOM tooling wired into CI, secret scan wired into
    CI, benchmark artifact tooling."""

    assert (ROOT / "docs" / "architecture" / "capability_reality_matrix.md").exists()
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "secret-scan" in ci
    assert "cyclonedx" in ci.lower(), "SBOM generation step must be wired into CI"
    assert (ROOT / "scripts" / "export_benchmark_report.py").exists()


def test_v1_0_0_tfm_tag_status_is_reported_not_asserted():
    """Deliberately does not fail whichever way this comes out -- see
    module docstring. Only reports the current state for visibility."""

    result = subprocess.run(
        ["git", "tag", "-l", "v1.0.0-tfm"], cwd=ROOT, capture_output=True, text=True, check=False,
    )
    tag_exists = bool(result.stdout.strip())
    print(f"\nv1.0.0-tfm tag exists: {tag_exists}")
    if not tag_exists:
        print(
            "NOT YET TAGGED -- this is expected and correct until the thesis "
            "author deliberately decides to freeze the TFM submission. See "
            "docs/tfm/annexes/code_and_repository.md for the tagging command."
        )
