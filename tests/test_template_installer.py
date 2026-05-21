from __future__ import annotations

from erpguard.db.repositories import get_automation_draft
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.draft_validator import DraftValidatorService
from erpguard.product.skill_package_builder import SkillPackageBuilder
from erpguard.product.template_installer import TemplateInstallerService
from erpguard.product.template_requirements import TemplateRequirementsService


def test_requirements_check_passes_for_installable_odoo_template_with_connection_id():
    result = TemplateRequirementsService().check(
        "odoo_formula_preflight",
        {"connection_id": "conn_demo", "capacity_field": "x_studio_capacidad_ml"},
    )

    assert result.can_install is True
    assert result.missing_requirements == []
    assert result.blocking_reasons == []


def test_requirements_check_blocks_placeholder_connector_template():
    result = TemplateRequirementsService().check(
        "gmail_lead_intake_placeholder",
        {"connection_id": "gmail_conn_demo"},
    )

    assert result.can_install is False
    assert "connector_not_implemented" in result.blocking_reasons


def test_template_install_creates_safe_automation_draft_that_can_validate_and_compile():
    init_db()
    session = SessionLocal()
    try:
        installed = TemplateInstallerService(session).install_draft(
            "odoo_formula_preflight",
            {"connection_id": "conn_marketplace_demo", "capacity_field": "x_studio_capacidad_ml"},
        )

        assert installed.status == "draft_installed"
        assert installed.draft.runtime_mode == "dry_run_only"
        assert installed.draft.write_actions is False
        assert installed.draft.draft_package["marketplace_template_id"] == "odoo_formula_preflight"
        assert installed.next_steps == ["review", "validate", "compile", "approval"]

        draft_row = get_automation_draft(session, installed.draft.draft_id)
        assert draft_row is not None
        assert draft_row.write_actions is False

        validation = DraftValidatorService(session).validate(installed.draft.draft_id)
        assert validation.passed is True

        review = installed.review
        compiled = SkillPackageBuilder(session).build(review.review_id)
        assert compiled.skill_id.startswith("skill_")
        assert compiled.write_actions is False
        assert compiled.runtime_mode == "dry_run_only"
        assert "no_odoo_writes" in compiled.guards
    finally:
        session.close()


def test_installed_templates_list_returns_marketplace_drafts():
    init_db()
    session = SessionLocal()
    try:
        installer = TemplateInstallerService(session)
        installed = installer.install_draft("odoo_product_data_quality_guard", {"connection_id": "conn_demo"})
        installed_list = installer.list_installed()

        assert any(item.draft_id == installed.draft.draft_id for item in installed_list)
        assert any(item.template_id == "odoo_product_data_quality_guard" for item in installed_list)
    finally:
        session.close()
