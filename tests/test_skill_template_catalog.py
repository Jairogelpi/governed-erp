from __future__ import annotations

from erpguard.product.skill_template_catalog import SkillTemplateCatalogService
from erpguard.product.template_safety import TemplateSafetyService


def test_skill_template_catalog_lists_odoo_and_placeholder_templates():
    templates = SkillTemplateCatalogService().list_templates()
    by_id = {template.template_id: template for template in templates}

    assert "odoo_formula_preflight" in by_id
    assert "gmail_lead_intake_placeholder" in by_id
    assert by_id["odoo_formula_preflight"].connector_id == "odoo"
    assert by_id["gmail_lead_intake_placeholder"].connector_status == "placeholder"
    assert by_id["gmail_lead_intake_placeholder"].installable is False


def test_template_detail_contains_safety_metadata_and_guards():
    template = SkillTemplateCatalogService().get_template("odoo_formula_preflight")

    assert template is not None
    assert template.risk_level == "R2"
    assert "formula_guard" in template.required_guards
    assert "no_odoo_writes" in template.required_guards
    assert template.install_mode == "draft_only"
    assert template.write_actions is False


def test_template_safety_summary_blocks_generic_and_high_risk_writes():
    template = SkillTemplateCatalogService().get_template("odoo_r2_partner_field_update")
    summary = TemplateSafetyService().summarize(template)

    assert summary.can_install_as_draft is True
    assert summary.write_actions_enabled is False
    assert summary.requires_review_compile_approval is True
    assert summary.generic_writes_enabled is False
    assert summary.r3_r4_enabled is False
    assert "requires_approval_before_activation" in summary.guards
