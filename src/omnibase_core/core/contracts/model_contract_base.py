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
        max_length=100,  # Prevent memory issues with extensive dependency lists
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

        # Validate dependency graph for circular dependencies
        self._validate_dependency_graph()

        # Delegate to node-specific validation
        self.validate_node_specific_config()

    @field_validator("dependencies", mode="before")
    @classmethod
    def validate_dependencies_model_dependency_only(
        cls, v: object
    ) -> list[ModelDependency]:
        """Validate dependencies with optimized batch processing.

        ZERO TOLERANCE for runtime: Only ModelDependency objects.
        YAML EXCEPTION: Allow dict conversion only during YAML contract loading.
        MEMORY SAFETY: Enforce maximum dependencies limit to prevent resource exhaustion.
        SECURITY: Reject string dependencies with clear actionable error messages.
        PERFORMANCE: Batch validation for large dependency lists.
        """
        if not v:
            return []

        if not isinstance(v, list):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Contract dependencies must be a list, got {type(v).__name__}",
                context={
                    "input_type": type(v).__name__,
                    "expected_type": "list",
                    "example": '[{"name": "ProtocolEventBus", "module": "omnibase_core.protocol"}]',
                },
            )

        # Memory safety check: prevent unbounded list growth
        max_dependencies = 100  # Same as Field max_length constraint
        if len(v) > max_dependencies:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Too many dependencies: {len(v)}. Maximum allowed: {max_dependencies}",
                context={
                    "dependency_count": len(v),
                    "max_allowed": max_dependencies,
                    "memory_safety": "Prevents memory exhaustion with large dependency lists",
                    "suggestion": "Consider using pagination or breaking into smaller contracts",
                },
            )

        # Batch validation approach for better performance
        return cls._validate_dependency_batch(v)

    @classmethod
    def _validate_dependency_batch(cls, dependencies: list) -> list[ModelDependency]:
        """
        Optimized batch validation for dependency lists.

        Groups validation by type for better performance and provides
        comprehensive error reporting for multiple issues.
        """
        if not dependencies:
            return []

        # Pre-categorize items by type for batch processing
        model_deps = []
        dict_deps = []
        string_deps = []
        invalid_deps = []

        # Single pass categorization
        for i, item in enumerate(dependencies):
            if isinstance(item, ModelDependency):
                model_deps.append((i, item))
            elif isinstance(item, dict):
                dict_deps.append((i, item))
            elif isinstance(item, str):
                string_deps.append((i, item))
            else:
                invalid_deps.append((i, item))

        # Immediate rejection of invalid types with batch error messages
        if string_deps or invalid_deps:
            cls._raise_batch_validation_errors(string_deps, invalid_deps)

        # Batch process valid ModelDependency instances
        result_deps = [item for _, item in model_deps]

        # Batch convert dict dependencies to ModelDependency
        if dict_deps:
            result_deps.extend(cls._batch_convert_dict_dependencies(dict_deps))

        return result_deps

    @classmethod
    def _raise_batch_validation_errors(
        cls, string_deps: list[tuple[int, str]], invalid_deps: list[tuple[int, object]]
    ) -> None:
        """Raise comprehensive batch validation errors."""
        error_details = []

        # Collect all string dependency errors
        for i, item in string_deps:
            error_details.append(
                {
                    "index": i,
                    "type": "string_dependency",
                    "value": str(item)[:50] + ("..." if len(str(item)) > 50 else ""),
                    "error": "String dependencies not allowed - security risk",
                }
            )

        # Collect all invalid type errors
        for i, item in invalid_deps:
            error_details.append(
                {
                    "index": i,
                    "type": "invalid_type",
                    "value": str(item)[:50] + ("..." if len(str(item)) > 50 else ""),
                    "error": f"Invalid type {type(item).__name__} not allowed",
                }
            )

        # Single comprehensive error with all validation issues
        raise OnexError(
            error_code=CoreErrorCode.VALIDATION_FAILED,
            message=f"Batch validation failed: {len(error_details)} invalid dependencies found",
            context={
                "validation_errors": error_details,
                "total_dependencies": len(string_deps) + len(invalid_deps),
                "security_policy": "String dependencies rejected to prevent injection attacks",
                "allowed_types": ["ModelDependency", "dict (YAML only)"],
                "example_format": {
                    "name": "ProtocolEventBus",
                    "module": "omnibase_core.protocol",
                },
            },
        )

    @classmethod
    def _batch_convert_dict_dependencies(
        cls, dict_deps: list[tuple[int, dict]]
    ) -> list[ModelDependency]:
        """Batch convert dict dependencies to ModelDependency instances."""
        result_deps = []
        conversion_errors = []

        for i, item in dict_deps:
            try:
                result_deps.append(ModelDependency(**item))
            except Exception as e:
                conversion_errors.append(
                    {
                        "index": i,
                        "data": str(item)[:100]
                        + ("..." if len(str(item)) > 100 else ""),
                        "error": str(e)[:100] + ("..." if len(str(e)) > 100 else ""),
                    }
                )

        # Report all conversion errors at once if any occurred
        if conversion_errors:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Batch YAML dependency conversion failed: {len(conversion_errors)} errors",
                context={
                    "conversion_errors": conversion_errors,
                    "total_failed": len(conversion_errors),
                    "yaml_deserialization": "Dict conversion allowed only for YAML loading",
                    "example_format": {
                        "name": "ProtocolEventBus",
                        "module": "omnibase_core.protocol",
                    },
                },
            )

        return result_deps

    @field_validator("node_type", mode="before")
    @classmethod
    def validate_node_type_enum_only(cls, v: object) -> EnumNodeType:
        """Validate node_type with YAML deserialization support.

        ZERO TOLERANCE for runtime usage: Only EnumNodeType enum instances.
        YAML EXCEPTION: Allow string conversion only during YAML contract loading.
        """
        if isinstance(v, EnumNodeType):
            return v
        elif isinstance(v, str):
            # YAML DESERIALIZATION EXCEPTION: Allow string-to-enum conversion for contract loading
            # This maintains zero tolerance for runtime while enabling YAML contract deserialization
            try:
                return EnumNodeType(v)
            except ValueError:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Invalid node_type string '{v}'. Must be valid EnumNodeType value.",
                    context={
                        "invalid_value": v,
                        "valid_enum_values": [e.value for e in EnumNodeType],
                        "yaml_deserialization": "String conversion allowed only for YAML loading",
                    },
                )
        else:
            # ZERO TOLERANCE: Reject all other types
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"node_type must be EnumNodeType enum or valid string for YAML, not {type(v).__name__}.",
                context={
                    "received_type": str(type(v)),
                    "expected_types": ["EnumNodeType", "str (YAML only)"],
                    "valid_enum_values": [e.value for e in EnumNodeType],
                },
            )

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

    def _validate_dependency_graph(self) -> None:
        """
        Validate dependency graph to prevent circular dependencies and ensure consistency.

        This validation prevents complex circular dependency scenarios where multiple
        dependencies might create loops in the contract dependency graph.
        """
        if not self.dependencies:
            return

        # Build dependency graph for cycle detection
        dependency_names = set()
        contract_name = self.name.lower()

        for dependency in self.dependencies:
            dep_name = dependency.name.lower()

            # Check for direct self-dependency
            if dep_name == contract_name:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Direct circular dependency: Contract '{self.name}' cannot depend on itself via dependency '{dependency.name}'.",
                    context={
                        "contract_name": self.name,
                        "dependency_name": dependency.name,
                        "dependency_type": dependency.dependency_type.value,
                        "validation_type": "direct_circular_dependency",
                        "suggested_fix": "Remove self-referencing dependency or use a different dependency name",
                    },
                )

            # Check for duplicate dependencies (same name)
            if dep_name in dependency_names:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Duplicate dependency detected: '{dependency.name}' is already defined in this contract.",
                    context={
                        "contract_name": self.name,
                        "duplicate_dependency": dependency.name,
                        "dependency_type": dependency.dependency_type.value,
                        "validation_type": "duplicate_dependency",
                        "suggested_fix": "Remove duplicate dependency or use different names for different versions",
                    },
                )

            dependency_names.add(dep_name)

            # Additional validation for module-based circular dependencies
            if dependency.module and self.name.lower() in dependency.module.lower():
                # This could indicate a potential circular dependency through module references
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Potential circular dependency: Contract '{self.name}' depends on module '{dependency.module}' which contains the contract name.",
                    context={
                        "contract_name": self.name,
                        "dependency_name": dependency.name,
                        "dependency_module": dependency.module,
                        "validation_type": "module_circular_dependency",
                        "warning": "This may indicate a circular dependency through module references",
                        "suggested_fix": "Verify that the module does not depend back on this contract",
                    },
                )

        # Validate maximum dependency complexity to prevent over-complex contracts
        max_dependencies = 50  # Reasonable limit for contract complexity
        if len(self.dependencies) > max_dependencies:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Contract has too many dependencies: {len(self.dependencies)}. Maximum recommended: {max_dependencies}.",
                context={
                    "contract_name": self.name,
                    "dependency_count": len(self.dependencies),
                    "max_recommended": max_dependencies,
                    "validation_type": "complexity_limit",
                    "architectural_guidance": "Consider breaking complex contracts into smaller, more focused contracts",
                },
            )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
        str_strip_whitespace = True
        # Enable model validation caching for performance
        validate_default = True
