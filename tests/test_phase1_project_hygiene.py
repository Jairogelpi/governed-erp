from pathlib import Path

import tomllib

from apps.api.main import app
from erpguard.version import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_public_version_is_converged_across_package_api_and_readme():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert pyproject["project"]["version"] == __version__
    assert app.version == __version__
    assert f"ERPGuard Evolution v{__version__}" in readme


def test_phase1_delivery_artifacts_exist():
    required = (
        "uv.lock",
        "Dockerfile",
        ".github/workflows/ci.yml",
        "LICENSE",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "GOVERNANCE.md",
        "SUPPORT.md",
        "CITATION.cff",
        "CHANGELOG.md",
        "ROADMAP.md",
        "docs/public/README.md",
        "docs/legacy/README.md",
        "docs/DEPRECATION_POLICY.md",
    )
    for relative_path in required:
        assert (ROOT / relative_path).is_file(), relative_path

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pip install" in dockerfile
    assert '"apps.api.main:app"' in dockerfile
    assert "docker build" in workflow


def test_phase1_quality_tools_are_declared_and_safety_boundary_remains_locked():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]
    assert any(dependency.startswith("ruff") for dependency in dev_dependencies)
    assert any(dependency.startswith("mypy") for dependency in dev_dependencies)
    assert "ERPGuard remains the mandatory safety kernel" in (
        ROOT / "docs" / "DEPRECATION_POLICY.md"
    ).read_text(encoding="utf-8")
