class ERPGuardError(Exception):
    """Base exception for ERPGuard domain errors."""


class AdapterNotImplementedError(ERPGuardError, NotImplementedError):
    """Raised when an ERP adapter type is recognized but not implemented."""


class ObjectNotFoundError(ERPGuardError):
    """Raised when an adapter cannot find a requested canonical object."""


class AdapterHealthCheckError(ERPGuardError):
    """Raised when an adapter health check fails."""


class PolicyNotFoundError(ERPGuardError):
    """Raised when a requested policy is not registered."""
