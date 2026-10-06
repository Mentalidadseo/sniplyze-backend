"""Errores de dominio que la API traduce a respuestas HTTP claras."""
from typing import Any


class AppError(Exception):
    status_code = 400
    code = "error"

    def __init__(self, message: str, **details: Any):
        super().__init__(message)
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {"error": self.code, "message": self.message, **self.details}


class InputError(AppError):
    """Entrada inválida: se rechaza antes de gastar crédito."""

    status_code = 422
    code = "invalid_input"


class ConfigError(AppError):
    status_code = 503
    code = "not_configured"


class ConfirmationRequired(AppError):
    """La consulta supera el umbral de coste (o su coste es desconocido) y necesita confirmación."""

    status_code = 402
    code = "confirmation_required"


class BudgetExceeded(AppError):
    status_code = 402
    code = "budget_exceeded"


class ProviderError(AppError):
    """El proveedor de datos devolvió un error o una respuesta inesperada."""

    status_code = 502
    code = "provider_error"


class NotFound(AppError):
    status_code = 404
    code = "not_found"
