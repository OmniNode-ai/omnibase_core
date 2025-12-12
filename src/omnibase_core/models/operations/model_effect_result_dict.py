"""Effect Result Dict Model.

Dictionary result for effect operations (e.g., file operations).
"""

from typing import Any, Literal

from pydantic import BaseModel


class ModelEffectResultDict(BaseModel):
    """Dictionary result for effect operations (e.g., file operations)."""

    result_type: Literal["dict[str, Any]"] = "dict[str, Any]"
    value: dict[str, Any]
