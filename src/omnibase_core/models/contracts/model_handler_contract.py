"""
Handler Contract Model for ONEX Framework.

This module defines ModelHandlerContract, the foundational contract model
that defines handler capabilities, commands, security, and packaging metadata.
It enables contract-driven handler discovery and registration.

Core Design Decisions:
    1. Single execute pattern: Handlers have one entry point `execute(input, ctx) -> output`
    2. Behavior embedded: Runtime semantics live in `descriptor` field
    3. Capability-based deps: No vendor names in contracts (use capability + requirements)
    4. Profile integration: Contracts can extend profiles for default behavior values

Three-Layer Architecture:
    1. Profile (ModelExecutionProfile): Resource allocation, execution environment
    2. Behavior (ModelHandlerBehavior): Handler behavior configuration
    3. Contract (this model): Full declarative handler specification

Example:
    >>> contract = ModelHandlerContract(
    ...     handler_id="node.user.reducer",
    ...     name="User Registration Reducer",
    ...     contract_version=ModelSemVer(major=1, minor=0, patch=0),
    ...     descriptor=ModelHandlerBehavior(
    ...         node_archetype="reducer",
    ...         purity="side_effecting",
    ...         idempotent=True,
    ...     ),
    ...     input_model="omnibase_core.models.events.ModelUserRegistrationEvent",
    ...     output_model="omnibase_core.models.results.ModelUserState",
    ... )

See Also:
    - OMN-1117: Handler Contract Model & YAML Schema
    - ModelHandlerBehavior: Runtime behavior configuration
    - ModelCapabilityDependency: Vendor-agnostic capability dependencies
    - ModelExecutionConstraints: Execution ordering constraints

.. versionadded:: 0.4.1
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_contract_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.contracts.model_execution_constraints import (
    ModelExecutionConstraints,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import (
    ModelHandlerBehavior,
)


class ModelHandlerContract(BaseModel):
    """
    Complete handler contract - the authoring surface for ONEX handlers.

    The handler contract is the declarative specification that defines:
    - What the handler does (behavior)
    - What capabilities it needs (capability_inputs)
    - What it provides (capability_outputs)
    - How it fits in execution order (execution_constraints)
    - What it accepts and returns (input_model, output_model)

    Identity Fields:
        - handler_id: Unique identifier for registry lookup
        - name: Human-readable display name
        - contract_version: Semantic version (ModelSemVer)
        - description: Optional detailed description

    Behavior Configuration:
        - descriptor: Embedded ModelHandlerBehavior for runtime semantics

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
        contract_version: Semantic version (ModelSemVer instance).
        description: Optional detailed description.
        descriptor: Embedded behavior configuration (purity, idempotency, etc.).
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
        ...     contract_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     descriptor=ModelHandlerBehavior(
        ...         node_archetype="reducer",
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
        ...     contract_version=ModelSemVer(major=2, minor=0, patch=0),
        ...     descriptor=ModelHandlerBehavior(
        ...         node_archetype="effect",
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
        - ModelHandlerBehavior: Runtime behavior configuration
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

    contract_version: ModelSemVer = Field(
        ...,
        description="Semantic version of this handler contract",
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional detailed description of the handler",
    )

    # ==========================================================================
    # Embedded Behavior (runtime semantics)
    # ==========================================================================

    descriptor: ModelHandlerBehavior = Field(
        ...,
        description="Embedded behavior configuration defining runtime semantics",
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

    # ONEX_EXCLUDE: dict_str_any - extensibility metadata for contract customization
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for extensibility",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

    @model_validator(mode="before")
    @classmethod
    def reject_deprecated_version_field(cls, data: Any) -> Any:
        """
        Reject deprecated 'version' field - use 'contract_version' instead.

        Args:
            data: Raw input data.

        Returns:
            Validated data.

        Raises:
            ModelOnexError: If deprecated 'version' field is present.
        """
        if isinstance(data, dict) and "version" in data:
            raise ModelOnexError(
                message=(
                    "Handler contracts must use 'contract_version', not 'version'. "
                    "The 'version' field was renamed per ONEX specification (OMN-1436)."
                ),
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            )
        return data

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
    def validate_descriptor_node_archetype_consistency(self) -> ModelHandlerContract:
        """
        Validate that handler_id prefix is consistent with descriptor.node_archetype.

        Returns:
            The validated contract.

        Raises:
            ModelOnexError: If there's a mismatch between ID prefix and node archetype.
        """
        # Extract first segment of handler_id
        prefix = self.handler_id.split(".")[0].lower()

        # Map common prefixes to node archetypes
        prefix_to_archetype = {
            "node": None,  # Generic, any archetype allowed
            "handler": None,  # Generic, any archetype allowed
            "compute": "compute",
            "effect": "effect",
            "reducer": "reducer",
            "orchestrator": "orchestrator",
        }

        expected_archetype = prefix_to_archetype.get(prefix)

        # Only validate if prefix implies a specific archetype
        if (
            expected_archetype is not None
            and self.descriptor.node_archetype != expected_archetype
        ):
            raise ModelOnexError(
                message=(
                    f"Handler ID prefix '{prefix}' implies node_archetype='{expected_archetype}' "
                    f"but descriptor has node_archetype='{self.descriptor.node_archetype}'"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                handler_id=self.handler_id,
                expected_archetype=expected_archetype,
                actual_archetype=str(self.descriptor.node_archetype),
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
