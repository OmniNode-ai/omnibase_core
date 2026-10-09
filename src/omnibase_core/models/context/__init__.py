# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Context models for typed Generic[TContext] patterns.

Reusable typed context models for use as type parameters
in generic models like ModelErrorDetails[TContext].

Available Context Models:
    Error/Retry Context:
        - ModelTraceContext: Distributed tracing and correlation
        - ModelOperationalContext: Operation-level metadata
        - ModelRetryContext: Retry-related metadata
        - ModelResourceContext: Resource identification
        - ModelRuntimeDirectivePayload: Runtime directive parameters
        - ModelUserContext: User and session tracking
        - ModelValidationContext: Field-level validation details
        - ModelErrorMetadata: Error tracking with correlation and retry support
        - ModelMetricsContext: Observability and distributed tracing metadata

    Effect Context:
        - ModelEffectInputData: Effect operation targets and parameters

    Intent Context:
        - ModelReducerIntentPayload: Typed payload for reducer intents (FSM transitions)

    Metadata Context:
        - ModelSessionContext: Session identification and client context
        - ModelHttpRequestMetadata: HTTP-specific request metadata
        - ModelAuthorizationContext: RBAC/ABAC authorization information
        - ModelAuditMetadata: Compliance and audit trail metadata
        - ModelCheckpointMetadata: Checkpoint state persistence metadata
        - ModelDetectionMetadata: Security pattern detection metadata
        - ModelNodeInitMetadata: Node initialization tracking metadata

    Action/Routing Context (OMN-1049):
        - ModelActionExecutionContext: Action/node execution context
        - ModelRoutingMetadata: Service routing and load balancing
        - ModelServiceDiscoveryMetadata: Service discovery and composition
        - ModelActionParameters: Typed action execution parameters

Thread Safety:
    All context models are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.

Usage Notes:
    Checkpoint Metadata Models:
        There are two checkpoint metadata models with distinct purposes:

        - ModelCheckpointMetadata (this module):
            For workflow state tracking. Use when you need to capture checkpoint
            state within a workflow context, including trigger events, workflow
            stage, and checkpoint version.

        - ModelStorageCheckpointMetadata (omnibase_core.models.core):
            For storage backend persistence. Use when implementing checkpoint
            storage backends that need retention policies, storage labels, and
            blob store integration.

Example:
    Using context models with Generic patterns::

        from omnibase_core.models.context import (
            ModelTraceContext,
            ModelOperationalContext,
            ModelRetryContext,
            ModelSessionContext,
        )
        from uuid import uuid4

        # Create trace context
        trace = ModelTraceContext(
            trace_id=uuid4(),
            span_id=uuid4(),
        )

        # Create operational context
        operation = ModelOperationalContext(
            operation_name="create_user",
            timeout_ms=5000,
        )

        # Create retry context
        retry = ModelRetryContext(
            attempt=2,
            retryable=True,
        )

        # Create session context
        session = ModelSessionContext(
            session_id="sess_123",
            locale="en-US",
        )
"""

from __future__ import annotations

__all__ = [
    # Knowledge context bundle models (OMN-11928)
    "ModelContextProvenance",
    "ModelADRSummary",
    "ModelAntipatternSummary",
    "ModelLearningMatch",
    "ModelGraphSnapshot",
    "ModelKnowledgeContextBundle",
    # Error/Retry context models
    "ModelErrorContext",
    "ModelErrorMetadata",
    "ModelOperationalContext",
    "ModelResourceContext",
    "ModelRetryContext",
    "ModelRuntimeDirectivePayload",
    "ModelTraceContext",
    "ModelUserContext",
    "ModelValidationContext",
    # Error category constants (re-exported from model_error_metadata)
    "CATEGORY_AUTH",
    "CATEGORY_NETWORK",
    "CATEGORY_SYSTEM",
    "CATEGORY_VALIDATION",
    "CLIENT_ERROR_CATEGORIES",
    "SERVER_ERROR_CATEGORIES",
    # Effect context models
    "ModelEffectInputData",
    "ModelEffectTemplateContext",
    # Intent context models
    "ModelReducerIntentPayload",
    # Metadata context models
    "ModelAuditMetadata",
    "ModelAuthorizationContext",
    "ModelCheckpointMetadata",
    "ModelDetectionMetadata",
    "ModelHttpRequestMetadata",
    "ModelMetricsContext",
    "ModelNodeInitMetadata",
    "ModelSessionContext",
    # Action/Routing context models (OMN-1049)
    "LoadBalanceStrategy",
    "ModelActionExecutionContext",
    "ModelActionParameters",
    "ModelRoutingMetadata",
    "ModelServiceDiscoveryMetadata",
    "VALID_LOAD_BALANCE_STRATEGIES",
]

# Action/Routing context models (OMN-1049)
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.context.model_action_execution_context import (
        ModelActionExecutionContext,
    )
    from omnibase_core.models.context.model_action_parameters import (
        ModelActionParameters,
    )

    # Knowledge context bundle models (OMN-11928)
    from omnibase_core.models.context.model_adr_summary import ModelADRSummary
    from omnibase_core.models.context.model_antipattern_summary import (
        ModelAntipatternSummary,
    )

    # Metadata context models
    from omnibase_core.models.context.model_audit_metadata import ModelAuditMetadata
    from omnibase_core.models.context.model_authorization_context import (
        ModelAuthorizationContext,
    )
    from omnibase_core.models.context.model_checkpoint_metadata import (
        ModelCheckpointMetadata,
    )
    from omnibase_core.models.context.model_context_provenance import (
        ModelContextProvenance,
    )
    from omnibase_core.models.context.model_detection_metadata import (
        ModelDetectionMetadata,
    )

    # Effect context models
    from omnibase_core.models.context.model_effect_input_data import (
        ModelEffectInputData,
    )
    from omnibase_core.models.context.model_effect_template_context import (
        ModelEffectTemplateContext,
    )
    from omnibase_core.models.context.model_error_metadata import (
        CATEGORY_AUTH,
        CATEGORY_NETWORK,
        CATEGORY_SYSTEM,
        CATEGORY_VALIDATION,
        CLIENT_ERROR_CATEGORIES,
        SERVER_ERROR_CATEGORIES,
        ModelErrorMetadata,
    )
    from omnibase_core.models.context.model_graph_snapshot import ModelGraphSnapshot
    from omnibase_core.models.context.model_http_request_metadata import (
        ModelHttpRequestMetadata,
    )
    from omnibase_core.models.context.model_knowledge_context_bundle import (
        ModelKnowledgeContextBundle,
    )
    from omnibase_core.models.context.model_learning_match import ModelLearningMatch
    from omnibase_core.models.context.model_metrics_context import ModelMetricsContext
    from omnibase_core.models.context.model_node_init_metadata import (
        ModelNodeInitMetadata,
    )

    # Error/Retry context models
    from omnibase_core.models.context.model_operational_context import (
        ModelOperationalContext,
    )

    # Intent context models
    from omnibase_core.models.context.model_reducer_intent_payload import (
        ModelReducerIntentPayload,
    )
    from omnibase_core.models.context.model_resource_context import ModelResourceContext
    from omnibase_core.models.context.model_retry_context import ModelRetryContext

    # Runtime context models
    from omnibase_core.models.context.model_retry_error_context import ModelErrorContext
    from omnibase_core.models.context.model_routing_metadata import (
        VALID_LOAD_BALANCE_STRATEGIES,
        LoadBalanceStrategy,
        ModelRoutingMetadata,
    )
    from omnibase_core.models.context.model_runtime_directive_payload import (
        ModelRuntimeDirectivePayload,
    )
    from omnibase_core.models.context.model_service_discovery_metadata import (
        ModelServiceDiscoveryMetadata,
    )
    from omnibase_core.models.context.model_session_context import ModelSessionContext
    from omnibase_core.models.context.model_trace_context import ModelTraceContext
    from omnibase_core.models.context.model_user_context import ModelUserContext
    from omnibase_core.models.context.model_validation_context import (
        ModelValidationContext,
    )


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelActionExecutionContext": (
        "omnibase_core.models.context.model_action_execution_context",
        "ModelActionExecutionContext",
    ),
    "ModelActionParameters": (
        "omnibase_core.models.context.model_action_parameters",
        "ModelActionParameters",
    ),
    "ModelADRSummary": (
        "omnibase_core.models.context.model_adr_summary",
        "ModelADRSummary",
    ),
    "ModelAntipatternSummary": (
        "omnibase_core.models.context.model_antipattern_summary",
        "ModelAntipatternSummary",
    ),
    "ModelAuditMetadata": (
        "omnibase_core.models.context.model_audit_metadata",
        "ModelAuditMetadata",
    ),
    "ModelAuthorizationContext": (
        "omnibase_core.models.context.model_authorization_context",
        "ModelAuthorizationContext",
    ),
    "ModelCheckpointMetadata": (
        "omnibase_core.models.context.model_checkpoint_metadata",
        "ModelCheckpointMetadata",
    ),
    "ModelContextProvenance": (
        "omnibase_core.models.context.model_context_provenance",
        "ModelContextProvenance",
    ),
    "ModelDetectionMetadata": (
        "omnibase_core.models.context.model_detection_metadata",
        "ModelDetectionMetadata",
    ),
    "ModelEffectInputData": (
        "omnibase_core.models.context.model_effect_input_data",
        "ModelEffectInputData",
    ),
    "ModelEffectTemplateContext": (
        "omnibase_core.models.context.model_effect_template_context",
        "ModelEffectTemplateContext",
    ),
    "CATEGORY_AUTH": (
        "omnibase_core.models.context.model_error_metadata",
        "CATEGORY_AUTH",
    ),
    "CATEGORY_NETWORK": (
        "omnibase_core.models.context.model_error_metadata",
        "CATEGORY_NETWORK",
    ),
    "CATEGORY_SYSTEM": (
        "omnibase_core.models.context.model_error_metadata",
        "CATEGORY_SYSTEM",
    ),
    "CATEGORY_VALIDATION": (
        "omnibase_core.models.context.model_error_metadata",
        "CATEGORY_VALIDATION",
    ),
    "CLIENT_ERROR_CATEGORIES": (
        "omnibase_core.models.context.model_error_metadata",
        "CLIENT_ERROR_CATEGORIES",
    ),
    "SERVER_ERROR_CATEGORIES": (
        "omnibase_core.models.context.model_error_metadata",
        "SERVER_ERROR_CATEGORIES",
    ),
    "ModelErrorMetadata": (
        "omnibase_core.models.context.model_error_metadata",
        "ModelErrorMetadata",
    ),
    "ModelGraphSnapshot": (
        "omnibase_core.models.context.model_graph_snapshot",
        "ModelGraphSnapshot",
    ),
    "ModelHttpRequestMetadata": (
        "omnibase_core.models.context.model_http_request_metadata",
        "ModelHttpRequestMetadata",
    ),
    "ModelKnowledgeContextBundle": (
        "omnibase_core.models.context.model_knowledge_context_bundle",
        "ModelKnowledgeContextBundle",
    ),
    "ModelLearningMatch": (
        "omnibase_core.models.context.model_learning_match",
        "ModelLearningMatch",
    ),
    "ModelMetricsContext": (
        "omnibase_core.models.context.model_metrics_context",
        "ModelMetricsContext",
    ),
    "ModelNodeInitMetadata": (
        "omnibase_core.models.context.model_node_init_metadata",
        "ModelNodeInitMetadata",
    ),
    "ModelOperationalContext": (
        "omnibase_core.models.context.model_operational_context",
        "ModelOperationalContext",
    ),
    "ModelReducerIntentPayload": (
        "omnibase_core.models.context.model_reducer_intent_payload",
        "ModelReducerIntentPayload",
    ),
    "ModelResourceContext": (
        "omnibase_core.models.context.model_resource_context",
        "ModelResourceContext",
    ),
    "ModelRetryContext": (
        "omnibase_core.models.context.model_retry_context",
        "ModelRetryContext",
    ),
    "ModelErrorContext": (
        "omnibase_core.models.context.model_retry_error_context",
        "ModelErrorContext",
    ),
    "VALID_LOAD_BALANCE_STRATEGIES": (
        "omnibase_core.models.context.model_routing_metadata",
        "VALID_LOAD_BALANCE_STRATEGIES",
    ),
    "LoadBalanceStrategy": (
        "omnibase_core.models.context.model_routing_metadata",
        "LoadBalanceStrategy",
    ),
    "ModelRoutingMetadata": (
        "omnibase_core.models.context.model_routing_metadata",
        "ModelRoutingMetadata",
    ),
    "ModelRuntimeDirectivePayload": (
        "omnibase_core.models.context.model_runtime_directive_payload",
        "ModelRuntimeDirectivePayload",
    ),
    "ModelServiceDiscoveryMetadata": (
        "omnibase_core.models.context.model_service_discovery_metadata",
        "ModelServiceDiscoveryMetadata",
    ),
    "ModelSessionContext": (
        "omnibase_core.models.context.model_session_context",
        "ModelSessionContext",
    ),
    "ModelTraceContext": (
        "omnibase_core.models.context.model_trace_context",
        "ModelTraceContext",
    ),
    "ModelUserContext": (
        "omnibase_core.models.context.model_user_context",
        "ModelUserContext",
    ),
    "ModelValidationContext": (
        "omnibase_core.models.context.model_validation_context",
        "ModelValidationContext",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
