# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Domain-level outcome of registration.

ModelDualRegistrationOutcome, a pure domain model representing
the logical result of registering a node. This is a
PURE domain model - it does NOT include infrastructure concerns like timing,
retries, or telemetry.

Design Pattern:
    ModelDualRegistrationOutcome is the return type from Effect nodes that perform
    registration. It captures the outcome of the registration operation
    in a single, immutable model.

    The model follows these principles:
    - **Domain Purity**: Only captures domain-level outcomes, no infra concerns
    - **Atomic Result**: Single model represents outcome of the operation
    - **Error Transparency**: Clear error fields when operations fail
    - **Correlation**: Links to originating request via correlation_id

Outcome States:
    The `status` field represents the overall outcome:
    - "success": PostgreSQL registration succeeded
    - "partial": Registration partially succeeded
    - "failed": Registration attempt failed

Data Flow:
    ```
    ┌──────────────────────────────────────────────────────────────────┐
    │                   Registration Outcome Flow                       │
    ├──────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │   Effect Node                                 Orchestrator       │
    │       │                                            │             │
    │       │   register to Postgres                     │             │
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
    >>> # Successful registration
    >>> outcome = ModelDualRegistrationOutcome(
    ...     node_id=uuid4(),
    ...     status="success",
    ...     postgres_applied=True,
    ...     correlation_id=uuid4(),
    ... )
    >>>
    >>> # Failed registration
    >>> failure = ModelDualRegistrationOutcome(
    ...     node_id=uuid4(),
    ...     status="failed",
    ...     postgres_applied=False,
    ...     postgres_error="Database connection refused",
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
    """Domain-level outcome of registration.

    This is a PURE domain model representing the logical result of
    registering a node. It does NOT include infrastructure concerns
    (timing, retries, telemetry).

    This model is used by:
    - Effect nodes (return this after performing registration)
    - Orchestrator nodes (aggregate multiple outcomes)

    Attributes:
        node_id: The node that was registered (or attempted).
        status: Overall outcome status ("success", "partial", "failed").
        postgres_applied: Whether PostgreSQL registration succeeded.
        postgres_error: Error message if PostgreSQL registration failed.
        correlation_id: Correlation ID for distributed tracing.

    Example:
        >>> from uuid import uuid4
        >>>
        >>> # Complete success
        >>> success = ModelDualRegistrationOutcome(
        ...     node_id=uuid4(),
        ...     status="success",
        ...     postgres_applied=True,
        ...     correlation_id=uuid4(),
        ... )
        >>>
        >>> # Complete failure
        >>> failure = ModelDualRegistrationOutcome(
        ...     node_id=uuid4(),
        ...     status="failed",
        ...     postgres_applied=False,
        ...     postgres_error="Database connection refused",
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
            "Overall outcome status. 'success' means the operation succeeded, "
            "'partial' means partially succeeded, 'failed' means it failed."
        ),
    )

    # ---- Individual Operation Results ----
    postgres_applied: bool = Field(
        ...,
        description="Whether PostgreSQL registration succeeded.",
    )

    # ---- Error Information ----
    postgres_error: str | None = Field(
        default=None,
        description="Error message if PostgreSQL registration failed (max 2000 characters).",
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

        1. status="success": Requires postgres_applied=True
           - Complete success means the operation succeeded

        2. status="failed": Requires postgres_applied=False
           - Complete failure means the operation failed

        3. status="partial": Cannot have both all-succeeded or all-failed

        Returns:
            Self after validation passes.

        Raises:
            ValueError: If status doesn't match the applied flags.

        Example:
            >>> from uuid import uuid4
            >>>
            >>> # Valid: status="success" with operation succeeded
            >>> ModelDualRegistrationOutcome(
            ...     node_id=uuid4(),
            ...     status="success",
            ...     postgres_applied=True,
            ...     correlation_id=uuid4(),
            ... )
            >>>
            >>> # Invalid: status="success" but postgres failed
            >>> ModelDualRegistrationOutcome(
            ...     node_id=uuid4(),
            ...     status="success",  # Will raise ValueError
            ...     postgres_applied=False,
            ...     correlation_id=uuid4(),
            ... )
            Traceback (most recent call last):
                ...
            ValueError: status='success' requires postgres_applied to be True
        """
        if self.status == "success" and not self.postgres_applied:
            # error-ok: Pydantic validator requires ValueError
            raise ValueError("status='success' requires postgres_applied to be True")
        if self.status == "failed" and self.postgres_applied:
            # error-ok: Pydantic validator requires ValueError
            raise ValueError("status='failed' requires postgres_applied to be False")

        return self


__all__ = ["ModelDualRegistrationOutcome"]
