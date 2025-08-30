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
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums import EnumNodeType
from omnibase_core.model.core.model_semver import ModelSemVer


class ModelPerformanceRequirements(BaseModel):
    """
    Performance SLA specifications for contract-driven behavior.

    Defines measurable performance targets and resource constraints
    for runtime validation and optimization.
    """

    single_operation_max_ms: Optional[int] = Field(
        default=None,
        description="Maximum execution time for single operation in milliseconds",
        ge=1,
    )

    batch_operation_max_s: Optional[int] = Field(
        default=None,
        description="Maximum execution time for batch operations in seconds",
        ge=1,
    )

    memory_limit_mb: Optional[int] = Field(
        default=None, description="Maximum memory usage in megabytes", ge=1
    )

    cpu_limit_percent: Optional[int] = Field(
        default=None, description="Maximum CPU usage percentage", ge=1, le=100
    )

    throughput_min_ops_per_second: Optional[float] = Field(
        default=None, description="Minimum throughput in operations per second", ge=0.0
    )


class ModelLifecycleConfig(BaseModel):
    """
    Lifecycle management configuration for node initialization and cleanup.

    Defines initialization, error handling, state management and cleanup
    policies for contract-driven lifecycle management.
    """

    initialization_timeout_s: int = Field(
        default=30, description="Maximum time for node initialization in seconds", ge=1
    )

    cleanup_timeout_s: int = Field(
        default=30, description="Maximum time for node cleanup in seconds", ge=1
    )

    error_recovery_enabled: bool = Field(
        default=True, description="Enable automatic error recovery mechanisms"
    )

    state_persistence_enabled: bool = Field(
        default=False, description="Enable state persistence across restarts"
    )

    health_check_interval_s: int = Field(
        default=60, description="Health check interval in seconds", ge=1
    )


class ModelValidationRules(BaseModel):
    """
    Contract validation rules and constraint definitions.

    Defines runtime validation rules for input/output models,
    configuration constraints, and compliance checking.
    """

    strict_typing_enabled: bool = Field(
        default=True, description="Enforce strict type checking for all operations"
    )

    input_validation_enabled: bool = Field(
        default=True, description="Enable input model validation"
    )

    output_validation_enabled: bool = Field(
        default=True, description="Enable output model validation"
    )

    performance_validation_enabled: bool = Field(
        default=True, description="Enable performance requirement validation"
    )

    constraint_definitions: Dict[str, str] = Field(
        default_factory=dict, description="Custom constraint definitions for validation"
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
        ..., description="Unique contract name for identification", min_length=1
    )

    version: ModelSemVer = Field(
        ..., description="Semantic version following SemVer specification"
    )

    description: str = Field(
        ..., description="Human-readable contract description", min_length=1
    )

    node_type: EnumNodeType = Field(
        ..., description="Node type classification for 4-node architecture"
    )

    # Model specifications with strong typing
    input_model: str = Field(
        ..., description="Fully qualified input model class name", min_length=1
    )

    output_model: str = Field(
        ..., description="Fully qualified output model class name", min_length=1
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
    dependencies: List[str] = Field(
        default_factory=list,
        description="Required protocol dependencies (fully qualified names)",
    )

    protocol_interfaces: List[str] = Field(
        default_factory=list,
        description="Protocol interfaces implemented by this contract",
    )

    # Validation and constraints
    validation_rules: ModelValidationRules = Field(
        default_factory=ModelValidationRules,
        description="Contract validation rules and constraints",
    )

    # Metadata and documentation
    author: Optional[str] = Field(
        default=None, description="Contract author information"
    )

    documentation_url: Optional[str] = Field(
        default=None, description="URL to detailed contract documentation"
    )

    tags: List[str] = Field(
        default_factory=list, description="Contract classification tags"
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
        pass

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

    @field_validator("node_type", mode="before")
    @classmethod
    def convert_node_type_string_to_enum(cls, v: object) -> EnumNodeType:
        """Convert string node_type values to enum values when loading from YAML."""
        if isinstance(v, str):
            return EnumNodeType(v)
        if isinstance(v, EnumNodeType):
            return v
        raise ValueError(f"Invalid node_type value: {v}")

    def _validate_node_type_compliance(self) -> None:
        """
        Validate that node_type matches the specialized contract class.

        This is enforced in specialized contract models using Literal types.
        """
        # Try to convert string to enum if needed (fallback validation)
        if isinstance(self.node_type, str):
            try:
                self.node_type = EnumNodeType(self.node_type)
            except ValueError:
                raise ValueError(
                    f"Invalid node_type string: {self.node_type}. Must be one of: {list(EnumNodeType)}"
                )

        # Base validation - specialized contracts override with Literal types
        if not isinstance(self.node_type, EnumNodeType):
            raise ValueError(
                f"node_type must be a valid EnumNodeType, got {type(self.node_type)}"
            )

    def _validate_protocol_dependencies(self) -> None:
        """
        Validate that all protocol dependencies are properly formatted.

        Ensures protocol dependencies follow ONEX naming conventions.
        Accepts both simple names (Protocol*) and fully qualified paths (omnibase.protocol.protocol_*).
        Also supports structured dependency specifications with separate fields.
        """
        for dependency in self.dependencies:
            # Handle string dependencies (traditional format used by most tools)
            if isinstance(dependency, str):
                # Accept fully qualified protocol paths like omnibase.protocol.protocol_consul_client
                if "protocol" in dependency.lower():
                    # Valid protocol dependency
                    continue
                # Also accept simple Protocol* names for backward compatibility
                if dependency.startswith("Protocol"):
                    continue
                raise ValueError(
                    f"Protocol dependency must contain 'protocol' or start with 'Protocol', got: {dependency}"
                )

            # Handle structured dependencies (used by infrastructure tools)
            elif (
                hasattr(dependency, "name")
                and hasattr(dependency, "type")
                and hasattr(dependency, "module")
            ):
                # This is a structured dependency - validate the module path and type
                module_path = dependency.module
                dep_type = dependency.type
                if "protocol" in module_path.lower() or dep_type.lower() == "protocol":
                    continue
                raise ValueError(
                    f"Structured dependency must have 'protocol' in module path or type 'protocol', got: {dependency}"
                )

            # Unknown dependency format
            else:
                raise ValueError(
                    f"Dependency must be a string or structured specification, got: {type(dependency)}"
                )

        for interface in self.protocol_interfaces:
            # Accept fully qualified protocol paths
            if "protocol" in interface.lower():
                continue
            # Also accept simple Protocol* names for backward compatibility
            if interface.startswith("Protocol"):
                continue
            raise ValueError(
                f"Protocol interface must contain 'protocol' or start with 'Protocol', got: {interface}"
            )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
        str_strip_whitespace = True
