from __future__ import annotations

from erpguard.product.models import WriteDetectedCandidateModel, WriteRiskMatrixEntryModel

_RISK_RULES: dict[str, dict] = {
    "create": {"risk_level": "R2", "risk_code": "creates_new_records", "reversible": False, "rationale": "Creates new records in Odoo — requires dual approval and rollback plan"},
    "write": {"risk_level": "R2", "risk_code": "modifies_existing_records", "reversible": True, "rationale": "Modifies existing Odoo records — field-level rollback possible with backup"},
    "unlink": {"risk_level": "R3", "risk_code": "deletes_records", "reversible": False, "rationale": "Deletes records permanently — requires highest risk authorization"},
    "copy": {"risk_level": "R2", "risk_code": "duplicates_records", "reversible": False, "rationale": "Duplicates records and may cause data inconsistencies"},
    "action_confirm": {"risk_level": "R3", "risk_code": "confirms_document", "reversible": False, "rationale": "Transitions document state to confirmed — may trigger downstream operations"},
    "action_done": {"risk_level": "R3", "risk_code": "finalizes_document", "reversible": False, "rationale": "Finalizes document — typically irreversible workflow state"},
    "action_cancel": {"risk_level": "R2", "risk_code": "cancels_document", "reversible": True, "rationale": "Cancels a document — may be recreatable but disrupts business flow"},
    "button_confirm": {"risk_level": "R3", "risk_code": "confirms_document", "reversible": False, "rationale": "UI confirm action — equivalent to action_confirm in risk level"},
    "button_validate": {"risk_level": "R3", "risk_code": "validates_document", "reversible": False, "rationale": "Validates and locks document — stock moves, accounting entries may post"},
    "button_approve": {"risk_level": "R2", "risk_code": "approves_document", "reversible": True, "rationale": "Approval action — can sometimes be reset with sufficient permissions"},
}

_RISK_ORDER = {"R1": 1, "R2": 2, "R3": 3, "R4": 4}


def _classify_method(method: str) -> dict:
    return _RISK_RULES.get(
        method,
        {"risk_level": "R4", "risk_code": "unknown_write_method", "reversible": False, "rationale": "Unknown write method — blocked by default under R4 policy"},
    )


class WriteRiskMatrix:
    def classify(self, candidates: list[WriteDetectedCandidateModel]) -> list[WriteRiskMatrixEntryModel]:
        entries: list[WriteRiskMatrixEntryModel] = []
        for c in candidates:
            rule = _classify_method(c.write_method)
            entries.append(
                WriteRiskMatrixEntryModel(
                    candidate_id=c.candidate_id,
                    odoo_model=c.odoo_model,
                    write_method=c.write_method,
                    risk_level=rule["risk_level"],
                    risk_code=rule["risk_code"],
                    rationale=rule["rationale"],
                    reversible=rule["reversible"],
                    requires_dual_approval=True,
                    can_execute_real_writes=False,
                )
            )
        return entries

    def overall_risk_level(self, entries: list[WriteRiskMatrixEntryModel]) -> str:
        if not entries:
            return "R1"
        return max((e.risk_level for e in entries), key=lambda r: _RISK_ORDER.get(r, 0))

    def blocking_issues(self, entries: list[WriteRiskMatrixEntryModel]) -> list[str]:
        issues: list[str] = []
        for e in entries:
            if e.risk_level in ("R3", "R4"):
                issues.append(f"{e.write_method} on {e.odoo_model} is {e.risk_level} — {e.risk_code}")
        return issues

    def can_certify(self, entries: list[WriteRiskMatrixEntryModel]) -> bool:
        return all(e.risk_level in ("R1", "R2") for e in entries) if entries else True
