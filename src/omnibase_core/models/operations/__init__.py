# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Operations models for strongly-typed data structures.

Typed models to replace dict[str, Any] usage patterns.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_change_proposal import ModelChangeProposal
    from .model_computation_data import (
        ModelComputationInputData,
        ModelComputationOutputData,
    )
    from .model_compute_operation_data import ModelComputeOperationData
    from .model_effect_operation_config import ModelEffectOperationConfig
    from .model_effect_operation_data import ModelEffectOperationData
    from .model_effect_result import (
        ModelEffectResult,
        ModelEffectResultBool,
        ModelEffectResultDict,
        ModelEffectResultList,
        ModelEffectResultStr,
    )
    from .model_metadata_structures import (
        ModelEventMetadata,
        ModelExecutionMetadata,
        ModelSystemMetadata,
        ModelWorkflowInstanceMetadata,
    )
    from .model_operation_data_base import ModelOperationDataBase
    from .model_operation_parameters import (
        ModelEffectParameters,
        ModelOperationParameters,
        ModelWorkflowParameters,
    )
    from .model_operation_payload_parameters_base import ModelOperationParametersBase
    from .model_orchestrator_operation_data import ModelOrchestratorOperationData
    from .model_payload_structures import (
        ModelEventPayload,
        ModelMessagePayload,
        ModelOperationPayload,
        ModelWorkflowPayload,
    )
    from .model_reducer_operation_data import ModelReducerOperationData

__all__ = [
    "ModelChangeProposal",
    "ModelComputationInputData",
    "ModelComputationOutputData",
    "ModelComputeOperationData",
    "ModelEffectOperationConfig",
    "ModelEffectOperationData",
    "ModelEffectParameters",
    "ModelEffectResult",
    "ModelEffectResultBool",
    "ModelEffectResultDict",
    "ModelEffectResultList",
    "ModelEffectResultStr",
    "ModelEventMetadata",
    "ModelEventPayload",
    "ModelExecutionMetadata",
    "ModelMessagePayload",
    "ModelOperationDataBase",
    "ModelOperationParameters",
    "ModelOperationPayload",
    "ModelOperationParametersBase",
    "ModelOrchestratorOperationData",
    "ModelReducerOperationData",
    "ModelSystemMetadata",
    "ModelWorkflowInstanceMetadata",
    "ModelWorkflowParameters",
    "ModelWorkflowPayload",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelChangeProposal": (
        "omnibase_core.models.operations.model_change_proposal",
        "ModelChangeProposal",
    ),
    "ModelComputationInputData": (
        "omnibase_core.models.operations.model_computation_data",
        "ModelComputationInputData",
    ),
    "ModelComputationOutputData": (
        "omnibase_core.models.operations.model_computation_data",
        "ModelComputationOutputData",
    ),
    "ModelComputeOperationData": (
        "omnibase_core.models.operations.model_compute_operation_data",
        "ModelComputeOperationData",
    ),
    "ModelEffectOperationConfig": (
        "omnibase_core.models.operations.model_effect_operation_config",
        "ModelEffectOperationConfig",
    ),
    "ModelEffectOperationData": (
        "omnibase_core.models.operations.model_effect_operation_data",
        "ModelEffectOperationData",
    ),
    "ModelEffectResult": (
        "omnibase_core.models.operations.model_effect_result",
        "ModelEffectResult",
    ),
    "ModelEffectResultBool": (
        "omnibase_core.models.operations.model_effect_result",
        "ModelEffectResultBool",
    ),
    "ModelEffectResultDict": (
        "omnibase_core.models.operations.model_effect_result",
        "ModelEffectResultDict",
    ),
    "ModelEffectResultList": (
        "omnibase_core.models.operations.model_effect_result",
        "ModelEffectResultList",
    ),
    "ModelEffectResultStr": (
        "omnibase_core.models.operations.model_effect_result",
        "ModelEffectResultStr",
    ),
    "ModelEventMetadata": (
        "omnibase_core.models.operations.model_metadata_structures",
        "ModelEventMetadata",
    ),
    "ModelExecutionMetadata": (
        "omnibase_core.models.operations.model_metadata_structures",
        "ModelExecutionMetadata",
    ),
    "ModelSystemMetadata": (
        "omnibase_core.models.operations.model_metadata_structures",
        "ModelSystemMetadata",
    ),
    "ModelWorkflowInstanceMetadata": (
        "omnibase_core.models.operations.model_metadata_structures",
        "ModelWorkflowInstanceMetadata",
    ),
    "ModelOperationDataBase": (
        "omnibase_core.models.operations.model_operation_data_base",
        "ModelOperationDataBase",
    ),
    "ModelEffectParameters": (
        "omnibase_core.models.operations.model_operation_parameters",
        "ModelEffectParameters",
    ),
    "ModelOperationParameters": (
        "omnibase_core.models.operations.model_operation_parameters",
        "ModelOperationParameters",
    ),
    "ModelWorkflowParameters": (
        "omnibase_core.models.operations.model_operation_parameters",
        "ModelWorkflowParameters",
    ),
    "ModelOperationParametersBase": (
        "omnibase_core.models.operations.model_operation_payload_parameters_base",
        "ModelOperationParametersBase",
    ),
    "ModelOrchestratorOperationData": (
        "omnibase_core.models.operations.model_orchestrator_operation_data",
        "ModelOrchestratorOperationData",
    ),
    "ModelEventPayload": (
        "omnibase_core.models.operations.model_payload_structures",
        "ModelEventPayload",
    ),
    "ModelMessagePayload": (
        "omnibase_core.models.operations.model_payload_structures",
        "ModelMessagePayload",
    ),
    "ModelOperationPayload": (
        "omnibase_core.models.operations.model_payload_structures",
        "ModelOperationPayload",
    ),
    "ModelWorkflowPayload": (
        "omnibase_core.models.operations.model_payload_structures",
        "ModelWorkflowPayload",
    ),
    "ModelReducerOperationData": (
        "omnibase_core.models.operations.model_reducer_operation_data",
        "ModelReducerOperationData",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
