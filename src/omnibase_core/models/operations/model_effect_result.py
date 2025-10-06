"""Effect result models with discriminated union support.

Re-export module for effect result components including individual result types
and discriminated union patterns.
"""

from omnibase_core.models.operations.effect_result_types import (
    EffectResultDiscriminator,
    EffectResultUnion,
    ModelEffectResult,
    get_effect_result_discriminator,
)
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

__all__ = [
    "ModelEffectResultDict",
    "ModelEffectResultBool",
    "ModelEffectResultStr",
    "ModelEffectResultList",
    "ModelEffectResult",
    "EffectResultUnion",
    "EffectResultDiscriminator",
    "get_effect_result_discriminator",
]
