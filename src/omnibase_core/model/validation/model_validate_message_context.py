"""
ValidateMessageContext model.
"""

from typing import Any

from pydantic import BaseModel


class ModelValidateMessageContext(BaseModel):
    field: str | None = None
    value: Any | None = None
    expected: Any | None = None
    actual: Any | None = None
    reason: str | None = None
