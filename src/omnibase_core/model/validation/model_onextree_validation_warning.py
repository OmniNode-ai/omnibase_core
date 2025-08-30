"""
OnextreeValidationWarning model.
"""

from typing import Optional

from pydantic import BaseModel


class ModelOnextreeValidationWarning(BaseModel):
    message: str
    path: Optional[str] = None
