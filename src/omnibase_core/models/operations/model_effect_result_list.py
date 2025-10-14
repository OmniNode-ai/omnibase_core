"""Effect Result List Model.

List result for effect operations.
"""

from typing import Any, Literal

from pydantic import BaseModel


class ModelEffectResultList(BaseModel):
    """List result for effect operations."""

    result_type: Literal["list[Any]"] = "list[Any]"
    value: list[Any]
