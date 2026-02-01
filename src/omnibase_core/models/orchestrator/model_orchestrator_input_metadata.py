"""
Typed metadata model for orchestrator input.

This module provides ModelOrchestratorInputMetadata which replaces the
untyped dict[str, ModelSchemaValue] pattern in ModelOrchestratorInput
with strongly-typed fields for full type safety and IDE support.

Thread Safety:
    ModelOrchestratorInputMetadata is mutable (frozen=False) as input
    metadata may be modified during workflow execution preparation.
    Instances should not be shared across threads without synchronization.

Key Features:
    - Full type safety for all metadata fields
    - IDE autocomplete and type checking support
    - No dict-based escape hatches - all fields are explicitly typed
    - Based on actual usage audit of integration tests and documentation

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.orchestrator import (
    ...     ModelOrchestratorInputMetadata,
    ... )
    >>>
    >>> # Create metadata with tracing info
    >>> metadata = ModelOrchestratorInputMetadata(
    ...     source="api_gateway",
    ...     environment="production",
    ...     correlation_id=uuid4(),
    ...     trigger="start",
    ...     persist_result=True,
    ... )

See Also:
    - omnibase_core.models.orchestrator.model_orchestrator_input: Parent model
    - docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md: Tutorial
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelOrchestratorInputMetadata(BaseModel):
    """Typed metadata for orchestrator input.

    Replaces dict[str, ModelSchemaValue] with strongly-typed fields.
    All fields are based on actual usage audit of integration tests and docs.

    Attributes:
        source: Origin of the workflow request (e.g., "api_gateway", "scheduler").
        environment: Execution environment (e.g., "test", "staging", "prod").
        correlation_id: Request correlation ID for distributed tracing.
        trigger: FSM trigger for state transitions. Defaults to "process".
        persist_result: Whether to persist workflow results. Defaults to False.

    Example:
        >>> metadata = ModelOrchestratorInputMetadata(
        ...     source="scheduler",
        ...     environment="staging",
        ...     trigger="process",
        ... )
        >>> metadata.source
        'scheduler'
    """

    model_config = ConfigDict(
        frozen=False,  # Mutable - input metadata may be modified during execution
        extra="forbid",
        from_attributes=True,
    )

    # Observability/Tracing
    source: str | None = Field(
        default=None,
        description="Origin of the workflow request",
    )

    environment: str | None = Field(
        default=None,
        description="Execution environment (test, staging, prod)",
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Request correlation ID for distributed tracing",
    )

    # FSM Control
    trigger: str = Field(
        default="process",
        description="FSM trigger for state transitions",
    )

    # Persistence Control
    persist_result: bool = Field(
        default=False,
        description="Whether to persist workflow results",
    )


__all__ = ["ModelOrchestratorInputMetadata"]
