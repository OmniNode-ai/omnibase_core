# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime models for ONEX node execution."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.runtime.model_declared_target_identity import (
        ModelDeclaredTargetIdentity,
    )
    from omnibase_core.models.runtime.model_demand_source_ref import (
        ModelDemandSourceRef,
    )
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
    from omnibase_core.models.runtime.model_runtime_directive import (
        ModelRuntimeDirective,
    )
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelDeclaredTargetIdentity": (
        "omnibase_core.models.runtime.model_declared_target_identity",
        "ModelDeclaredTargetIdentity",
    ),
    "ModelDemandSourceRef": (
        "omnibase_core.models.runtime.model_demand_source_ref",
        "ModelDemandSourceRef",
    ),
    "ModelDescriptorCircuitBreaker": (
        "omnibase_core.models.runtime.model_descriptor_circuit_breaker",
        "ModelDescriptorCircuitBreaker",
    ),
    "ModelDescriptorRetryPolicy": (
        "omnibase_core.models.runtime.model_descriptor_retry_policy",
        "ModelDescriptorRetryPolicy",
    ),
    "ModelDomainPluginConfig": (
        "omnibase_core.models.runtime.model_domain_plugin",
        "ModelDomainPluginConfig",
    ),
    "ModelDomainPluginResult": (
        "omnibase_core.models.runtime.model_domain_plugin_result",
        "ModelDomainPluginResult",
    ),
    "ModelEventRef": ("omnibase_core.models.runtime.model_event_ref", "ModelEventRef"),
    "ModelHandlerBehavior": (
        "omnibase_core.models.runtime.model_handler_behavior",
        "ModelHandlerBehavior",
    ),
    "ModelHandlerMetadata": (
        "omnibase_core.models.runtime.model_handler_metadata",
        "ModelHandlerMetadata",
    ),
    "ModelLivenessArtifactRef": (
        "omnibase_core.models.runtime.model_liveness_artifact_ref",
        "ModelArtifactRef",
    ),
    "ModelLivenessReceipt": (
        "omnibase_core.models.runtime.model_liveness_receipt",
        "ModelLivenessReceipt",
    ),
    "ModelLivenessRegistryEntry": (
        "omnibase_core.models.runtime.model_liveness_registry_entry",
        "ModelLivenessRegistryEntry",
    ),
    "ModelOutputJoinSpec": (
        "omnibase_core.models.runtime.model_output_join_spec",
        "ModelOutputJoinSpec",
    ),
    "ModelPackageIdentity": (
        "omnibase_core.models.runtime.model_package_identity",
        "ModelPackageIdentity",
    ),
    "ModelPrimaryDlqDispositionReceipt": (
        "omnibase_core.models.runtime.model_primary_dlq_disposition_receipt",
        "ModelPrimaryDlqDispositionReceipt",
    ),
    "ModelProbeTargetVerdict": (
        "omnibase_core.models.runtime.model_probe_target_verdict",
        "ModelProbeTargetVerdict",
    ),
    "ModelQuarantineDispositionReceipt": (
        "omnibase_core.models.runtime.model_quarantine_disposition_receipt",
        "ModelQuarantineDispositionReceipt",
    ),
    "ModelRuntimeAddress": (
        "omnibase_core.models.runtime.model_runtime_address",
        "ModelRuntimeAddress",
    ),
    "ModelRuntimeAddressRegistry": (
        "omnibase_core.models.runtime.model_runtime_address_registry",
        "ModelRuntimeAddressRegistry",
    ),
    "DEFAULT_TIMEOUT_SECONDS": (
        "omnibase_core.models.runtime.model_runtime_aliveness_probe",
        "DEFAULT_TIMEOUT_SECONDS",
    ),
    "TIMEOUT_ENV_VAR": (
        "omnibase_core.models.runtime.model_runtime_aliveness_probe",
        "TIMEOUT_ENV_VAR",
    ),
    "ModelRuntimeAlivenessProbeCommand": (
        "omnibase_core.models.runtime.model_runtime_aliveness_probe",
        "ModelRuntimeAlivenessProbeCommand",
    ),
    "ModelRuntimeAlivenessProbeReceipt": (
        "omnibase_core.models.runtime.model_runtime_aliveness_probe_receipt",
        "ModelRuntimeAlivenessProbeReceipt",
    ),
    "ModelRuntimeDirective": (
        "omnibase_core.models.runtime.model_runtime_directive",
        "ModelRuntimeDirective",
    ),
    "RUNTIME_IDENTITY_SCHEMA_VERSION": (
        "omnibase_core.models.runtime.model_runtime_identity",
        "RUNTIME_IDENTITY_SCHEMA_VERSION",
    ),
    "ModelRuntimeIdentity": (
        "omnibase_core.models.runtime.model_runtime_identity",
        "ModelRuntimeIdentity",
    ),
    "ModelRuntimeSkillError": (
        "omnibase_core.models.runtime.model_runtime_skill_error",
        "ModelRuntimeSkillError",
    ),
    "ModelRuntimeSkillRequest": (
        "omnibase_core.models.runtime.model_runtime_skill_request",
        "ModelRuntimeSkillRequest",
    ),
    "ModelRuntimeSkillResponse": (
        "omnibase_core.models.runtime.model_runtime_skill_response",
        "ModelRuntimeSkillResponse",
    ),
    "ModelRuntimeTargetSelector": (
        "omnibase_core.models.runtime.model_runtime_target_selector",
        "ModelRuntimeTargetSelector",
    ),
    "ModelSamplingPolicy": (
        "omnibase_core.models.runtime.model_sampling_policy",
        "ModelSamplingPolicy",
    ),
    "ModelTerminalDispositionRequest": (
        "omnibase_core.models.runtime.model_terminal_disposition_request",
        "ModelTerminalDispositionRequest",
    ),
    "ModelTransportMessage": (
        "omnibase_core.models.runtime.model_transport_message",
        "ModelTransportMessage",
    ),
    "ModelCancelExecutionPayload": (
        "omnibase_core.models.runtime.payloads",
        "ModelCancelExecutionPayload",
    ),
    "ModelDelayUntilPayload": (
        "omnibase_core.models.runtime.payloads",
        "ModelDelayUntilPayload",
    ),
    "ModelDirectivePayload": (
        "omnibase_core.models.runtime.payloads",
        "ModelDirectivePayload",
    ),
    "ModelDirectivePayloadBase": (
        "omnibase_core.models.runtime.payloads",
        "ModelDirectivePayloadBase",
    ),
    "ModelEnqueueHandlerPayload": (
        "omnibase_core.models.runtime.payloads",
        "ModelEnqueueHandlerPayload",
    ),
    "ModelRetryWithBackoffPayload": (
        "omnibase_core.models.runtime.payloads",
        "ModelRetryWithBackoffPayload",
    ),
    "ModelScheduleEffectPayload": (
        "omnibase_core.models.runtime.payloads",
        "ModelScheduleEffectPayload",
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
