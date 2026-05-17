from enum import StrEnum


class ERPType(StrEnum):
    ODOO = "odoo"
    ERPNEXT = "erpnext"
    FAKE = "fake"
    MOCK = "mock"


class SalesOrderState(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    CONFIRMED = "confirmed"
    DONE = "done"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class ProductType(StrEnum):
    STOCKABLE = "stockable"
    CONSUMABLE = "consumable"
    SERVICE = "service"
    DIGITAL = "digital"
    UNKNOWN = "unknown"


class ProductTracking(StrEnum):
    NONE = "none"
    LOT = "lot"
    SERIAL = "serial"
    UNKNOWN = "unknown"


class CanonicalAction(StrEnum):
    CONFIRM_SALES_ORDER = "confirm_sales_order"
    INSPECT_SALES_ORDER = "inspect_sales_order"
    VALIDATE_FORMULA = "validate_formula"
    INSPECT_ACCESS_RULES = "inspect_access_rules"


class RiskLevel(StrEnum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"
    R5 = "R5"


class PreflightDecision(StrEnum):
    ALLOW = "allow"
    ALLOW_WITH_WARNING = "allow_with_warning"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"
    UNSUPPORTED = "unsupported"
    NEEDS_MORE_CONTEXT = "needs_more_context"


class InvariantSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


class InvariantStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
