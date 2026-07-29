from __future__ import annotations

import json
from uuid import uuid4

from erpguard.db.repositories import get_latest_skill_version, get_opportunity
from erpguard.product.models import WriteDetectedCandidateModel

_WRITE_METHODS = [
    "create", "write", "unlink", "copy",
    "action_confirm", "action_done", "action_cancel",
    "button_confirm", "button_validate", "button_approve",
]

_WRITE_CANDIDATES_BY_OPPORTUNITY_CODE: dict[str, list[dict]] = {
    "formula_mapping_alignment": [
        {
            "odoo_model": "sale.order.line",
            "write_method": "write",
            "description": "Update formula field mapping on sale order lines",
            "risk_level": "R2",
        },
    ],
    "read_only_sales_preflight": [],
    "product_metadata_governance": [
        {
            "odoo_model": "product.product",
            "write_method": "write",
            "description": "Update product metadata governance fields",
            "risk_level": "R2",
        },
    ],
}

_DEFAULT_CANDIDATES: list[dict] = [
    {
        "odoo_model": "sale.order",
        "write_method": "action_confirm",
        "description": "Confirm draft sales orders to 'sale' state",
        "risk_level": "R3",
    },
]


def _opportunity_code_matches(code: str, key: str) -> bool:
    return key.lower() in (code or "").lower()


class WriteCandidateDetector:
    def __init__(self, session) -> None:
        self.session = session

    def detect(self, skill_id: str) -> list[WriteDetectedCandidateModel]:
        opportunity_code = self._resolve_opportunity_code(skill_id)

        raw_candidates = _DEFAULT_CANDIDATES
        for key, candidates in _WRITE_CANDIDATES_BY_OPPORTUNITY_CODE.items():
            if _opportunity_code_matches(opportunity_code, key):
                raw_candidates = candidates
                break

        results: list[WriteDetectedCandidateModel] = []
        for c in raw_candidates:
            results.append(
                WriteDetectedCandidateModel(
                    candidate_id=f"wc_{uuid4().hex[:12]}",
                    opportunity_code=opportunity_code,
                    odoo_model=c["odoo_model"],
                    write_method=c["write_method"],
                    description=c["description"],
                    blocked=True,
                    blocked_reason="ALLOW_REAL_ODOO_WRITES=false",
                    risk_level=c.get("risk_level", "R4"),
                )
            )
        return results

    def _resolve_opportunity_code(self, skill_id: str) -> str:
        version_row = get_latest_skill_version(self.session, skill_id)
        if not version_row:
            return ""
        try:
            pkg = json.loads(version_row.skill_package_json)
        except Exception:
            return ""
        opportunity_id = pkg.get("opportunity_id", "")
        if not opportunity_id:
            return ""
        opp = get_opportunity(self.session, opportunity_id)
        return opp.code if opp else ""
