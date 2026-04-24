# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Concurrency Contract Spec.

Contract-level concurrency requirements for node dispatch providing:
- Per-node maximum parallel invocation cap (``max_parallel``)
- Opt-in model registry concurrency coupling (``model_concurrency_aware``)

Declared via an optional ``concurrency:`` block on a node's ``contract.yaml``
and consumed by the runtime and model router when scheduling work.

Related:
    OMN-7839 (this model), OMN-7832 (GLM wiring),
    ``model_registry.yaml`` ``concurrency_limit`` field.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelConcurrencyContractSpec(BaseModel):
    """
    Contract-level concurrency requirements for a node.

    Declared under the ``concurrency:`` block of a node's ``contract.yaml``.
    The runtime and the model router read these fields when scheduling work
    so that nodes do not exceed their own parallelism cap and, optionally,
    respect the concurrency limits published by the model registry.

    Example:
        >>> spec = ModelConcurrencyContractSpec(
        ...     max_parallel=5,
        ...     model_concurrency_aware=True,
        ... )
        >>> spec.max_parallel
        5
        >>> spec.model_concurrency_aware
        True

    YAML form::

        concurrency:
          max_parallel: 5
          model_concurrency_aware: true
    """

    max_parallel: int = Field(
        default=1,
        description=(
            "Maximum number of concurrent invocations of this node that the "
            "runtime may dispatch at any given time. Must be >= 1."
        ),
        ge=1,
    )

    model_concurrency_aware: bool = Field(
        default=False,
        description=(
            "When true, the router will gate dispatched work by the target "
            "model's ``concurrency_limit`` as published in the model registry. "
            "When false, only ``max_parallel`` is enforced."
        ),
    )

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        validate_default=True,
    )
