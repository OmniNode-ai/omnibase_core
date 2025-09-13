#!/usr/bin/env python3
"""
Contract Model Base - ONEX Standards Compliant.

Abstract foundation for 4-node architecture contract models providing:
- Core contract identification and versioning
- Node type classification with EnumNodeType
- Input/output model specifications with generic typing
- Performance requirements and lifecycle management
- Validation rules and constraint definitions

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.contracts.model_dependency import ModelDependency
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums import EnumNodeType
from omnibase_core.models.core.model_semver import ModelSemVer


class ModelPerformanceRequirements(BaseModel):
    """
    Performance SLA specifications for contract-driven behavior.

    Defines measurable performance targets and resource constraints
    for runtime validation and optimization.
    """

    single_operation_max_ms: int | None = Field(
        default=None,
        description="Maximum execution time for single operation in milliseconds",
        ge=1,
    )

    batch_operation_max_s: int | None = Field(
        default=None,
        description="Maximum execution time for batch operations in seconds",
        ge=1,
    )

    memory_limit_mb: int | None = Field(
        default=None,
        description="Maximum memory usage in megabytes",
        ge=1,
    )

    cpu_limit_percent: int | None = Field(
        default=None,
        description="Maximum CPU usage percentage",
        ge=1,
        le=100,
    )

    throughput_min_ops_per_second: float | None = Field(
        default=None,
        description="Minimum throughput in operations per second",
        ge=0.0,
    )


class ModelLifecycleConfig(BaseModel):
    """
    Lifecycle management configuration for node initialization and cleanup.

    Defines initialization, error handling, state management and cleanup
    policies for contract-driven lifecycle management.
    """

    initialization_timeout_s: int = Field(
        default=30,
        description="Maximum time for node initialization in seconds",
        ge=1,
    )

    cleanup_timeout_s: int = Field(
        default=30,
        description="Maximum time for node cleanup in seconds",
        ge=1,
    )

    error_recovery_enabled: bool = Field(
        default=True,
        description="Enable automatic error recovery mechanisms",
    )

    state_persistence_enabled: bool = Field(
        default=False,
        description="Enable state persistence across restarts",
    )

    health_check_interval_s: int = Field(
        default=60,
        description="Health check interval in seconds",
        ge=1,
    )


class ModelValidationRules(BaseModel):
    """
    Contract validation rules and constraint definitions.

    Defines runtime validation rules for input/output models,
    configuration constraints, and compliance checking.
    """

    strict_typing_enabled: bool = Field(
        default=True,
        description="Enforce strict type checking for all operations",
    )

    input_validation_enabled: bool = Field(
        default=True,
        description="Enable input model validation",
    )

    output_validation_enabled: bool = Field(
        default=True,
        description="Enable output model validation",
    )

    performance_validation_enabled: bool = Field(
        default=True,
        description="Enable performance requirement validation",
    )

    constraint_definitions: dict[str, str] = Field(
        default_factory=dict,
        description="Custom constraint definitions for validation",
    )


class ModelContractBase(BaseModel, ABC):
    """
    Abstract base for 4-node architecture contract models.

    Provides common contract fields, node type classification,
    and foundational configuration for all specialized contract models.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Core contract identification
    name: str = Field(
        ...,
        description="Unique contract name for identification",
        min_length=1,
    )

    version: ModelSemVer = Field(
        ...,
        description="Semantic version following SemVer specification",
    )

    description: str = Field(
        ...,
        description="Human-readable contract description",
        min_length=1,
    )

    node_type: EnumNodeType = Field(
        ...,
        description="Node type classification for 4-node architecture",
    )

    # Model specifications with strong typing
    input_model: str = Field(
        ...,
        description="Fully qualified input model class name",
        min_length=1,
    )

    output_model: str = Field(
        ...,
        description="Fully qualified output model class name",
        min_length=1,
    )

    # Performance requirements
    performance: ModelPerformanceRequirements = Field(
        default_factory=ModelPerformanceRequirements,
        description="Performance SLA specifications",
    )

    # Lifecycle management
    lifecycle: ModelLifecycleConfig = Field(
        default_factory=ModelLifecycleConfig,
        description="Lifecycle management configuration",
    )

    # Dependencies and protocols
    dependencies: list[ModelDependency] = Field(
        default_factory=list,
        description="Required protocol dependencies with structured specification",
    )

    protocol_interfaces: list[str] = Field(
        default_factory=list,
        description="Protocol interfaces implemented by this contract",
    )

    # Validation and constraints
    validation_rules: ModelValidationRules = Field(
        default_factory=ModelValidationRules,
        description="Contract validation rules and constraints",
    )

    # Metadata and documentation
    author: str | None = Field(
        default=None,
        description="Contract author information",
    )

    documentation_url: str | None = Field(
        default=None,
        description="URL to detailed contract documentation",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Contract classification tags",
    )

    @abstractmethod
    def validate_node_specific_config(self) -> None:
        """
        Validate node-specific configuration requirements.

        Each specialized contract model must implement this method
        to validate their specific configuration requirements.

        Raises:
            ValidationError: If node-specific validation fails
        """

    def model_post_init(self, __context: object) -> None:
        """
        Post-initialization validation for contract compliance.

        Performs base validation and delegates to node-specific validation.
        """
        # Validate that node type matches contract specialization
        self._validate_node_type_compliance()

        # Validate protocol dependencies exist
        self._validate_protocol_dependencies()

        # Delegate to node-specific validation
        self.validate_node_specific_config()

    @field_validator("dependencies", mode="before")
    @classmethod
    def validate_dependencies_structured_only(cls, v: object) -> list[ModelDependency]:
        """Convert structured dependency dicts to ModelDependency objects.

        ONLY accepts structured dict format - no legacy string support.
        This enables YAML loading while maintaining zero tech debt.
        """
        if not v:
            return []

        if not isinstance(v, list):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Contract dependencies must be a list, got {type(v)}",
                context={"input_type": str(type(v))},
            )

        dependencies = []
        for i, item in enumerate(v):
            if isinstance(item, ModelDependency):
                dependencies.append(item)
            # ONEX STRONG TYPES ONLY: No dict fallbacks - use ModelDependency directly
            else:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Dependency {i} must be ModelDependency instance. Strong types only - no dict/string fallbacks.",
                    context={
                        "dependency_index": i,
                        "received_type": str(type(item)),
                        "expected_type": "ModelDependency",
                        "onex_principle": "Strong types only, no fallbacks",
                    },
                )

        return dependencies

    @field_validator("node_type", mode="before")
    @classmethod
    def validate_node_type_enum_only(cls, v: object) -> EnumNodeType:
        """ONEX STRONG TYPES: Only accept EnumNodeType instances, no string conversion."""
        if isinstance(v, EnumNodeType):
            return v
        # ONEX STRONG TYPES ONLY: No string fallbacks
        msg = f"node_type must be EnumNodeType enum instance, not {type(v).__name__}. Strong types only."
        raise ValueError(msg)

    def _validate_node_type_compliance(self) -> None:
        """
        Validate that node_type matches the specialized contract class.

        This is enforced in specialized contract models using Literal types.
        """
        # Base validation - specialized contracts use Literal types that preserve strings
        # Accept either EnumNodeType instances or valid enum value strings
        if isinstance(self.node_type, EnumNodeType):
            # Already an enum instance - valid
            return
        elif isinstance(self.node_type, str):
            # Check if it's a valid enum value string
            try:
                EnumNodeType(self.node_type)
                return
            except ValueError:
                msg = f"node_type string value '{self.node_type}' is not a valid EnumNodeType value"
                raise ValueError(msg)
        else:
            msg = f"node_type must be a valid EnumNodeType or enum value string, got {self.node_type!r} ({type(self.node_type)})"
            raise ValueError(msg)

    def _validate_protocol_dependencies(self) -> None:
        """
        Validate that all protocol dependencies follow ONEX naming conventions.

        Uses ModelDependency objects to provide consistent validation
        through unified format handling.
        """
        for dependency in self.dependencies:
            # All dependencies should now be ModelDependency instances
            if not isinstance(dependency, ModelDependency):
                msg = f"All dependencies must be ModelDependency instances, got: {type(dependency)}"
                raise ValueError(msg)

            # Validate dependency follows ONEX patterns
            if not dependency.matches_onex_patterns():
                msg = f"Dependency does not follow ONEX patterns: {dependency.name}"
                raise ValueError(msg)

        for interface in self.protocol_interfaces:
            # Only accept fully qualified protocol paths - no legacy patterns
            if "protocol" in interface.lower():
                continue
            msg = f"Protocol interface must contain 'protocol' in the name, got: {interface}"
            raise ValueError(
                msg,
            )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
        str_strip_whitespace = True
