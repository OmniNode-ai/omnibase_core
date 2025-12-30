# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Handler Contract Model for ONEX Framework.

This module defines ModelHandlerContract, the foundational contract model
that defines handler capabilities, commands, security, and packaging metadata.
It enables contract-driven handler discovery and registration.

Core Design Decisions:
    1. Single execute pattern: Handlers have one entry point `execute(input, ctx) -> output`
    2. Descriptor embedded: Runtime semantics live in `descriptor` field
    3. Capability-based deps: No vendor names in contracts (use capability + requirements)
    4. Profile integration: Contracts can extend profiles for default descriptor values

Three-Layer Architecture:
    1. Profile (ModelExecutionProfile): Resource allocation, execution environment
    2. Descriptor (ModelHandlerBehaviorDescriptor): Handler behavior configuration
    3. Contract (this model): Full declarative handler specification

Example:
    >>> contract = ModelHandlerContract(
    ...     handler_id="node.user.reducer",
    ...     name="User Registration Reducer",
    ...     version="1.0.0",
    ...     descriptor=ModelHandlerBehaviorDescriptor(
    ...         handler_kind="reducer",
    ...         purity="side_effecting",
    ...         idempotent=True,
    ...     ),
    ...     input_model="omnibase_core.models.events.ModelUserRegistrationEvent",
    ...     output_model="omnibase_core.models.results.ModelUserState",
    ... )

See Also:
    - OMN-1117: Handler Contract Model & YAML Schema
    - ModelHandlerBehaviorDescriptor: Runtime behavior configuration
    - ModelCapabilityDependency: Vendor-agnostic capability dependencies
    - ModelExecutionConstraints: Execution ordering constraints

.. versionadded:: 0.4.1
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.contracts.model_execution_constraints import (
    ModelExecutionConstraints,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.model_handler_behavior_descriptor import (
    ModelHandlerBehaviorDescriptor,
)


class ModelHandlerContract(BaseModel):
    """
    Complete handler contract - the authoring surface for ONEX handlers.

    The handler contract is the declarative specification that defines:
    - What the handler does (descriptor)
    - What capabilities it needs (capability_inputs)
    - What it provides (capability_outputs)
    - How it fits in execution order (execution_constraints)
    - What it accepts and returns (input_model, output_model)

    Identity Fields:
        - handler_id: Unique identifier for registry lookup
        - name: Human-readable display name
        - version: Semantic version string
        - description: Optional detailed description

    Behavior Configuration:
        - descriptor: Embedded ModelHandlerBehaviorDescriptor for runtime semantics

    Capability Dependencies:
        - capability_inputs: Required input capabilities (vendor-agnostic)
        - capability_outputs: Provided output capabilities

    Execution:
        - input_model: Fully qualified input model reference
        - output_model: Fully qualified output model reference
        - execution_constraints: Ordering constraints (requires_before/after)

    Lifecycle:
        - supports_lifecycle: Handler implements lifecycle hooks
        - supports_health_check: Handler implements health checking
        - supports_provisioning: Handler can be provisioned/deprovisioned

    Attributes:
        handler_id: Unique identifier (e.g., "node.user.reducer").
        name: Human-readable name (e.g., "User Registration Reducer").
        version: Semantic version string (e.g., "1.0.0").
        description: Optional detailed description.
        descriptor: Embedded behavior descriptor (purity, idempotency, etc.).
        capability_inputs: List of required input capabilities.
        capability_outputs: List of provided output capability names.
        input_model: Fully qualified input model reference.
        output_model: Fully qualified output model reference.
        execution_constraints: Ordering constraints for execution.
        supports_lifecycle: Handler implements lifecycle hooks.
        supports_health_check: Handler implements health checking.
        supports_provisioning: Handler supports provisioning.
        tags: Optional tags for categorization and discovery.
        metadata: Optional additional metadata.

    Example:
        >>> # Reducer handler contract
        >>> contract = ModelHandlerContract(
        ...     handler_id="node.user.reducer",
        ...     name="User Registration Reducer",
        ...     version="1.0.0",
        ...     descriptor=ModelHandlerBehaviorDescriptor(
        ...         handler_kind="reducer",
        ...         purity="side_effecting",
        ...         idempotent=True,
        ...         timeout_ms=30000,
        ...     ),
        ...     capability_inputs=[
        ...         ModelCapabilityDependency(
        ...             alias="db",
        ...             capability="database.relational",
        ...             requirements=ModelRequirementSet(
        ...                 must={"supports_transactions": True},
        ...             ),
        ...         ),
        ...     ],
        ...     input_model="myapp.models.UserRegistrationEvent",
        ...     output_model="myapp.models.UserState",
        ... )

        >>> # Effect handler contract
        >>> effect_contract = ModelHandlerContract(
        ...     handler_id="handler.email.sender",
        ...     name="Email Sender",
        ...     version="2.0.0",
        ...     descriptor=ModelHandlerBehaviorDescriptor(
        ...         handler_kind="effect",
        ...         purity="side_effecting",
        ...         idempotent=False,
        ...     ),
        ...     capability_outputs=["notification.email"],
        ...     input_model="myapp.models.EmailRequest",
        ...     output_model="myapp.models.EmailResult",
        ...     supports_health_check=True,
        ... )

    Thread Safety:
        This model is immutable (frozen=True) and safe for concurrent access.

    See Also:
        - ModelHandlerBehaviorDescriptor: Runtime behavior configuration
        - ModelCapabilityDependency: Capability dependency specification
        - ModelExecutionConstraints: Execution ordering constraints
    """

    # ==========================================================================
    # Identity
    # ==========================================================================

    handler_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Unique identifier for registry lookup (e.g., 'node.user.reducer')",
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Human-readable display name",
    )

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$",
        description="Semantic version string (e.g., '1.0.0', '1.0.0-beta.1')",
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional detailed description of the handler",
    )

    # ==========================================================================
    # Embedded Descriptor (runtime semantics)
    # ==========================================================================

    descriptor: ModelHandlerBehaviorDescriptor = Field(
        ...,
        description="Embedded behavior descriptor defining runtime semantics",
    )

    # ==========================================================================
    # Capability Dependencies (vendor-agnostic)
    # ==========================================================================

    capability_inputs: list[ModelCapabilityDependency] = Field(
        default_factory=list,
        description="Required input capabilities (vendor-agnostic requirements)",
    )

    capability_outputs: list[str] = Field(
        default_factory=list,
        description="Provided output capability names (e.g., ['event.user_created'])",
    )

    # ==========================================================================
    # Execution
    # ==========================================================================

    input_model: str = Field(
        ...,
        min_length=1,
        description="Fully qualified input model reference (e.g., 'myapp.models.Input')",
    )

    output_model: str = Field(
        ...,
        min_length=1,
        description="Fully qualified output model reference (e.g., 'myapp.models.Output')",
    )

    execution_constraints: ModelExecutionConstraints | None = Field(
        default=None,
        description="Execution ordering constraints (requires_before/after)",
    )

    # ==========================================================================
    # Lifecycle
    # ==========================================================================

    supports_lifecycle: bool = Field(
        default=False,
        description="Handler implements lifecycle hooks (init/shutdown)",
    )

    supports_health_check: bool = Field(
        default=False,
        description="Handler implements health checking",
    )

    supports_provisioning: bool = Field(
        default=False,
        description="Handler can be provisioned/deprovisioned dynamically",
    )

    # ==========================================================================
    # Optional Metadata
    # ==========================================================================

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and discovery",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for extensibility",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @field_validator("handler_id")
    @classmethod
    def validate_handler_id_format(cls, v: str) -> str:
        """
        Validate handler_id uses dot-notation with valid segments.

        Args:
            v: The handler_id string.

        Returns:
            The validated handler_id.

        Raises:
            ValueError: If format is invalid.
        """
        if not v or not v.strip():
            raise ValueError("handler_id cannot be empty")

        segments = v.split(".")
        if len(segments) < 2:
            raise ValueError(
                f"handler_id '{v}' must have at least 2 segments (e.g., 'node.name')"
            )

        for segment in segments:
            if not segment:
                raise ValueError(f"handler_id '{v}' contains empty segment")
            if not segment[0].isalpha() and segment[0] != "_":
                raise ValueError(
                    f"handler_id segment '{segment}' must start with letter or underscore"
                )

        return v

    @field_validator("capability_inputs")
    @classmethod
    def validate_unique_aliases(
        cls, v: list[ModelCapabilityDependency]
    ) -> list[ModelCapabilityDependency]:
        """
        Validate that capability input aliases are unique.

        Args:
            v: List of capability dependencies.

        Returns:
            The validated list.

        Raises:
            ValueError: If duplicate aliases found.
        """
        if not v:
            return v

        aliases = [dep.alias for dep in v]
        if len(aliases) != len(set(aliases)):
            duplicates = [a for a in aliases if aliases.count(a) > 1]
            raise ValueError(f"Duplicate capability input aliases: {set(duplicates)}")

        return v

    @model_validator(mode="after")
    def validate_descriptor_handler_kind_consistency(self) -> "ModelHandlerContract":
        """
        Validate that handler_id prefix is consistent with descriptor.handler_kind.

        Returns:
            The validated contract.

        Raises:
            ModelOnexError: If there's a mismatch between ID prefix and handler kind.
        """
        # Extract first segment of handler_id
        prefix = self.handler_id.split(".")[0].lower()

        # Map common prefixes to handler kinds
        prefix_to_kind = {
            "node": None,  # Generic, any kind allowed
            "handler": None,  # Generic, any kind allowed
            "compute": "compute",
            "effect": "effect",
            "reducer": "reducer",
            "orchestrator": "orchestrator",
        }

        expected_kind = prefix_to_kind.get(prefix)

        # Only validate if prefix implies a specific kind
        if expected_kind is not None and self.descriptor.handler_kind != expected_kind:
            raise ModelOnexError(
                message=(
                    f"Handler ID prefix '{prefix}' implies handler_kind='{expected_kind}' "
                    f"but descriptor has handler_kind='{self.descriptor.handler_kind}'"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                handler_id=self.handler_id,
                expected_kind=expected_kind,
                actual_kind=self.descriptor.handler_kind,
            )

        return self

    def get_capability_aliases(self) -> list[str]:
        """
        Get all capability input aliases.

        Returns:
            List of alias names for capability inputs.
        """
        return [dep.alias for dep in self.capability_inputs]

    def get_required_capabilities(self) -> list[str]:
        """
        Get all required (strict=True) capability names.

        Returns:
            List of capability names that are required.
        """
        return [dep.capability for dep in self.capability_inputs if dep.strict]

    def get_optional_capabilities(self) -> list[str]:
        """
        Get all optional (strict=False) capability names.

        Returns:
            List of capability names that are optional.
        """
        return [dep.capability for dep in self.capability_inputs if not dep.strict]

    def has_execution_constraints(self) -> bool:
        """
        Check if this contract has execution ordering constraints.

        Returns:
            True if execution_constraints is set and has ordering requirements.
        """
        return (
            self.execution_constraints is not None
            and self.execution_constraints.has_ordering_constraints()
        )


__all__ = [
    "ModelHandlerContract",
]
