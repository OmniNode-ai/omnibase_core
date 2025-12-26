# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Context models for typed Generic[TContext] patterns.

This module provides reusable typed context models for use as type parameters
in generic models like ModelErrorDetails[TContext].

Available Context Models:
    - ModelTraceContext: Distributed tracing and correlation
    - ModelOperationalContext: Operation-level metadata
    - ModelRetryContext: Retry-related metadata
    - ModelResourceContext: Resource identification
    - ModelUserContext: User and session tracking
    - ModelValidationContext: Field-level validation details

Thread Safety:
    All context models are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.

Example:
    Using context models with Generic patterns::

        from omnibase_core.models.context import (
            ModelTraceContext,
            ModelOperationalContext,
            ModelRetryContext,
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
"""

from omnibase_core.models.context.model_operational_context import (
    ModelOperationalContext,
)
from omnibase_core.models.context.model_resource_context import ModelResourceContext
from omnibase_core.models.context.model_retry_context import ModelRetryContext
from omnibase_core.models.context.model_trace_context import ModelTraceContext
from omnibase_core.models.context.model_user_context import ModelUserContext
from omnibase_core.models.context.model_validation_context import ModelValidationContext

__all__ = [
    "ModelOperationalContext",
    "ModelResourceContext",
    "ModelRetryContext",
    "ModelTraceContext",
    "ModelUserContext",
    "ModelValidationContext",
]
