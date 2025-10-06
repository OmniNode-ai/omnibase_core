"""Effect Result Dict Model.

Dictionary result for effect operations (e.g., file operations).
"""

from typing import Any

from pydantic import BaseModel


class ModelEffectResultDict(BaseModel):
    """Dictionary result for effect operations (e.g., file operations)."""

    result_type: str = "dict[str, Any]"
    value: dict[str, Any]
