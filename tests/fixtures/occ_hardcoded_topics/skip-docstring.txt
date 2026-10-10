# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pydantic backing model for the hook prompt submitted contract.

Type-safe access to the hook prompt submitted configuration
defined in contract_hook_prompt_submitted.yaml. It replaces manual yaml.safe_load +
isinstance checks with validated Pydantic models.

The contract defines the ONEX node contract for the prompt submitted hook effect:
- Event bus configuration (Kafka topic, partition strategy)
- Runtime configuration (timeouts, side effects)
- Privacy settings (data minimization, preview length)
- I/O model references and capability definitions

Usage:
    >>> from omniclaude.hooks.contracts.contract_hook_prompt_submitted import (
    ...     HookPromptSubmittedContract,
    ... )
    >>> contract = HookPromptSubmittedContract.load()
    >>> print(contract.event_bus.topic_base)
    'onex.evt.omniclaude.prompt-submitted.v1'  # onex-topic-sot
    >>> print(contract.privacy.preview_max_length)
    100

See Also:
    - contract_hook_prompt_submitted.yaml for the source YAML contract
    - OMN-1399: Define Claude Code hooks schema for ONEX event emission
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omniclaude.hooks.contracts.contract_experiment_cohort import Metadata, Version
from omniclaude.hooks.contracts.contract_hook_tool_executed import (
    Capability,
    Dependency,
    EventBus,
    ModelReference,
    Runtime,
    TimestampPolicy,
)
from omniclaude.hooks.contracts.schema import ModelJsonSchemaDefinition

# =============================================================================
# Privacy Configuration (specific to prompt_submitted)
# =============================================================================


class Privacy(BaseModel):
    """Privacy configuration for data minimization.

    Defines privacy-preserving behavior for the hook, particularly for
    prompt content handling.

    Attributes:
        data_minimization: Whether to minimize data sent in events.
        preview_max_length: Maximum character length for prompt previews.
        pii_policy: Policy for handling PII ('exclude', 'redact', 'allow').
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    data_minimization: bool = Field(
        ...,
        description="Whether to minimize data sent in events",
    )
    preview_max_length: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Maximum character length for prompt previews",
    )
    pii_policy: Literal["exclude", "redact", "allow"] = Field(
        ...,
        description="Policy for handling PII ('exclude', 'redact', 'allow')",
    )


# =============================================================================
# Root Contract Model
# =============================================================================


class HookPromptSubmittedContract(BaseModel):
    """Root model for the hook prompt submitted contract.

    This model validates the entire contract_hook_prompt_submitted.yaml structure
    and provides type-safe access to all configuration values.

    Attributes:
        name: Contract name identifier.
        contract_name: Contract name (typically same as name).
        node_name: Node name for ONEX compatibility.
        version: Semantic version of the contract.
        node_version: Semantic version of the node implementation.
        node_type: ONEX node type (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR).
        description: Human-readable description of the node's purpose.
        input_model: Reference to the input Pydantic model.
        output_model: Reference to the output Pydantic model.
        event_bus: Kafka event bus configuration.
        runtime: Runtime execution configuration.
        timestamp_policy: Timestamp handling policy.
        privacy: Privacy configuration for data minimization.
        dependencies: List of node dependencies.
        capabilities: List of capabilities provided by the node.
        definitions: JSON Schema-like model definitions.
        metadata: Contract metadata for documentation and tracking.

    Example:
        >>> contract = HookPromptSubmittedContract.load()
        >>> contract.event_bus.topic_base
        'onex.evt.omniclaude.prompt-submitted.v1'  # onex-topic-sot
        >>> contract.privacy.preview_max_length
        100
        >>> contract.runtime.timeout_ms
        500
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    name: str = Field(
        ...,
        min_length=1,
        description="Contract name identifier",
    )
    contract_name: str = Field(
        ...,
        min_length=1,
        description="Contract name (typically same as name)",
    )
    node_name: str = Field(
        ...,
        min_length=1,
        description="Node name for ONEX compatibility",
    )
    contract_version: Version = Field(
        ...,
        description="Semantic version of the contract",
    )
    node_version: Version = Field(
        ...,
        description="Semantic version of the node implementation",
    )
    node_type: Literal[
        "EFFECT",
        "EFFECT_GENERIC",
        "COMPUTE",
        "COMPUTE_GENERIC",
        "REDUCER",
        "REDUCER_GENERIC",
        "ORCHESTRATOR",
        "ORCHESTRATOR_GENERIC",
    ] = Field(
        ...,
        description="ONEX node type",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of the node's purpose",
    )
    input_model: ModelReference = Field(
        ...,
        description="Reference to the input Pydantic model",
    )
    output_model: ModelReference = Field(
        ...,
        description="Reference to the output Pydantic model",
    )
    event_bus: EventBus = Field(
        ...,
        description="Kafka event bus configuration",
    )
    runtime: Runtime = Field(
        ...,
        description="Runtime execution configuration",
    )
    timestamp_policy: TimestampPolicy = Field(
        ...,
        description="Timestamp handling policy",
    )
    privacy: Privacy = Field(
        ...,
        description="Privacy configuration for data minimization",
    )
    dependencies: list[Dependency] = Field(
        ...,
        min_length=1,
        description="List of node dependencies",
    )
    capabilities: list[Capability] = Field(
        ...,
        min_length=1,
        description="List of capabilities provided by the node",
    )
    definitions: dict[str, ModelJsonSchemaDefinition] = Field(
        ...,
        description="JSON Schema-like model definitions",
    )
    metadata: Metadata = Field(
        ...,
        description="Contract metadata for documentation and tracking",
    )

    @classmethod
    def load(cls, path: Path | None = None) -> Self:
        """Load and validate the hook prompt submitted contract from YAML.

        Args:
            path: Optional path to the YAML contract file. If not provided,
                defaults to contract_hook_prompt_submitted.yaml in the same directory.

        Returns:
            Validated HookPromptSubmittedContract instance.

        Raises:
            FileNotFoundError: If the contract file does not exist.
            yaml.YAMLError: If the YAML is malformed.
            pydantic.ValidationError: If the contract fails validation.

        Example:
            >>> contract = HookPromptSubmittedContract.load()
            >>> contract.event_bus.topic_base
            'onex.evt.omniclaude.prompt-submitted.v1'  # onex-topic-sot
        """
        if path is None:
            path = Path(__file__).parent / "contract_hook_prompt_submitted.yaml"

        with open(path) as f:
            data: dict[str, object] = yaml.safe_load(f)

        return cls.model_validate(data)


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    # Re-exported shared models (for convenience)
    "Version",
    "Metadata",
    "ModelReference",
    "EventBus",
    "Runtime",
    "TimestampPolicy",
    "Dependency",
    "Capability",
    # New models specific to prompt_submitted
    "Privacy",
    # Root contract
    "HookPromptSubmittedContract",
    # Re-export from shared schema module for convenience
    "ModelJsonSchemaDefinition",
]
