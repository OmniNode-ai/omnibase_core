# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Onboarding policy model for graph traversal.

Defines a traversal policy that describes a path through an onboarding graph.
Policies specify which capabilities are required at entry, which capabilities
are targeted, and constraints on the traversal (skip steps, time budget,
simulation/deferral flags).

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.orchestrator.model_onboarding_policy import (
    ...     ModelOnboardingPolicy,
    ... )
    >>> policy = ModelOnboardingPolicy(
    ...     policy_id=uuid4(),
    ...     policy_name="standalone_quickstart",
    ...     description="Minimal path to running a standalone node",
    ...     target_capabilities=["first_node_running"],
    ...     max_estimated_minutes=5,
    ... )
    >>> policy.policy_name
    'standalone_quickstart'
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelOnboardingPolicy(BaseModel):
    """Traversal policy for navigating an onboarding graph.

    Describes a path through the onboarding graph by specifying entry
    requirements, target capabilities, and traversal constraints.

    Attributes:
        policy_id: Unique identifier for this policy.
        policy_name: Human-readable policy name (e.g. "standalone_quickstart").
        description: Human-readable description of the policy's purpose.
        required_entry_capabilities: Capabilities the environment must
            already have before starting this policy.
        target_capabilities: Capabilities this policy aims to achieve.
        skip_steps: Step IDs to skip during traversal.
        max_estimated_minutes: Optional time budget for the policy.
        allow_simulation: Whether steps can be simulated rather than
            executed for real.
        allow_deferral: Whether steps can be deferred to a later run.
    """

    policy_id: UUID = Field(description="Unique policy identifier")
    policy_name: str = Field(description="Human-readable policy name")
    description: str = Field(description="Human-readable policy description")
    required_entry_capabilities: list[str] = Field(
        default_factory=list,
        description="Capabilities required before starting this policy",
    )
    target_capabilities: list[str] = Field(
        default_factory=list,
        description="Capabilities this policy aims to achieve",
    )
    skip_steps: list[str] = Field(
        default_factory=list,
        description="Step IDs to skip during traversal",
    )
    max_estimated_minutes: int | None = Field(
        default=None,
        description="Optional time budget in minutes",
    )
    allow_simulation: bool = Field(
        default=False,
        description="Whether steps can be simulated",
    )
    allow_deferral: bool = Field(
        default=False,
        description="Whether steps can be deferred to a later run",
    )


__all__ = ["ModelOnboardingPolicy"]
