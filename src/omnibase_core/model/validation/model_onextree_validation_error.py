"""
OnextreeValidationError model.
"""

from typing import Optional

from pydantic import BaseModel

from omnibase_core.core.core_error_codes import CoreErrorCode


class ModelOnextreeValidationError(BaseModel):
    """Onextree validation error model using existing CoreErrorCode."""

    code: CoreErrorCode = CoreErrorCode.VALIDATION_ERROR
    message: str
    path: Optional[str] = None
