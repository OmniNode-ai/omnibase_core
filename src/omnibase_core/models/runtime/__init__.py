# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime models for ONEX node execution."""

from omnibase_core.models.runtime.model_declared_target_identity import (
    ModelDeclaredTargetIdentity,
)
from omnibase_core.models.runtime.model_demand_source_ref import ModelDemandSourceRef
from omnibase_core.models.runtime.model_descriptor_circuit_breaker import (
    ModelDescriptorCircuitBreaker,
)
from omnibase_core.models.runtime.model_descriptor_retry_policy import (
    ModelDescriptorRetryPolicy,
)
from omnibase_core.models.runtime.model_domain_plugin import ModelDomainPluginConfig
from omnibase_core.models.runtime.model_domain_plugin_result import (
    ModelDomainPluginResult,
)
from omnibase_core.models.runtime.model_event_ref import ModelEventRef
from omnibase_core.models.runtime.model_handler_behavior import (
    ModelHandlerBehavior,
)
from omnibase_core.models.runtime.model_handler_metadata import ModelHandlerMetadata
from omnibase_core.models.runtime.model_liveness_artifact_ref import (
    ModelArtifactRef as ModelLivenessArtifactRef,
)
from omnibase_core.models.runtime.model_liveness_receipt import ModelLivenessReceipt
from omnibase_core.models.runtime.model_liveness_registry_entry import (
    ModelLivenessRegistryEntry,
)
from omnibase_core.models.runtime.model_output_join_spec import ModelOutputJoinSpec
from omnibase_core.models.runtime.model_package_identity import ModelPackageIdentity
from omnibase_core.models.runtime.model_primary_dlq_disposition_receipt import (
    ModelPrimaryDlqDispositionReceipt,
)
from omnibase_core.models.runtime.model_probe_target_verdict import (
    ModelProbeTargetVerdict,
)
from omnibase_core.models.runtime.model_quarantine_disposition_receipt import (
    ModelQuarantineDispositionReceipt,
)
from omnibase_core.models.runtime.model_runtime_address import ModelRuntimeAddress
from omnibase_core.models.runtime.model_runtime_address_registry import (
    ModelRuntimeAddressRegistry,
)
from omnibase_core.models.runtime.model_runtime_aliveness_probe import (
    DEFAULT_TIMEOUT_SECONDS,
    TIMEOUT_ENV_VAR,
    ModelRuntimeAlivenessProbeCommand,
)
from omnibase_core.models.runtime.model_runtime_aliveness_probe_receipt import (
    ModelRuntimeAlivenessProbeReceipt,
)
from omnibase_core.models.runtime.model_runtime_directive import ModelRuntimeDirective
from omnibase_core.models.runtime.model_runtime_identity import (
    RUNTIME_IDENTITY_SCHEMA_VERSION,
    ModelRuntimeIdentity,
)
from omnibase_core.models.runtime.model_runtime_skill_error import (
    ModelRuntimeSkillError,
)
from omnibase_core.models.runtime.model_runtime_skill_request import (
    ModelRuntimeSkillRequest,
)
from omnibase_core.models.runtime.model_runtime_skill_response import (
    ModelRuntimeSkillResponse,
)
from omnibase_core.models.runtime.model_runtime_target_selector import (
    ModelRuntimeTargetSelector,
)
from omnibase_core.models.runtime.model_sampling_policy import ModelSamplingPolicy
from omnibase_core.models.runtime.model_terminal_disposition_request import (
    ModelTerminalDispositionRequest,
)
from omnibase_core.models.runtime.model_transport_message import (
    ModelTransportMessage,
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
    "ModelDomainPluginConfig",
    "ModelDomainPluginResult",
    "ModelRuntimeDirective",
    "ModelRuntimeSkillError",
    "ModelRuntimeSkillRequest",
    "ModelRuntimeSkillResponse",
    "ModelRuntimeAddress",
    "ModelRuntimeAddressRegistry",
    "ModelRuntimeTargetSelector",
    "ModelTransportMessage",
    # Aliveness probe contract (Wave 3)
    "ModelRuntimeAlivenessProbeCommand",
    "ModelRuntimeAlivenessProbeReceipt",
    "DEFAULT_TIMEOUT_SECONDS",
    "TIMEOUT_ENV_VAR",
    # Demand-aware liveness contract (OMN-15126 / design OMN-14845)
    "ModelLivenessArtifactRef",
    "ModelDemandSourceRef",
    "ModelEventRef",
    "ModelLivenessReceipt",
    "ModelLivenessRegistryEntry",
    "ModelOutputJoinSpec",
    "ModelSamplingPolicy",
    # Canonical quarantine disposition receipt (OMN-15667)
    "ModelQuarantineDispositionReceipt",
    # Dual-sink terminal durability (OMN-15666)
    "ModelPrimaryDlqDispositionReceipt",
    "ModelTerminalDispositionRequest",
    # Runtime-identity stamp + probe-target assertion (OMN-17308 / OMN-17312)
    "RUNTIME_IDENTITY_SCHEMA_VERSION",
    "ModelPackageIdentity",
    "ModelRuntimeIdentity",
    "ModelDeclaredTargetIdentity",
    "ModelProbeTargetVerdict",
    # Directive payload types (re-exported for convenience)
    "ModelDirectivePayload",
    "ModelDirectivePayloadBase",
    "ModelScheduleEffectPayload",
    "ModelEnqueueHandlerPayload",
    "ModelRetryWithBackoffPayload",
    "ModelDelayUntilPayload",
    "ModelCancelExecutionPayload",
]
