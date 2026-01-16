"""
Model Dependency Specification for Capability-Based Dependencies.

This module defines ModelDependencySpec, which declares dependencies by
capability/intent/protocol rather than hardcoded module paths. This enables
auto-discovery and loose coupling between nodes using the principle:
"I'm interested in what you do, not what you are."

The model supports three discovery methods:
- capability: Match by capability string (e.g., "event.publishing")
- intent_types: Match by handled intent types (e.g., ["consul.register"])
- protocol: Match by protocol interface (e.g., "ProtocolReducer")

At least one discovery method must be specified for the dependency to be valid.

Example:
    >>> spec = ModelDependencySpec(
    ...     name="event_bus",
    ...     type="protocol",
    ...     capability="event.publishing",
    ...     selection_strategy="round_robin",
    ... )
    >>> spec.has_capability_filter()
    True

See Also:
    - OMN-1123: ModelDependencySpec (Capability-Based Dependencies)
    - ONEX Four-Node Architecture documentation
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Type aliases for Literal types
DependencyType = Literal[  # enum-ok: model type annotation
    "node", "protocol", "handler"
]
SelectionStrategy = Literal[  # enum-ok: model type annotation
    "first", "random", "round_robin", "least_loaded"
]


class ModelDependencySpec(BaseModel):
    """
    Capability-based dependency specification for ONEX nodes.

    Declares dependencies by capability/intent/protocol rather than hardcoded
    module paths, enabling auto-discovery and loose coupling between nodes.

    Core Principle:
        "I'm interested in what you do, not what you are."

    Discovery Methods (at least one required):
        - capability: Match by capability string
        - intent_types: Match by handled intent types
        - protocol: Match by protocol interface

    Filters:
        - contract_type: Filter by node type (effect, compute, reducer, orchestrator)
        - state: Filter by registration state (default: ACTIVE)

    Selection:
        - selection_strategy: How to select when multiple matches found

    Fallback:
        - fallback_module: Module to use if capability-based discovery fails

    Attributes:
        name: Reference name used in code to access the resolved dependency.
        type: Type of dependency (node, protocol, handler).
        capability: Capability string for discovery (e.g., "consul.registration").
        intent_types: List of intent types for discovery (e.g., ["consul.register"]).
        protocol: Protocol interface name for discovery (e.g., "ProtocolReducer").
        contract_type: Filter by contract type (effect, compute, reducer, orchestrator).
        state: Filter by registration state (default: "ACTIVE").
        selection_strategy: Strategy for selecting among multiple matches.
        fallback_module: Fallback module path if capability discovery fails.
        description: Human-readable description of the dependency.

    Example:
        >>> # Dependency by capability
        >>> spec = ModelDependencySpec(
        ...     name="event_bus",
        ...     type="protocol",
        ...     capability="event.publishing",
        ... )

        >>> # Dependency by intent types
        >>> spec = ModelDependencySpec(
        ...     name="consul_handler",
        ...     type="handler",
        ...     intent_types=["consul.register", "consul.deregister"],
        ... )

        >>> # Dependency by protocol with fallback
        >>> spec = ModelDependencySpec(
        ...     name="reducer",
        ...     type="node",
        ...     protocol="ProtocolReducer",
        ...     fallback_module="omnibase_core.nodes.default_reducer",
        ... )

    Raises:
        ModelOnexError: If none of capability, intent_types, or protocol is specified.
        ValidationError: If type or selection_strategy has invalid value.
    """

    name: str = Field(
        ...,
        description="Reference name used in code to access the resolved dependency",
        min_length=1,
    )

    type: DependencyType = Field(
        ...,
        description="Type of dependency: node, protocol, or handler",
    )

    # Capability-based discovery (at least one must be specified)
    capability: str | None = Field(
        default=None,
        description="Capability string for discovery (e.g., 'consul.registration')",
    )

    intent_types: list[str] | None = Field(
        default=None,
        description="List of intent types for discovery (e.g., ['consul.register'])",
    )

    protocol: str | None = Field(
        default=None,
        description="Protocol interface name for discovery (e.g., 'ProtocolReducer')",
    )

    # Filters
    contract_type: str | None = Field(
        default=None,
        description="Filter by contract type: effect, compute, reducer, orchestrator",
    )

    state: str = Field(
        default="ACTIVE",
        description="Filter by registration state (default: ACTIVE)",
    )

    # Selection strategy (when multiple matches)
    selection_strategy: SelectionStrategy = Field(
        default="first",
        description="Strategy for selecting among multiple matches: first, random, round_robin, least_loaded",
    )

    # Fallback (if capability not found)
    fallback_module: str | None = Field(
        default=None,
        description="Fallback module path if capability-based discovery fails",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the dependency",
    )

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
        frozen=True,
    )

    @field_validator("intent_types")
    @classmethod
    def validate_intent_types_not_empty(cls, v: list[str] | None) -> list[str] | None:
        """
        Validate that intent_types list does not contain empty strings.

        Args:
            v: The intent_types list value.

        Returns:
            The validated list.

        Raises:
            ValueError: If any intent type is empty or whitespace-only.
        """
        if v is not None:
            for i, intent in enumerate(v):
                if not intent or not intent.strip():
                    raise ValueError(
                        f"intent_types[{i}] cannot be empty or whitespace-only"
                    )
        return v

    @model_validator(mode="after")
    def validate_at_least_one_discovery_method(self) -> "ModelDependencySpec":
        """
        Validate that at least one discovery method is specified.

        At least one of capability, intent_types, or protocol must be specified
        for the dependency to be resolvable.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If none of the discovery methods is specified.
        """
        # Check capability - must be non-empty string
        has_capability = bool(self.capability and self.capability.strip())

        # Check intent_types - must be non-empty list
        has_intent_types = bool(self.intent_types and len(self.intent_types) > 0)

        # Check protocol - must be non-empty string
        has_protocol = bool(self.protocol and self.protocol.strip())

        if not (has_capability or has_intent_types or has_protocol):
            raise ModelOnexError(
                message=(
                    f"Dependency spec '{self.name}' must specify at least one discovery "
                    "method: capability, intent_types, or protocol. "
                    "None were provided or all were empty."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                name=self.name,
                capability=str(self.capability),
                intent_types=str(self.intent_types),
                protocol=str(self.protocol),
                requirement="At least one of: capability, intent_types, protocol",
            )

        return self

    def has_capability_filter(self) -> bool:
        """
        Check if this dependency spec uses capability-based discovery.

        Returns:
            True if capability is specified and non-empty, False otherwise.
        """
        return bool(self.capability and self.capability.strip())

    def has_intent_filter(self) -> bool:
        """
        Check if this dependency spec uses intent-based discovery.

        Returns:
            True if intent_types is specified and non-empty, False otherwise.
        """
        return bool(self.intent_types and len(self.intent_types) > 0)

    def has_protocol_filter(self) -> bool:
        """
        Check if this dependency spec uses protocol-based discovery.

        Returns:
            True if protocol is specified and non-empty, False otherwise.
        """
        return bool(self.protocol and self.protocol.strip())

    def get_discovery_methods(self) -> list[str]:
        """
        Get a list of discovery methods specified for this dependency.

        Returns:
            List of discovery method names that are specified.
            Possible values: "capability", "intent_types", "protocol".
        """
        methods: list[str] = []
        if self.has_capability_filter():
            methods.append("capability")
        if self.has_intent_filter():
            methods.append("intent_types")
        if self.has_protocol_filter():
            methods.append("protocol")
        return methods


__all__ = [
    "ModelDependencySpec",
    "DependencyType",
    "SelectionStrategy",
]
