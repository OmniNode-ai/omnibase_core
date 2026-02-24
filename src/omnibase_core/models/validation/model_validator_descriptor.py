# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorDescriptor model — declares what a validator applies to and its constraints.

Part of the Generic Validator Node Architecture (OMN-2362).

The validator registry uses ValidatorDescriptor to match validators to targets
and enforce execution constraints without invoking the validator itself.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelValidatorDescriptor(BaseModel):
    """Declares what a validator applies to and its execution constraints.

    The validator registry reads this descriptor to determine:
    - Which scopes the validator handles.
    - Which ONEX contract types the validator can inspect.
    - Which tuple types the validator understands.
    - What runtime capabilities the validator requires.
    - Whether the validator is deterministic and idempotent.
    - How long the validator is allowed to run.

    Example:
        >>> descriptor = ModelValidatorDescriptor(
        ...     validator_id="naming_convention",
        ...     applicable_scopes=("file", "subtree"),
        ...     deterministic=True,
        ...     idempotent=True,
        ...     timeout_seconds=30,
        ... )
        >>> descriptor.validator_id
        'naming_convention'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    validator_id: str = Field(
        description=(
            "Unique identifier for this validator. "
            "Must be stable across releases; used as the primary key in the registry. "
            "Recommended format: lowercase snake_case, e.g. 'naming_convention'."
        ),
    )

    display_name: str | None = Field(
        default=None,
        description=(
            "Optional human-readable name for display in reports and tooling. "
            "Defaults to validator_id when not set."
        ),
    )

    description: str | None = Field(
        default=None,
        description="Brief description of what this validator checks.",
    )

    applicable_scopes: tuple[
        Literal["file", "subtree", "workspace", "artifact"], ...
    ] = Field(
        default=("file", "subtree", "workspace", "artifact"),
        description=(
            "Validation scopes this validator can handle. "
            "The registry uses this to filter validators for a given ValidationRequest. "
            "Defaults to all scopes when not restricted."
        ),
    )

    applicable_contract_types: tuple[str, ...] = Field(
        default=(),
        description=(
            "ONEX contract types this validator applies to, e.g. ('NodeContract',). "
            "Empty tuple means the validator applies regardless of contract type."
        ),
    )

    applicable_tuple_types: tuple[str, ...] = Field(
        default=(),
        description=(
            "ONEX tuple types this validator understands, e.g. ('ModelOnexNode',). "
            "Empty tuple means the validator applies regardless of tuple type."
        ),
    )

    required_capabilities: tuple[str, ...] = Field(
        default=(),
        description=(
            "Named capabilities the runtime must provide for this validator to run, "
            "e.g. ('filesystem', 'network'). "
            "The execution planner uses this to skip validators in constrained environments."
        ),
    )

    deterministic: bool = Field(
        default=True,
        description=(
            "True if the validator always produces the same findings for the same input. "
            "Non-deterministic validators (e.g. those that call external services) "
            "should set this to False to opt out of result caching."
        ),
    )

    idempotent: bool = Field(
        default=True,
        description=(
            "True if running the validator multiple times on the same input "
            "produces the same side effects as running it once. "
            "Validators that mutate external state must set this to False."
        ),
    )

    timeout_seconds: int | None = Field(
        default=None,
        description=(
            "Maximum wall-clock seconds the validator is allowed to run. "
            "None means no timeout enforced by the execution planner. "
            "Individual runners may apply their own hard limits regardless."
        ),
        ge=1,
    )

    tags: tuple[str, ...] = Field(
        default=(),
        description=(
            "Arbitrary tags for filtering via ValidationRequest.tag_filters. "
            "Examples: ('style', 'security', 'performance')."
        ),
    )

    version: str | None = Field(
        default=None,
        description=(
            "Optional semver string for the validator implementation. "
            "Included in ValidationReport provenance for audit purposes."
        ),
    )


__all__ = ["ModelValidatorDescriptor"]
