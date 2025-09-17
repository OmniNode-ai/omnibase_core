"""
OnextreeValidationError model.
"""

from pydantic import BaseModel

from omnibase_core.core.errors.core_errors import CoreErrorCode


class ModelOnextreeValidationError(BaseModel):
    """Onextree validation error model using existing CoreErrorCode."""

    code: CoreErrorCode = CoreErrorCode.VALIDATION_ERROR
    message: str
    path: str | None = None
