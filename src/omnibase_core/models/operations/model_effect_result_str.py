"""Effect Result Str Model.

String result for effect operations.
"""

from typing import Literal

from pydantic import BaseModel


class ModelEffectResultStr(BaseModel):
    """String result for effect operations."""

    result_type: Literal["str"] = "str"
    value: str
