"""
ValidateMessageContext model.
"""

from typing import Any, Optional

from pydantic import BaseModel


class ModelValidateMessageContext(BaseModel):
    field: Optional[str] = None
    value: Optional[Any] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    reason: Optional[str] = None
