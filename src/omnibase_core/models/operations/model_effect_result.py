"""Effect result models with discriminated union support.

Re-export module for effect result components including individual result types
and discriminated union patterns.
"""

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
from omnibase_core.models.operations.model_effect_result_types import ModelEffectResult

__all__ = [
    "ModelEffectResultDict",
    "ModelEffectResultBool",
    "ModelEffectResultStr",
    "ModelEffectResultList",
    "ModelEffectResult",
]
