# src/core/exceptions.py


class VRPOptimizerError(Exception):
    """Base exception for VRP Optimizer."""

    def __init__(self, message: str = None):
        self.message = message
        super().__init__(self.message)


class DataValidationError(VRPOptimizerError):
    """Raised when data validation fails."""

    def __init__(self, message: str = None, errors: list = None):
        self.errors = errors or []
        super().__init__(message or "Data validation failed")


class OptimizationError(Exception):
    """Exception raised for errors in the optimization process."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class GeocodingError(VRPOptimizerError):
    """Raised when geocoding fails."""

    def __init__(self, message: str = None, location: str = None):
        self.location = location
        super().__init__(message or f"Geocoding failed for location: {location}")


class RouteValidationError(VRPOptimizerError):
    """Raised when route validation fails."""

    def __init__(self, message: str = None, route_id: str = None):
        self.route_id = route_id
        super().__init__(message or f"Route validation failed for route: {route_id}")


class ResourceExhaustedError(VRPOptimizerError):
    """Raised when system resources are exhausted."""

    def __init__(self, message: str = None, resource: str = None):
        self.resource = resource
        super().__init__(message or f"Resource exhausted: {resource}")


class ConfigurationError(VRPOptimizerError):
    """Raised when there's a configuration error."""

    def __init__(self, message: str = None, setting: str = None):
        self.setting = setting
        super().__init__(message or f"Configuration error for setting: {setting}")


class FileProcessingError(VRPOptimizerError):
    """Raised when file processing fails."""

    def __init__(self, message: str = None, filename: str = None):
        self.filename = filename
        super().__init__(message or f"File processing failed for: {filename}")


class APIError(VRPOptimizerError):
    """Raised when API operations fail."""

    def __init__(self, message: str = None, status_code: int = None):
        self.status_code = status_code
        super().__init__(message or f"API error with status code: {status_code}")


class SecurityError(VRPOptimizerError):
    """Raised for security-related issues."""

    def __init__(self, message: str = None, security_type: str = None):
        self.security_type = security_type
        super().__init__(message or f"Security error of type: {security_type}")
