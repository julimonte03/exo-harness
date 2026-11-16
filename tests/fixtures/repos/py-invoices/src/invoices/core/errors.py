"""Domain errors. The HTTP layer maps each one to a status code."""


class InvoiceError(Exception):
    code = "invoice_error"

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationError(InvoiceError):
    code = "validation_error"


class NotFoundError(InvoiceError):
    code = "not_found"


class ConflictError(InvoiceError):
    code = "conflict"


class AuthError(InvoiceError):
    code = "unauthenticated"


class PermissionDenied(InvoiceError):
    code = "forbidden"


class ConfigError(InvoiceError):
    code = "config_error"
