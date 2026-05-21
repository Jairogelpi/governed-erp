from __future__ import annotations

from pydantic import BaseModel, Field

from erpguard.product.connector_catalog import ConnectorCatalogService


class SkillTemplateDefinition(BaseModel):
    template_id: str
    name: str
    connector_id: str
    connector_name: str
    connector_status: str
    description: str
    category: str
    risk_level: str
    required_guards: list[str] = Field(default_factory=list)
    required_connection: str
    required_permissions: list[str] = Field(default_factory=list)
    required_config: list[str] = Field(default_factory=list)
    opportunity_code: str
    install_mode: str = "draft_only"
    installable: bool = True
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    compile_later: bool = True
    notes: list[str] = Field(default_factory=list)


def _template(
    template_id: str,
    name: str,
    connector_id: str,
    description: str,
    category: str,
    risk_level: str,
    opportunity_code: str,
    required_guards: list[str],
    required_config: list[str] | None = None,
    required_permissions: list[str] | None = None,
    installable: bool = True,
    notes: list[str] | None = None,
) -> SkillTemplateDefinition:
    connector = ConnectorCatalogService().get_connector(connector_id)
    connector_name = connector.name if connector else connector_id
    connector_status = connector.status if connector else "unknown"
    return SkillTemplateDefinition(
        template_id=template_id,
        name=name,
        connector_id=connector_id,
        connector_name=connector_name,
        connector_status=connector_status,
        description=description,
        category=category,
        risk_level=risk_level,
        required_guards=required_guards,
        required_connection=connector_id,
        required_permissions=required_permissions or ["read"],
        required_config=required_config or ["connection_id"],
        opportunity_code=opportunity_code,
        installable=installable and connector_status == "implemented",
        notes=notes or [],
    )


_TEMPLATES = [
    _template(
        "odoo_formula_preflight",
        "Odoo Formula Preflight",
        "odoo",
        "Check formula/capacity alignment before sales-order confirmation.",
        "preflight",
        "R2",
        "formula_mapping_alignment",
        ["read_only", "no_odoo_writes", "dry_run_only", "formula_guard", "requires_approval_before_activation"],
        ["connection_id"],
        ["read:sale.order", "read:product.product", "read:metadata"],
    ),
    _template(
        "odoo_product_data_quality_guard",
        "Odoo Product Data Quality Guard",
        "odoo",
        "Review product metadata completeness using read-only evidence.",
        "data_quality",
        "R1",
        "product_metadata_governance",
        ["read_only", "no_odoo_writes", "dry_run_only"],
        ["connection_id"],
        ["read:product.product"],
    ),
    _template(
        "odoo_stuck_sales_order_review",
        "Odoo Stuck Sales Order Review",
        "odoo",
        "Find sales orders that need operator review without confirming them.",
        "sales_review",
        "R1",
        "read_only_sales_preflight",
        ["read_only", "no_odoo_writes", "dry_run_only"],
        ["connection_id"],
        ["read:sale.order"],
    ),
    _template(
        "odoo_lot_traceability_review",
        "Odoo Lot Traceability Review",
        "odoo",
        "Inspect lot traceability gaps through read-only inventory evidence.",
        "traceability",
        "R2",
        "lot_traceability_review",
        ["read_only", "no_odoo_writes", "dry_run_only"],
        ["connection_id"],
        ["read:stock.production.lot", "read:stock.move"],
    ),
    _template(
        "odoo_r1_chatter_audit_note",
        "Odoo R1 Chatter Audit Note",
        "odoo",
        "Prepare a controlled R1 chatter-note draft; actual pilot remains feature-flagged off.",
        "write_pilot",
        "R1",
        "r1_chatter_audit_note",
        ["read_only", "no_odoo_writes", "dry_run_only", "requires_approval_before_activation"],
        ["connection_id"],
        ["read:target_record"],
        notes=["Installs as draft only; does not enable ALLOW_R1_REAL_WRITE_PILOT."],
    ),
    _template(
        "odoo_r2_partner_field_update",
        "Odoo R2 Partner Field Update",
        "odoo",
        "Prepare a controlled R2 partner-field update draft; real execution stays disabled by default.",
        "write_pilot",
        "R2",
        "r2_partner_field_update",
        ["read_only", "no_odoo_writes", "dry_run_only", "requires_approval_before_activation"],
        ["connection_id"],
        ["read:res.partner"],
        notes=["Installs as draft only; does not enable ALLOW_R2_REAL_WRITE_PILOT."],
    ),
    _template(
        "gmail_lead_intake_placeholder",
        "Gmail Lead Intake Placeholder",
        "gmail",
        "Placeholder template for future lead intake from email.",
        "placeholder",
        "R1",
        "gmail_lead_intake",
        ["catalog_only"],
        ["oauth_connection_id"],
        ["mail.readonly"],
        installable=False,
    ),
    _template(
        "calendar_follow_up_placeholder",
        "Calendar Follow-up Placeholder",
        "google_calendar",
        "Placeholder template for future follow-up scheduling.",
        "placeholder",
        "R1",
        "calendar_follow_up",
        ["catalog_only"],
        ["oauth_connection_id"],
        ["calendar.readonly"],
        installable=False,
    ),
    _template(
        "drive_document_classifier_placeholder",
        "Drive Document Classifier Placeholder",
        "google_drive",
        "Placeholder template for future document classification.",
        "placeholder",
        "R1",
        "drive_document_classifier",
        ["catalog_only"],
        ["oauth_connection_id"],
        ["drive.readonly"],
        installable=False,
    ),
]


class SkillTemplateCatalogService:
    def list_templates(self) -> list[SkillTemplateDefinition]:
        return list(_TEMPLATES)

    def get_template(self, template_id: str) -> SkillTemplateDefinition | None:
        return next((template for template in _TEMPLATES if template.template_id == template_id), None)
