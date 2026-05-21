class ERPGuardError(Exception):
    """Base exception for ERPGuard domain errors."""


class AdapterNotImplementedError(ERPGuardError, NotImplementedError):
    """Raised when an ERP adapter type is recognized but not implemented."""


class ObjectNotFoundError(ERPGuardError):
    """Raised when an adapter cannot find a requested canonical object."""


class AdapterHealthCheckError(ERPGuardError):
    """Raised when an adapter health check fails."""


class AdapterConfigurationError(ERPGuardError):
    """Raised when an adapter cannot be built because required config is missing."""


class AdapterAuthenticationError(ERPGuardError):
    """Raised when an adapter cannot authenticate with its ERP."""


class ReadOnlyViolationError(ERPGuardError):
    """Raised when read-only Odoo access attempts a forbidden method."""


class PolicyNotFoundError(ERPGuardError):
    """Raised when a requested policy is not registered."""


class PolicyLoadError(ERPGuardError):
    """Raised when a policy file cannot be loaded."""


class PolicyValidationError(ERPGuardError):
    """Raised when a policy file fails schema validation."""
