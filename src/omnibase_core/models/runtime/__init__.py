# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime models for ONEX node execution."""

from omnibase_core.models.runtime.model_descriptor_circuit_breaker import (
    ModelDescriptorCircuitBreaker,
)
from omnibase_core.models.runtime.model_descriptor_retry_policy import (
    ModelDescriptorRetryPolicy,
)
from omnibase_core.models.runtime.model_domain_plugin_result import (
    ModelDomainPluginResult,
)
from omnibase_core.models.runtime.model_handler_behavior import (
    ModelHandlerBehavior,
)
from omnibase_core.models.runtime.model_handler_metadata import ModelHandlerMetadata
from omnibase_core.models.runtime.model_runtime_aliveness_probe import (
    DEFAULT_TIMEOUT_SECONDS,
    TIMEOUT_ENV_VAR,
    FailureState,
    ModelRuntimeAlivenessProbeCommand,
)
from omnibase_core.models.runtime.model_runtime_aliveness_probe_receipt import (
    ModelRuntimeAlivenessProbeReceipt,
)
from omnibase_core.models.runtime.model_runtime_directive import ModelRuntimeDirective
from omnibase_core.models.runtime.model_runtime_node_instance import (
    ModelRuntimeNodeInstance,
    NodeInstance,
)
from omnibase_core.models.runtime.payloads import (
    ModelCancelExecutionPayload,
    ModelDelayUntilPayload,
    ModelDirectivePayload,
    ModelDirectivePayloadBase,
    ModelEnqueueHandlerPayload,
    ModelRetryWithBackoffPayload,
    ModelScheduleEffectPayload,
)

__all__ = [
    # Core runtime models
    "ModelHandlerBehavior",
    "ModelDescriptorRetryPolicy",
    "ModelDescriptorCircuitBreaker",
    "ModelHandlerMetadata",
    "ModelDomainPluginResult",
    "ModelRuntimeDirective",
    "ModelRuntimeNodeInstance",
    "NodeInstance",
    # Aliveness probe contract (Wave 3)
    "ModelRuntimeAlivenessProbeCommand",
    "ModelRuntimeAlivenessProbeReceipt",
    "FailureState",
    "DEFAULT_TIMEOUT_SECONDS",
    "TIMEOUT_ENV_VAR",
    # Directive payload types (re-exported for convenience)
    "ModelDirectivePayload",
    "ModelDirectivePayloadBase",
    "ModelScheduleEffectPayload",
    "ModelEnqueueHandlerPayload",
    "ModelRetryWithBackoffPayload",
    "ModelDelayUntilPayload",
    "ModelCancelExecutionPayload",
]
