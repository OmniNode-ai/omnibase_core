"""Effect Result Dict Model.

Dictionary result for effect operations (e.g., file operations).
"""

from typing import Literal

from pydantic import BaseModel

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelEffectResultDict(BaseModel):
    """Dictionary result for effect operations (e.g., file operations)."""

    result_type: Literal["dict[str, ModelSchemaValue]"] = "dict[str, ModelSchemaValue]"
    value: dict[str, ModelSchemaValue]
