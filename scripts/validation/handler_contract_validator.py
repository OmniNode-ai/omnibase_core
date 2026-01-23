#!/usr/bin/env python3
"""
Standalone Handler Contract Validator.

Minimal Pydantic models for validating handler contract YAML files without circular dependencies.
This module is designed specifically for the validation script to avoid import issues.

Handler contracts use a different schema than ONEX metadata contracts:
- They have handler_id instead of node_type/contract_version
- They define handler behavior through the descriptor field
- They specify capability dependencies and execution constraints

Supported node_archetype Values
-------------------------------
    compute, effect, reducer, orchestrator

Purity Values
-------------
    pure, side_effecting

Concurrency Policy Values
-------------------------
    parallel_ok, serialized

Observability Level Values
--------------------------
    minimal, standard, verbose

Usage Example
-------------
    from handler_contract_validator import MinimalHandlerContract

    yaml_data = {
        "handler_id": "compute.schema.validator",
        "name": "Schema Validator",
        "contract_version": {"major": 1, "minor": 0, "patch": 0},
        "descriptor": {
            "node_archetype": "compute",
            "purity": "pure",
            "idempotent": True,
        },
        "input_model": "myapp.models.Input",
        "output_model": "myapp.models.Output",
    }

    contract = MinimalHandlerContract.validate_yaml_content(yaml_data)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MinimalNodeArchetype:
    """Valid node_archetype values for handler contract validation."""

    VALID_ARCHETYPES = {"compute", "effect", "reducer", "orchestrator"}


class MinimalPurity:
    """Valid purity values for handler contract validation."""

    VALID_VALUES = {"pure", "side_effecting"}


class MinimalConcurrencyPolicy:
    """Valid concurrency_policy values for handler contract validation."""

    VALID_VALUES = {"parallel_ok", "serialized"}


class MinimalObservabilityLevel:
    """Valid observability_level values for handler contract validation."""

    VALID_VALUES = {"minimal", "standard", "verbose"}


class MinimalSemVer(BaseModel):
    """Minimal semantic version model for handler contract validation.

    Validates structured version format: {major: X, minor: Y, patch: Z}
    """

    model_config = ConfigDict(extra="forbid")

    major: int = Field(..., ge=0, description="Major version number")
    minor: int = Field(..., ge=0, description="Minor version number")
    patch: int = Field(..., ge=0, description="Patch version number")
    prerelease: tuple[str | int, ...] | list[str | int] | None = Field(
        default=None,
        description="Optional prerelease identifiers",
    )
    build: tuple[str, ...] | list[str] | None = Field(
        default=None,
        description="Optional build metadata",
    )


class MinimalRetryPolicy(BaseModel):
    """Minimal retry policy model for handler contracts."""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False)
    max_retries: int = Field(default=3, ge=0)
    backoff_strategy: str = Field(default="fixed")
    base_delay_ms: int = Field(default=100, ge=0)
    max_delay_ms: int = Field(default=10000, ge=0)


class MinimalCircuitBreaker(BaseModel):
    """Minimal circuit breaker model for handler contracts."""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False)
    failure_threshold: int = Field(default=5, ge=1)
    timeout_ms: int = Field(default=30000, ge=0)


class MinimalHandlerDescriptor(BaseModel):
    """Minimal handler behavior descriptor model for handler contracts."""

    model_config = ConfigDict(extra="allow")

    node_archetype: str = Field(
        ...,
        description="Type of handler (compute, effect, reducer, orchestrator)",
    )

    purity: str = Field(
        default="side_effecting",
        description="Handler purity (pure, side_effecting)",
    )

    idempotent: bool = Field(
        default=False,
        description="Whether handler is idempotent (safe to retry)",
    )

    timeout_ms: int = Field(
        default=30000,
        ge=0,
        description="Handler timeout in milliseconds",
    )

    retry_policy: MinimalRetryPolicy | None = Field(
        default=None,
        description="Retry policy configuration",
    )

    circuit_breaker: MinimalCircuitBreaker | None = Field(
        default=None,
        description="Circuit breaker configuration",
    )

    concurrency_policy: str = Field(
        default="serialized",
        description="Concurrency policy (parallel_ok, serialized)",
    )

    observability_level: str = Field(
        default="standard",
        description="Observability level (minimal, standard, verbose)",
    )

    @field_validator("node_archetype")
    @classmethod
    def validate_node_archetype(cls, value: str) -> str:
        """Validate node_archetype is one of the allowed values."""
        if not isinstance(value, str):
            raise ValueError("node_archetype must be a string")

        value_lower = value.lower()
        if value_lower not in MinimalNodeArchetype.VALID_ARCHETYPES:
            raise ValueError(
                f"Invalid node_archetype '{value}'. Must be one of: "
                f"{', '.join(sorted(MinimalNodeArchetype.VALID_ARCHETYPES))}"
            )
        return value_lower

    @field_validator("purity")
    @classmethod
    def validate_purity(cls, value: str) -> str:
        """Validate purity is one of the allowed values."""
        if not isinstance(value, str):
            raise ValueError("purity must be a string")

        value_lower = value.lower()
        if value_lower not in MinimalPurity.VALID_VALUES:
            raise ValueError(
                f"Invalid purity '{value}'. Must be one of: "
                f"{', '.join(sorted(MinimalPurity.VALID_VALUES))}"
            )
        return value_lower

    @field_validator("concurrency_policy")
    @classmethod
    def validate_concurrency_policy(cls, value: str) -> str:
        """Validate concurrency_policy is one of the allowed values."""
        if not isinstance(value, str):
            raise ValueError("concurrency_policy must be a string")

        value_lower = value.lower()
        if value_lower not in MinimalConcurrencyPolicy.VALID_VALUES:
            raise ValueError(
                f"Invalid concurrency_policy '{value}'. Must be one of: "
                f"{', '.join(sorted(MinimalConcurrencyPolicy.VALID_VALUES))}"
            )
        return value_lower

    @field_validator("observability_level")
    @classmethod
    def validate_observability_level(cls, value: str) -> str:
        """Validate observability_level is one of the allowed values."""
        if not isinstance(value, str):
            raise ValueError("observability_level must be a string")

        value_lower = value.lower()
        if value_lower not in MinimalObservabilityLevel.VALID_VALUES:
            raise ValueError(
                f"Invalid observability_level '{value}'. Must be one of: "
                f"{', '.join(sorted(MinimalObservabilityLevel.VALID_VALUES))}"
            )
        return value_lower


class MinimalRequirementSet(BaseModel):
    """Minimal requirement set for capability dependencies."""

    model_config = ConfigDict(extra="allow")

    must: dict[str, Any] = Field(default_factory=dict)
    prefer: dict[str, Any] = Field(default_factory=dict)
    forbid: dict[str, Any] = Field(default_factory=dict)


class MinimalCapabilityDependency(BaseModel):
    """Minimal capability dependency model for handler contracts."""

    model_config = ConfigDict(extra="allow")

    alias: str = Field(
        ...,
        min_length=1,
        description="Alias name for this capability",
    )

    capability: str = Field(
        ...,
        min_length=1,
        description="Capability identifier (e.g., 'database.relational')",
    )

    requirements: MinimalRequirementSet | None = Field(
        default=None,
        description="Capability requirements",
    )

    selection_policy: str = Field(
        default="auto_if_unique",
        description="How to select capability provider",
    )

    strict: bool = Field(
        default=True,
        description="Whether this capability is required (True) or optional (False)",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description",
    )


class MinimalExecutionConstraints(BaseModel):
    """Minimal execution constraints model for handler contracts."""

    model_config = ConfigDict(extra="allow")

    requires_before: list[str] = Field(
        default_factory=list,
        description="Capabilities that must execute before this handler",
    )

    requires_after: list[str] = Field(
        default_factory=list,
        description="Capabilities that must execute after this handler",
    )

    can_run_parallel: bool = Field(
        default=False,
        description="Whether handler can run in parallel with others",
    )

    must_run: bool = Field(
        default=False,
        description="Whether handler must always run",
    )

    nondeterministic_effect: bool = Field(
        default=False,
        description="Whether handler has nondeterministic effects",
    )


class MinimalHandlerContract(BaseModel):
    """Pydantic model for validating handler contract YAML files without circular imports.

    Validates required fields: handler_id, name, contract_version, descriptor, input_model, output_model.
    """

    model_config = ConfigDict(
        extra="allow",  # Allow additional fields for flexible contract formats
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    # Required identity fields
    handler_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Unique identifier for registry lookup",
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Human-readable display name",
    )

    contract_version: MinimalSemVer = Field(
        ...,
        description="Structured semantic version {major, minor, patch}",
    )

    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional detailed description",
    )

    # Required behavior descriptor
    descriptor: MinimalHandlerDescriptor = Field(
        ...,
        description="Handler behavior descriptor",
    )

    # Required execution fields
    input_model: str = Field(
        ...,
        min_length=1,
        description="Fully qualified input model reference",
    )

    output_model: str = Field(
        ...,
        min_length=1,
        description="Fully qualified output model reference",
    )

    # Optional capability dependencies
    capability_inputs: list[MinimalCapabilityDependency] = Field(
        default_factory=list,
        description="Required input capabilities",
    )

    capability_outputs: list[str] = Field(
        default_factory=list,
        description="Provided output capability names",
    )

    # Optional execution constraints
    execution_constraints: MinimalExecutionConstraints | None = Field(
        default=None,
        description="Execution ordering constraints",
    )

    # Optional lifecycle flags
    supports_lifecycle: bool = Field(
        default=False,
        description="Handler implements lifecycle hooks",
    )

    supports_health_check: bool = Field(
        default=False,
        description="Handler implements health checking",
    )

    supports_provisioning: bool = Field(
        default=False,
        description="Handler supports provisioning",
    )

    # Optional metadata
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and discovery",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    @field_validator("handler_id")
    @classmethod
    def validate_handler_id_format(cls, v: str) -> str:
        """Validate handler_id uses dot-notation with valid segments."""
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
        cls, v: list[MinimalCapabilityDependency]
    ) -> list[MinimalCapabilityDependency]:
        """Validate that capability input aliases are unique."""
        if not v:
            return v

        aliases = [dep.alias for dep in v]
        if len(aliases) != len(set(aliases)):
            duplicates = [a for a in aliases if aliases.count(a) > 1]
            raise ValueError(f"Duplicate capability input aliases: {set(duplicates)}")

        return v

    @model_validator(mode="after")
    def validate_descriptor_node_archetype_consistency(self) -> "MinimalHandlerContract":
        """Validate that handler_id prefix is consistent with descriptor.node_archetype."""
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
        if expected_archetype is not None and self.descriptor.node_archetype != expected_archetype:
            raise ValueError(
                f"Handler ID prefix '{prefix}' implies node_archetype='{expected_archetype}' "
                f"but descriptor has node_archetype='{self.descriptor.node_archetype}'"
            )

        return self

    @classmethod
    def validate_yaml_content(cls, yaml_data: dict[str, Any]) -> "MinimalHandlerContract":
        """Validate YAML dict and return validated handler contract.

        Args:
            yaml_data: Dictionary loaded from YAML file.

        Returns:
            Validated MinimalHandlerContract with normalized values.

        Raises:
            ValidationError: If required fields are missing or invalid.
        """
        return cls.model_validate(yaml_data)
