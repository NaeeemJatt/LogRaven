# LogRaven — Custom Exception Classes
#
# PURPOSE:
#   Custom exceptions that map to HTTP status codes.
#   The global exception handler in main.py catches these and converts
#   them to consistent JSON error responses.
#
# RESPONSE SHAPE:
#   {"error": "Human readable message", "code": "MACHINE_CODE", "detail": "optional"}
#
# TODO Month 1 Week 1: Implement this file.

from fastapi import HTTPException


class LogRavenError(Exception):
    """Base exception for all LogRaven errors."""
    status_code = 500  # default — subclasses override this
    def __init__(self, message: str, code: str = "LOGRAVEN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(LogRavenError):
    status_code = 404
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND")


class ForbiddenError(LogRavenError):
    status_code = 403
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "FORBIDDEN")


class RateLimitError(LogRavenError):
    status_code = 429
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT")


class InvalidFileTypeError(LogRavenError):
    status_code = 400
    def __init__(self, message: str = "Invalid file type"):
        super().__init__(message, "INVALID_FILE_TYPE")


class FileTooLargeError(LogRavenError):
    status_code = 400
    def __init__(self, message: str = "File exceeds tier size limit"):
        super().__init__(message, "FILE_TOO_LARGE")


class LicenseError(LogRavenError):
    status_code = 403
    def __init__(self, message: str = "Invalid or expired license"):
        super().__init__(message, "LICENSE_ERROR")


class UnknownLogTypeError(LogRavenError):
    status_code = 400
    def __init__(self, message: str = "Cannot detect log file format"):
        super().__init__(message, "UNKNOWN_LOG_TYPE")


class AIEngineError(LogRavenError):
    status_code = 503
    def __init__(self, message: str = "AI analysis engine unavailable"):
        super().__init__(message, "AI_ENGINE_ERROR")
