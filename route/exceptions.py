"""Defines exception classes for Route
"""


class RouteError(Exception):
    """Base exception for all Route related errors.
    """
    pass


class ActionError(RouteError):
    """Exception thrown for invalid operations.
    """
    pass


class ValidationError(ActionError):
    """Exception thrown for validation related errors.
    """
    pass
