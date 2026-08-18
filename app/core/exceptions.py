from typing import Any


class AppException(Exception):
    status_code: int = 500
    message: str = "Internal Server Error"

    def __init__(self, message: str | None = None, errors: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.errors = errors or {}
        super().__init__(self.message)


class BadRequestException(AppException):
    status_code = 400
    message = "Bad Request"


class UnauthorizedException(AppException):
    status_code = 401
    message = "Unauthorized"


class ForbiddenException(AppException):
    status_code = 403
    message = "Forbidden"


class NotFoundException(AppException):
    status_code = 404
    message = "Not Found"


class ConflictException(AppException):
    status_code = 409
    message = "Conflict"


class TooManyRequestsException(AppException):
    status_code = 429
    message = "Too Many Requests"

    def __init__(
        self,
        message: str | None = None,
        errors: dict[str, Any] | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, errors)
        self.retry_after = retry_after


class AiBridgeException(AppException):
    status_code = 502
    message = "El asistente IA no está disponible en este momento."