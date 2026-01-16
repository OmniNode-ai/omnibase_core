"""Domain-level outcome of dual registration.

This module provides ModelDualRegistrationOutcome, a pure domain model representing
the logical result of registering a node to both Consul and PostgreSQL. This is a
PURE domain model - it does NOT include infrastructure concerns like timing,
retries, or telemetry.

Design Pattern:
    ModelDualRegistrationOutcome is the return type from Effect nodes that perform
    dual registration. It captures the outcome of both registration operations
    in a single, immutable model.

    The model follows these principles:
    - **Domain Purity**: Only captures domain-level outcomes, no infra concerns
    - **Atomic Result**: Single model represents outcome of dual operation
    - **Error Transparency**: Clear error fields when operations fail
    - **Correlation**: Links to originating request via correlation_id

Outcome States:
    The `status` field represents the overall outcome:
    - "success": Both Postgres and Consul registration succeeded
    - "partial": One succeeded, one failed (check individual flags)
    - "failed": Both registration attempts failed

Data Flow:
    ```
    ┌──────────────────────────────────────────────────────────────────┐
    │                   Registration Outcome Flow                       │
    ├──────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │   Effect Node                                 Orchestrator       │
    │       │                                            │             │
    │       │   register to Postgres                     │             │
    │       │   register to Consul                       │             │
    │       │                                            │             │
    │       │   create DualRegistrationOutcome           │             │
    │       │───────────────────────────────────────────>│             │
    │       │                                            │ aggregate   │
    │       │                                            │ outcomes    │
    │                                                                  │
    └──────────────────────────────────────────────────────────────────┘
    ```

Thread Safety:
    ModelDualRegistrationOutcome is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.registration import ModelDualRegistrationOutcome
    >>>
    >>> # Successful dual registration
    >>> outcome = ModelDualRegistrationOutcome(
    ...     node_id=uuid4(),
    ...     status="success",
    ...     postgres_applied=True,
    ...     consul_applied=True,
    ...     correlation_id=uuid4(),
    ... )
    >>>
    >>> # Partial failure (Postgres succeeded, Consul failed)
    >>> partial = ModelDualRegistrationOutcome(
    ...     node_id=uuid4(),
    ...     status="partial",
    ...     postgres_applied=True,
    ...     consul_applied=False,
    ...     consul_error="Connection timeout",
    ...     correlation_id=uuid4(),
    ... )

See Also:
    omnibase_core.models.registration.ModelRegistrationPayload: Input payload
    omnibase_core.nodes.NodeEffect: Effect nodes that produce this outcome
    omnibase_core.nodes.NodeOrchestrator: Orchestrator that aggregates outcomes
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelDualRegistrationOutcome(BaseModel):
    """Domain-level outcome of dual registration.

    This is a PURE domain model representing the logical result of
    registering a node to both Consul and PostgreSQL. It does NOT
    include infrastructure concerns (timing, retries, telemetry).

    This model is used by:
    - Effect nodes (return this after performing registration)
    - Orchestrator nodes (aggregate multiple outcomes)

    Attributes:
        node_id: The node that was registered (or attempted).
        status: Overall outcome status ("success", "partial", "failed").
        postgres_applied: Whether PostgreSQL registration succeeded.
        consul_applied: Whether Consul registration succeeded.
        postgres_error: Error message if PostgreSQL registration failed.
        consul_error: Error message if Consul registration failed.
        correlation_id: Correlation ID for distributed tracing.

    Example:
        >>> from uuid import uuid4
        >>>
        >>> # Complete success
        >>> success = ModelDualRegistrationOutcome(
        ...     node_id=uuid4(),
        ...     status="success",
        ...     postgres_applied=True,
        ...     consul_applied=True,
        ...     correlation_id=uuid4(),
        ... )
        >>>
        >>> # Complete failure
        >>> failure = ModelDualRegistrationOutcome(
        ...     node_id=uuid4(),
        ...     status="failed",
        ...     postgres_applied=False,
        ...     consul_applied=False,
        ...     postgres_error="Database connection refused",
        ...     consul_error="Service unavailable",
        ...     correlation_id=uuid4(),
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # ---- Identity ----
    node_id: UUID = Field(
        ...,
        description="The node that was registered (or attempted).",
    )

    # ---- Overall Status ----
    status: Literal["success", "partial", "failed"] = Field(
        ...,
        description=(
            "Overall outcome status. 'success' means both operations succeeded, "
            "'partial' means one succeeded and one failed, 'failed' means both failed."
        ),
    )

    # ---- Individual Operation Results ----
    postgres_applied: bool = Field(
        ...,
        description="Whether PostgreSQL registration succeeded.",
    )
    consul_applied: bool = Field(
        ...,
        description="Whether Consul registration succeeded.",
    )

    # ---- Error Information ----
    postgres_error: str | None = Field(
        default=None,
        description="Error message if PostgreSQL registration failed (max 2000 characters).",
        max_length=2000,
    )
    consul_error: str | None = Field(
        default=None,
        description="Error message if Consul registration failed (max 2000 characters).",
        max_length=2000,
    )

    # ---- Tracing ----
    correlation_id: UUID = Field(
        ...,
        description=(
            "Correlation ID for distributed tracing. Links this outcome "
            "to the originating request."
        ),
    )

    @model_validator(mode="after")
    def validate_status_consistency(self) -> ModelDualRegistrationOutcome:
        """Validate that status field matches the applied flags.

        This validator enforces domain invariants for the three possible status values:

        1. status="success": Requires BOTH postgres_applied=True AND consul_applied=True
           - Complete success means both operations succeeded
           - Cannot have success status if either operation failed

        2. status="failed": Requires BOTH postgres_applied=False AND consul_applied=False
           - Complete failure means both operations failed
           - Cannot have failed status if either operation succeeded

        3. status="partial": Requires EXACTLY ONE operation to succeed (XOR condition)
           - Partial means one succeeded and one failed
           - Cannot have partial if both succeeded or both failed

        These invariants ensure the model cannot be constructed in an inconsistent state,
        preventing bugs where status doesn't match the actual operation outcomes.

        Returns:
            Self after validation passes.

        Raises:
            ValueError: If status doesn't match the applied flags.

        Example:
            >>> from uuid import uuid4
            >>>
            >>> # Valid: status="success" with both operations succeeded
            >>> ModelDualRegistrationOutcome(
            ...     node_id=uuid4(),
            ...     status="success",
            ...     postgres_applied=True,
            ...     consul_applied=True,
            ...     correlation_id=uuid4(),
            ... )
            >>>
            >>> # Invalid: status="success" but Consul failed
            >>> ModelDualRegistrationOutcome(
            ...     node_id=uuid4(),
            ...     status="success",  # Will raise ValueError
            ...     postgres_applied=True,
            ...     consul_applied=False,
            ...     correlation_id=uuid4(),
            ... )
            Traceback (most recent call last):
                ...
            ValueError: status='success' requires both postgres_applied and consul_applied to be True
        """
        both_succeeded = self.postgres_applied and self.consul_applied
        both_failed = not self.postgres_applied and not self.consul_applied

        if self.status == "success" and not both_succeeded:
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(
                "status='success' requires both postgres_applied and consul_applied to be True"
            )
        if self.status == "failed" and not both_failed:
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(
                "status='failed' requires both postgres_applied and consul_applied to be False"
            )
        if self.status == "partial" and (both_succeeded or both_failed):
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(
                "status='partial' requires exactly one operation to succeed"
            )

        return self


__all__ = ["ModelDualRegistrationOutcome"]
