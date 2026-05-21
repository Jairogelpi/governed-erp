from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.marketplace import (
    ConnectorDetailResponse,
    ConnectorListResponse,
    InstalledTemplatesResponse,
    SkillTemplateDetailResponse,
    SkillTemplateListResponse,
    TemplateConfigurationRequest,
    TemplateInstallResponse,
    TemplateRequirementsResponse,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.connector_catalog import ConnectorCatalogService
from erpguard.product.skill_template_catalog import SkillTemplateCatalogService
from erpguard.product.template_installer import TemplateInstallerService
from erpguard.product.template_requirements import TemplateRequirementsService
from erpguard.product.template_safety import TemplateSafetyService


router = APIRouter(prefix="/v1/marketplace", tags=["marketplace"])


@router.get("/connectors", response_model=ConnectorListResponse)
def list_connectors():
    return {"connectors": [connector.model_dump() for connector in ConnectorCatalogService().list_connectors()]}


@router.get("/connectors/{connector_id}", response_model=ConnectorDetailResponse)
def get_connector(connector_id: str):
    connector = ConnectorCatalogService().get_connector(connector_id)
    if connector is None:
        return _not_found("connector_not_found", f"Connector '{connector_id}' not found.")
    return connector.model_dump()


@router.get("/skill-templates", response_model=SkillTemplateListResponse)
def list_skill_templates():
    return {"templates": [template.model_dump() for template in SkillTemplateCatalogService().list_templates()]}


@router.get("/skill-templates/{template_id}", response_model=SkillTemplateDetailResponse)
def get_skill_template(template_id: str):
    template = SkillTemplateCatalogService().get_template(template_id)
    if template is None:
        return _not_found("template_not_found", f"Skill template '{template_id}' not found.")
    safety = TemplateSafetyService().summarize(template)
    return {**template.model_dump(), "safety_summary": safety.model_dump()}


@router.post("/skill-templates/{template_id}/check-requirements", response_model=TemplateRequirementsResponse)
def check_skill_template_requirements(template_id: str, request: TemplateConfigurationRequest):
    result = TemplateRequirementsService().check(template_id, request.configuration)
    if "template_not_found" in result.blocking_reasons:
        return _not_found("template_not_found", f"Skill template '{template_id}' not found.")
    return result.model_dump()


@router.post("/skill-templates/{template_id}/install-draft", response_model=TemplateInstallResponse)
def install_skill_template_draft(template_id: str, request: TemplateConfigurationRequest):
    init_db()
    session = SessionLocal()
    try:
        try:
            result = TemplateInstallerService(session).install_draft(template_id, request.configuration)
        except ValueError as exc:
            code = str(exc)
            if code == "template_not_found":
                return _not_found("template_not_found", f"Skill template '{template_id}' not found.")
            requirements = TemplateRequirementsService().check(template_id, request.configuration)
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "template_requirements_not_met",
                        "message": "Template requirements are not met.",
                        "details": requirements.model_dump(mode="json"),
                    }
                },
            )
        return result.model_dump()
    finally:
        session.close()


@router.get("/installed", response_model=InstalledTemplatesResponse)
def list_installed_marketplace_templates():
    init_db()
    session = SessionLocal()
    try:
        installed = TemplateInstallerService(session).list_installed()
        return {"installed": [item.model_dump() for item in installed]}
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})
