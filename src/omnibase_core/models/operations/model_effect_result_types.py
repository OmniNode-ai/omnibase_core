"""Effect Result Types.

ONEX discriminated union types for effect result patterns.
"""

from typing import Annotated, Any

from pydantic import Discriminator, Field

from omnibase_core.models.operations.model_effect_result_bool import (
    ModelEffectResultBool,
)
from omnibase_core.models.operations.model_effect_result_dict import (
    ModelEffectResultDict,
)
from omnibase_core.models.operations.model_effect_result_list import (
    ModelEffectResultList,
)
from omnibase_core.models.operations.model_effect_result_str import ModelEffectResultStr


def get_effect_result_discriminator(v: Any) -> str:
    """Extract discriminator value for effect result union."""
    if isinstance(v, dict):
        result_type = v.get("result_type", "dict[str, Any]")
        return str(result_type)  # Ensure string type
    return str(getattr(v, "result_type", "dict[str, Any]"))  # Ensure string type


# Type alias with discriminator for Pydantic validation
ModelEffectResult = Annotated[
    ModelEffectResultDict
    | ModelEffectResultBool
    | ModelEffectResultStr
    | ModelEffectResultList,
    Field(discriminator="result_type"),
]

# Type alias with discriminator for Pydantic validation
EffectResultDiscriminator = Discriminator(
    get_effect_result_discriminator,
    custom_error_type="effect_result_discriminator",
    custom_error_message="Invalid effect result type",
    custom_error_context={"discriminator": "result_type"},
)

__all__ = [
    "ModelEffectResult",
]
