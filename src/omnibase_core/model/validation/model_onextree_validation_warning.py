"""
OnextreeValidationWarning model.
"""

from pydantic import BaseModel


class ModelOnextreeValidationWarning(BaseModel):
    message: str
    path: str | None = None
