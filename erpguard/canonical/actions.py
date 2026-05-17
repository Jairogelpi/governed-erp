from dataclasses import dataclass

from erpguard.canonical.enums import CanonicalAction, RiskLevel


@dataclass(frozen=True)
class CanonicalActionDefinition:
    name: CanonicalAction
    canonical_object: str
    default_risk_level: RiskLevel
    description: str


CANONICAL_ACTIONS: dict[CanonicalAction, CanonicalActionDefinition] = {
    CanonicalAction.CONFIRM_SALES_ORDER: CanonicalActionDefinition(
        name=CanonicalAction.CONFIRM_SALES_ORDER,
        canonical_object="SalesOrder",
        default_risk_level=RiskLevel.R3,
        description="Confirm a sales order after semantic preflight checks.",
    ),
    CanonicalAction.INSPECT_SALES_ORDER: CanonicalActionDefinition(
        name=CanonicalAction.INSPECT_SALES_ORDER,
        canonical_object="SalesOrder",
        default_risk_level=RiskLevel.R0,
        description="Inspect a sales order without changing ERP state.",
    ),
    CanonicalAction.VALIDATE_FORMULA: CanonicalActionDefinition(
        name=CanonicalAction.VALIDATE_FORMULA,
        canonical_object="SalesOrderLine",
        default_risk_level=RiskLevel.R0,
        description="Validate formula quantities for a sales order line.",
    ),
    CanonicalAction.INSPECT_ACCESS_RULES: CanonicalActionDefinition(
        name=CanonicalAction.INSPECT_ACCESS_RULES,
        canonical_object="AccessRule",
        default_risk_level=RiskLevel.R0,
        description="Inspect access rules without changing ERP permissions.",
    ),
}
