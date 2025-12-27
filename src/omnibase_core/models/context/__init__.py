# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Context models for typed Generic[TContext] patterns.

This module provides reusable typed context models for use as type parameters
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

# Error/Retry context models
# Effect context models
# Metadata context models
from omnibase_core.models.context.model_audit_metadata import ModelAuditMetadata
from omnibase_core.models.context.model_authorization_context import (
    ModelAuthorizationContext,
)
from omnibase_core.models.context.model_checkpoint_metadata import (
    ModelCheckpointMetadata,
)
from omnibase_core.models.context.model_detection_metadata import ModelDetectionMetadata
from omnibase_core.models.context.model_effect_input_data import (
    ModelEffectInputData,
)
from omnibase_core.models.context.model_http_request_metadata import (
    ModelHttpRequestMetadata,
)
from omnibase_core.models.context.model_node_init_metadata import ModelNodeInitMetadata
from omnibase_core.models.context.model_operational_context import (
    ModelOperationalContext,
)
from omnibase_core.models.context.model_reducer_intent_payload import (
    ModelReducerIntentPayload,
)
from omnibase_core.models.context.model_resource_context import ModelResourceContext
from omnibase_core.models.context.model_retry_context import ModelRetryContext
from omnibase_core.models.context.model_runtime_directive_payload import (
    ModelRuntimeDirectivePayload,
)
from omnibase_core.models.context.model_session_context import ModelSessionContext
from omnibase_core.models.context.model_trace_context import ModelTraceContext
from omnibase_core.models.context.model_user_context import ModelUserContext
from omnibase_core.models.context.model_validation_context import ModelValidationContext

__all__ = [
    # Error/Retry context models
    "ModelOperationalContext",
    "ModelResourceContext",
    "ModelRetryContext",
    "ModelRuntimeDirectivePayload",
    "ModelTraceContext",
    "ModelUserContext",
    "ModelValidationContext",
    # Effect context models
    "ModelEffectInputData",
    # Intent context models
    "ModelReducerIntentPayload",
    # Metadata context models
    "ModelAuditMetadata",
    "ModelAuthorizationContext",
    "ModelCheckpointMetadata",
    "ModelDetectionMetadata",
    "ModelHttpRequestMetadata",
    "ModelNodeInitMetadata",
    "ModelSessionContext",
]
