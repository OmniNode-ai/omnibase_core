# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Handler Lifecycle Contract Model.

Declarative lifecycle configuration for ONEX handlers — capturing what lifecycle
phases a handler supports, its initialization order, teardown behavior, and
health check configuration.

This model is intentionally pure: it encodes no runtime resources, no handler
imports, and no implementation details. It provides a stable, machine-readable
schema for handler lifecycle registration and introspection.

Design Intent:
    HandlerHttp and HandlerKafka are preserved as monolithic handlers for MVP.
    However, their lifecycle configuration is currently implicit (embedded in
    __init__, startup hooks, and ad-hoc flags). Extracting it into this contract
    model:

    1. Makes lifecycle requirements explicit and machine-readable
    2. Enables future handler-as-nodes decomposition: a HandlerLifecycleContract
       becomes the declarative input to a future NodeHandlerLifecycleEffect
    3. Provides a stable schema for handler registration and introspection without
       depending on the concrete handler class

Scope:
    - Pure Pydantic model — no runtime resource references, no handler imports
    - No imports from concrete handler modules
    - Designed for composition with ModelHandlerContract

See Also:
    - OMN-4221: Extract HandlerLifecycleContract into omnibase_core
    - ModelHandlerContract: Full handler contract with behavior and capability deps
    - ModelLifecycleConfig: General node lifecycle configuration
    - RetryPolicyContract: Retry policy for handler lifecycle operations

.. versionadded:: 1.9.0
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_retry_policy_contract import (
    RetryPolicyContract,
)


class HandlerLifecycleContract(BaseModel):
    """
    Declarative lifecycle configuration for an ONEX handler.

    Captures the lifecycle surface of a handler — which phases it participates in,
    timeout configuration, warm-start capability, health check cadence, and retry
    policy — without referencing any runtime resources or concrete handler classes.

    This is the stable, machine-readable schema used for handler registration and
    introspection. It is the intended declarative input for a future
    ``NodeHandlerLifecycleEffect`` when handlers are decomposed into ONEX nodes.

    Fields:
        handler_id: Unique identifier matching the handler's registry key.
        handler_type: Transport/integration kind ('http', 'kafka', or custom label).
        supports_warm_start: Whether the handler can resume without full re-init.
        startup_timeout_seconds: Max time allowed for handler initialization.
        teardown_timeout_seconds: Max time allowed for graceful shutdown.
        health_check_interval_seconds: Cadence for health probes; None disables probing.
        retry_policy: Optional retry configuration for startup/teardown operations.

    Immutability:
        The model is frozen. Use ``model_copy(update={...})`` to derive variants.

    Example:
        >>> contract = HandlerLifecycleContract(
        ...     handler_id="handler.http.outbound",
        ...     handler_type="http",
        ...     supports_warm_start=True,
        ...     startup_timeout_seconds=15.0,
        ...     teardown_timeout_seconds=5.0,
        ...     health_check_interval_seconds=30.0,
        ...     retry_policy=RetryPolicyContract(max_retries=2),
        ... )

        >>> # Minimal contract — timeouts and retry use defaults
        >>> minimal = HandlerLifecycleContract(
        ...     handler_id="handler.kafka.consumer",
        ...     handler_type="kafka",
        ... )

    See Also:
        - OMN-4221: Extraction ticket
        - ModelHandlerContract: Full handler contract (behavior, capabilities, I/O)
        - ModelLifecycleConfig: General node lifecycle configuration
        - RetryPolicyContract: Retry policy for lifecycle operations
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

    handler_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description=(
            "Unique identifier for this handler, matching the registry key used in "
            "ModelHandlerContract.handler_id (e.g., 'handler.http.outbound')"
        ),
    )

    handler_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Transport or integration kind for this handler. "
            "Well-known values: 'http', 'kafka'. Custom labels are permitted."
        ),
    )

    supports_warm_start: bool = Field(
        default=False,
        description=(
            "Whether the handler supports warm-start: resuming from a suspended "
            "state without a full re-initialization cycle. "
            "Warm-start handlers skip resource re-acquisition on restart."
        ),
    )

    startup_timeout_seconds: float = Field(
        default=30.0,
        ge=0.1,
        le=600.0,
        description="Maximum time allowed for handler initialization in seconds",
    )

    teardown_timeout_seconds: float = Field(
        default=10.0,
        ge=0.1,
        le=300.0,
        description=(
            "Maximum time allowed for graceful handler shutdown in seconds. "
            "After this period the handler is forcibly terminated."
        ),
    )

    health_check_interval_seconds: float | None = Field(
        default=None,
        ge=1.0,
        le=3600.0,
        description=(
            "Cadence for periodic health probes in seconds. "
            "None disables active health probing for this handler."
        ),
    )

    retry_policy: RetryPolicyContract | None = Field(
        default=None,
        description=(
            "Optional retry configuration applied to startup and teardown operations. "
            "When None, the handler makes a single attempt with no retries."
        ),
    )


__all__ = ["HandlerLifecycleContract"]
