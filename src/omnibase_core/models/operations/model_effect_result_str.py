"""Effect Result Str Model.

String result for effect operations.
"""

from pydantic import BaseModel


class ModelEffectResultStr(BaseModel):
    """String result for effect operations."""

    result_type: str = "str"
    value: str
