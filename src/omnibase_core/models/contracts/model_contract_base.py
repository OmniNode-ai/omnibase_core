"""
Contract Model Base.

Abstract foundation for 4-node architecture contract models providing:
- Core contract identification and versioning
- Node type classification with EnumNodeType
- Input/output model specifications with generic typing
- Performance requirements and lifecycle management
- Validation rules and constraint definitions

This implementation does not use Any types.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_field_limits import MAX_LABELS_COUNT
from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_dependency_type import EnumDependencyType
from omnibase_core.models.contracts.model_dependency import ModelDependency

# Import ModelExecutionProfile for execution profile field
from omnibase_core.models.contracts.model_execution_profile import (
    ModelExecutionProfile,
)

# Import types for type checking only (avoid circular import)
# The runtime module imports model_runtime_node_instance which imports ModelContractBase
if TYPE_CHECKING:
    from omnibase_core.models.contracts.model_consumed_event_entry import (
        ModelConsumedEventEntry,
    )
    from omnibase_core.models.contracts.model_published_event_entry import (
        ModelPublishedEventEntry,
    )
    from omnibase_core.models.contracts.subcontracts.model_handler_routing_subcontract import (
        ModelHandlerRoutingSubcontract,
    )
    from omnibase_core.models.runtime.model_handler_behavior import (
        ModelHandlerBehavior,
    )
from omnibase_core.models.contracts.model_lifecycle_config import ModelLifecycleConfig
from omnibase_core.models.contracts.model_performance_requirements import (
    ModelPerformanceRequirements,
)
from omnibase_core.models.contracts.model_validation_rules import ModelValidationRules
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import (
    TypedDictConsumedEventEntry,
    TypedDictPublishedEventEntry,
)


class ModelContractBase(BaseModel, ABC):
    """
    Abstract base for 4-node architecture contract models.

    Provides common contract fields, node type classification,
    and foundational configuration for all specialized contract models.

    Strict typing is enforced: No Any types allowed in implementation.

    ONEX Infrastructure Extensions
    ------------------------------
    This class includes extension fields for contract-level event routing and
    handler configuration (added in OMN-1588). These fields enable downstream
    infrastructure to read event subscriptions and publishing declarations
    directly from YAML contracts without requiring field stripping.

    **When to use each field:**

    - ``handler_routing``: Use when a node needs to dispatch messages to
      different handlers based on payload type, operation, or topic pattern.
      Common for ORCHESTRATOR nodes that route events to specific handlers.

    - ``yaml_consumed_events``: Use to declare which event types a node subscribes to.
      Enables infrastructure to auto-configure event subscriptions from contracts.
      Note: Named with ``yaml_`` prefix to avoid collision with
      ``ModelContractOrchestrator.consumed_events`` which uses a different type.

    - ``yaml_published_events``: Use to declare which events a node may publish.
      Enables infrastructure to validate event schemas and configure topics.
      Note: Named with ``yaml_`` prefix to avoid collision with
      ``ModelContractOrchestrator.published_events`` which uses a different type.

    **Example YAML contract with all extension fields:**

    .. code-block:: yaml

        name: node_job_orchestrator
        contract_version: {major: 1, minor: 0, patch: 0}
        description: Job orchestration node
        node_type: orchestrator

        # Handler routing configuration
        handler_routing:
          version: {major: 1, minor: 0, patch: 0}
          routing_strategy: payload_type_match
          handlers:
            - routing_key: ModelEventJobCreated
              handler_key: handle_job_created
              priority: 0
          default_handler: handle_unknown

        # Events this node consumes (string shorthand)
        yaml_consumed_events:
          - "jobs.events.created.v1"
          - "jobs.events.completed.v1"

        # Events this node publishes
        yaml_published_events:
          - topic: "jobs.events.started.v1"
            event_type: ModelEventJobStarted
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Core contract identification
    name: str = Field(
        default=...,
        description="Unique contract name for identification",
        min_length=1,
    )

    contract_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Contract schema version following SemVer specification (ONEX spec: contract_version)",
    )

    node_version: ModelSemVer | None = Field(
        default=None,
        description="Node implementation version. Tracks the version of the node "
        "that implements this contract, separate from the contract schema version.",
    )

    description: str = Field(
        default=...,
        description="Human-readable contract description",
        min_length=1,
    )

    node_type: EnumNodeType = Field(
        default=...,
        description="Node type classification for 4-node architecture",
    )

    # Model specifications with strong typing
    input_model: str = Field(
        default=...,
        description="Fully qualified input model class name",
        min_length=1,
    )

    output_model: str = Field(
        default=...,
        description="Fully qualified output model class name",
        min_length=1,
    )

    # Performance requirements
    performance: ModelPerformanceRequirements = Field(
        default_factory=ModelPerformanceRequirements,
        description="Performance SLA specifications",
    )

    # EnumLifecycle management
    lifecycle: ModelLifecycleConfig = Field(
        default_factory=ModelLifecycleConfig,
        description="EnumLifecycle management configuration",
    )

    # Dependencies and protocols
    dependencies: list[ModelDependency] = Field(
        default_factory=list,
        description="Required protocol dependencies with structured specification",
        max_length=MAX_LABELS_COUNT,  # Prevent memory issues with extensive dependency lists
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

    # Execution profile for contract-driven execution
    # Optional: Only set when created via profile factory
    execution: ModelExecutionProfile | None = Field(
        default=None,
        description="Execution profile defining phases and ordering policy. "
        "Set when created via profile factory, None for manually created contracts.",
    )

    # Handler behavior configuration for contract-driven execution
    # Optional: Only set when created via profile factory
    # Note: String annotation used to avoid circular import with runtime module
    behavior: "ModelHandlerBehavior | None" = Field(
        default=None,
        description="Handler behavior configuration defining purity, idempotency, "
        "concurrency, isolation, and observability. "
        "Set when created via profile factory, None for manually created contracts.",
    )

    # ONEX Infrastructure Extension Fields (OMN-1588)
    # These fields enable contract-level event routing and handler configuration
    # without requiring downstream repos to strip fields before validation.

    handler_routing: "ModelHandlerRoutingSubcontract | None" = Field(
        default=None,
        description="Handler routing configuration defining how messages are routed "
        "to handlers based on payload type, operation, or topic pattern. "
        "ONEX infra extension for contract-driven handler dispatch. "
        "Accepts ModelHandlerRoutingSubcontract instance or equivalent dict from YAML.",
    )

    yaml_consumed_events: "list[ModelConsumedEventEntry]" = Field(
        default_factory=list,
        description="Events consumed by this node. ONEX infra extension for event "
        "subscriptions. Supports multiple input formats: "
        "(1) String list: ['event.type.v1'] - auto-converted to entries with event_type; "
        "(2) Dict list: [{event_type: '...', handler_function: '...'}] - full specification; "
        "(3) ModelConsumedEventEntry instances - passed through directly. "
        "Named with yaml_ prefix to avoid collision with ModelContractOrchestrator fields.",
    )

    yaml_published_events: "list[ModelPublishedEventEntry]" = Field(
        default_factory=list,
        description="Events published by this node. ONEX infra extension for event "
        "publishing declarations. Supports multiple input formats: "
        "(1) String list: ['topic.v1'] - auto-converted using string as both topic and event_type; "
        "(2) Dict list: [{topic: '...', event_type: '...'}] - full specification; "
        "(3) ModelPublishedEventEntry instances - passed through directly. "
        "Named with yaml_ prefix to avoid collision with ModelContractOrchestrator fields.",
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
        cls,
        v: object,
    ) -> list[ModelDependency]:
        """Validate dependencies with optimized batch processing.

        Strict typing is enforced for runtime: Only ModelDependency objects.
        YAML EXCEPTION: Allow dict[str, Any]conversion only during YAML contract loading.
        MEMORY SAFETY: Enforce maximum dependencies limit to prevent resource exhaustion.
        SECURITY: Reject string dependencies with clear actionable error messages.
        PERFORMANCE: Batch validation for large dependency list[Any]s.
        """
        if not v:
            return []

        # Perform basic validation checks
        cls._validate_dependencies_basic_checks(v)

        # Cast to list[Any]after validation - we know it's a list[Any]after basic checks
        validated_list = cast("list[object]", v)

        # Delegate to batch processing
        return cls._validate_dependencies_batch_processing(validated_list)

    @classmethod
    def _validate_dependencies_basic_checks(cls, v: object) -> None:
        """Perform basic validation checks on dependencies input.

        Validates type requirements and memory safety constraints.

        Args:
            v: Dependencies input to validate

        Raises:
            ModelOnexError: If basic validation fails
        """
        if not isinstance(v, list):
            raise ModelOnexError(
                message=f"Contract dependencies must be a list, got {type(v).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                input_type=type(v).__name__,
                expected_type="list",
                example='[{"name": "ProtocolEventBus", "module": "omnibase_core.protocol"}]',
            )

        # Memory safety check: prevent unbounded list growth
        max_dependencies = 100  # Same as Field max_length constraint
        if len(v) > max_dependencies:
            raise ModelOnexError(
                message=f"Too many dependencies: {len(v)}. Maximum allowed: {max_dependencies}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                dependency_count=len(v),
                max_allowed=max_dependencies,
                memory_safety="Prevents memory exhaustion with large dependency lists",
                suggestion="Consider using pagination or breaking into smaller contracts",
            )

    @classmethod
    def _validate_dependencies_batch_processing(
        cls,
        v: list[object],
    ) -> list[ModelDependency]:
        """Process dependencies list with batch validation.

        Args:
            v: List of dependencies to process

        Returns:
            list[ModelDependency]: Validated and converted dependencies
        """
        # Batch validation approach for better performance
        return cls._validate_dependency_batch(v)

    @classmethod
    def _validate_dependency_batch(
        cls,
        dependencies: list[object],
    ) -> list[ModelDependency]:
        """
        Optimized batch validation for dependency lists.

        Groups validation by type for better performance and provides
        comprehensive error reporting for multiple issues.
        """
        if not dependencies:
            return []

        # Categorize dependencies by type for batch processing
        categorized = cls._categorize_dependencies_by_type(dependencies)

        # Process categorized dependencies
        return cls._process_categorized_dependencies(categorized)

    @classmethod
    def _categorize_dependencies_by_type(
        cls,
        dependencies: list[object],
    ) -> dict[str, list[tuple[int, object]]]:
        """Categorize dependencies by type for efficient batch processing.

        Args:
            dependencies: List of dependency objects to categorize

        Returns:
            dict[str, list[tuple[int, object]]]: Categorized dependencies by type
        """
        categorized: dict[str, list[tuple[int, object]]] = {
            "model_deps": [],
            "dict_deps": [],
            "string_deps": [],
            "invalid_deps": [],
        }

        # Single pass categorization
        for i, item in enumerate(dependencies):
            if isinstance(item, ModelDependency):
                categorized["model_deps"].append((i, item))
            elif isinstance(item, dict):
                categorized["dict_deps"].append((i, item))
            elif isinstance(item, str):
                categorized["string_deps"].append((i, item))
            else:
                categorized["invalid_deps"].append((i, item))

        return categorized

    @classmethod
    def _process_categorized_dependencies(
        cls,
        categorized: dict[str, list[tuple[int, object]]],
    ) -> list[ModelDependency]:
        """Process categorized dependencies and return validated list.

        Args:
            categorized: Dependencies categorized by type

        Returns:
            list[ModelDependency]: Validated dependencies
        """
        # Immediate rejection of invalid types with batch error messages
        if categorized["string_deps"] or categorized["invalid_deps"]:
            # Cast to expected types - we know string_deps contains strings
            string_deps = cast("list[tuple[int, str]]", categorized["string_deps"])
            cls._raise_batch_validation_errors(string_deps, categorized["invalid_deps"])

        # Batch process valid ModelDependency instances
        result_deps: list[ModelDependency] = [
            cast("ModelDependency", item) for _, item in categorized["model_deps"]
        ]

        # Batch convert dict dependencies to ModelDependency
        if categorized["dict_deps"]:
            # Cast to expected type - we know dict_deps contains dicts
            dict_deps = cast(
                "list[tuple[int, dict[str, object]]]",
                categorized["dict_deps"],
            )
            result_deps.extend(cls._batch_convert_dict_dependencies(dict_deps))

        return result_deps

    @classmethod
    def _raise_batch_validation_errors(
        cls,
        string_deps: list[tuple[int, str]],
        invalid_deps: list[tuple[int, object]],
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
                },
            )

        # Collect all invalid type errors
        for i, item_obj in invalid_deps:
            # Explicitly convert object to string for MyPy type safety
            item_str = str(item_obj)
            error_details.append(
                {
                    "index": i,
                    "type": "invalid_type",
                    "value": item_str[:50] + ("..." if len(item_str) > 50 else ""),
                    "error": f"Invalid type {type(item_obj).__name__} not allowed",
                },
            )

        # Single comprehensive error with all validation issues
        raise ModelOnexError(
            message=f"Batch validation failed: {len(error_details)} invalid dependencies found",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            validation_errors=error_details,
            total_dependencies=len(string_deps) + len(invalid_deps),
            security_policy="String dependencies rejected to prevent injection attacks",
            allowed_types=["ModelDependency", "dict[str, Any](YAML only)"],
            example_format={
                "name": "ProtocolEventBus",
                "module": "omnibase_core.protocol",
            },
        )

    @classmethod
    def _batch_convert_dict_dependencies(
        cls,
        dict_deps: list[tuple[int, dict[str, object]]],
    ) -> list[ModelDependency]:
        """Batch convert dict dependencies to ModelDependency instances."""
        result_deps = []
        conversion_errors = []

        for i, item in dict_deps:
            try:
                # Convert to proper dict[str, object] and extract typed values
                item_dict: dict[str, object] = dict(item)

                # Extract and convert values to proper types for ModelDependency
                name = str(item_dict.get("name", ""))
                module = (
                    str(item_dict["module"])
                    if item_dict.get("module") is not None
                    else None
                )
                dependency_type = item_dict.get(
                    "dependency_type",
                    EnumDependencyType.PROTOCOL,
                )
                if isinstance(dependency_type, str):
                    dependency_type = EnumDependencyType(dependency_type)
                elif not isinstance(dependency_type, EnumDependencyType):
                    dependency_type = EnumDependencyType.PROTOCOL

                version = item_dict.get("version")
                if version is not None and not isinstance(version, ModelSemVer):
                    # Convert to ModelSemVer if needed, otherwise set to None
                    version = None

                required = bool(item_dict.get("required", True))
                description = (
                    str(item_dict["description"])
                    if item_dict.get("description") is not None
                    else None
                )

                result_deps.append(
                    ModelDependency(
                        name=name,
                        module=module,
                        dependency_type=dependency_type,
                        version=version,
                        required=required,
                        description=description,
                    ),
                )
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                conversion_errors.append(
                    {
                        "index": i,
                        "data": str(item)[:100]
                        + ("..." if len(str(item)) > 100 else ""),
                        "error": str(e)[:100] + ("..." if len(str(e)) > 100 else ""),
                    },
                )

        # Report all conversion errors at once if any occurred
        if conversion_errors:
            raise ModelOnexError(
                message=f"Batch YAML dependency conversion failed: {len(conversion_errors)} errors",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                conversion_errors=conversion_errors,
                total_failed=len(conversion_errors),
                yaml_deserialization="Dict conversion allowed only for YAML loading",
                example_format={
                    "name": "ProtocolEventBus",
                    "module": "omnibase_core.protocol",
                },
            )

        return result_deps

    @field_validator("yaml_consumed_events", mode="before")
    @classmethod
    def normalize_yaml_consumed_events(
        cls, v: object
    ) -> list[TypedDictConsumedEventEntry]:
        """Normalize yaml_consumed_events from multiple input shapes.

        Supports two input formats:
        1. String list: ["event.type.v1", "other.event.v1"]
           - Each string becomes {event_type: "..."}
        2. Object list: [{event_type: "...", handler_function: "..."}]
           - Passed through as-is

        Args:
            v: Input value (list of strings, dicts, or ModelConsumedEventEntry)

        Returns:
            list[TypedDictConsumedEventEntry]: Normalized list for Pydantic validation

        Raises:
            ValueError: If input is not a list or contains invalid item types
        """
        if not v:
            return []
        if not isinstance(v, list):
            raise ValueError("yaml_consumed_events must be a list")

        result: list[TypedDictConsumedEventEntry] = []
        for item in v:
            if isinstance(item, str):
                # String form: convert to dict with event_type
                result.append({"event_type": item})
            elif isinstance(item, dict):
                # Dict form: pass through (cast for type safety, Pydantic validates)
                result.append(cast(TypedDictConsumedEventEntry, item))
            elif hasattr(item, "model_dump"):
                # Already a Pydantic model: dump to dict
                result.append(cast(TypedDictConsumedEventEntry, item.model_dump()))
            else:
                raise ValueError(
                    f"Invalid yaml_consumed_events item type: {type(item)}"
                )
        return result

    @field_validator("yaml_published_events", mode="before")
    @classmethod
    def normalize_yaml_published_events(
        cls, v: object
    ) -> list[TypedDictPublishedEventEntry]:
        """Normalize yaml_published_events from multiple input shapes.

        Supports two input formats:
        1. String list: ["topic.v1", "topic.v2"]
           - Each string becomes {topic: "...", event_type: "..."}
           - Uses the string as both topic and event_type (common pattern)
        2. Object list: [{topic: "...", event_type: "..."}]
           - Passed through as-is

        Args:
            v: Input value (list of strings, dicts, or ModelPublishedEventEntry)

        Returns:
            list[TypedDictPublishedEventEntry]: Normalized list for Pydantic validation

        Raises:
            ValueError: If input is not a list or contains invalid item types
        """
        if not v:
            return []
        if not isinstance(v, list):
            raise ValueError("yaml_published_events must be a list")

        result: list[TypedDictPublishedEventEntry] = []
        for item in v:
            if isinstance(item, str):
                # String form: use as both topic and event_type
                result.append({"topic": item, "event_type": item})
            elif isinstance(item, dict):
                # Dict form: pass through (cast for type safety, Pydantic validates)
                result.append(cast(TypedDictPublishedEventEntry, item))
            elif hasattr(item, "model_dump"):
                # Already a Pydantic model: dump to dict
                result.append(cast(TypedDictPublishedEventEntry, item.model_dump()))
            else:
                raise ValueError(
                    f"Invalid yaml_published_events item type: {type(item)}"
                )
        return result

    @field_validator("node_type", mode="before")
    @classmethod
    def validate_node_type_enum_only(cls, v: object) -> EnumNodeType:
        """Validate node_type with YAML deserialization support.

        Strict typing is enforced for runtime usage: Only EnumNodeType enum instances.
        YAML EXCEPTION: Allow string conversion only during YAML contract loading.
        """
        if isinstance(v, EnumNodeType):
            return v
        if isinstance(v, str):
            # YAML DESERIALIZATION EXCEPTION: Allow string-to-enum conversion for contract loading
            # This maintains strict typing for runtime while enabling YAML contract deserialization
            try:
                return EnumNodeType(v)
            except ValueError:
                raise ModelOnexError(
                    message=f"Invalid node_type string '{v}'. Must be valid EnumNodeType value.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    invalid_value=v,
                    valid_enum_values=[e.value for e in EnumNodeType],
                    yaml_deserialization="String conversion allowed only for YAML loading",
                )
        else:
            # Strict typing is enforced: Reject all other types
            raise ModelOnexError(
                message=f"node_type must be EnumNodeType enum or valid string for YAML, not {type(v).__name__}.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                received_type=str(type(v)),
                expected_types=["EnumNodeType", "str (YAML only)"],
                valid_enum_values=[e.value for e in EnumNodeType],
            )

    def _validate_node_type_compliance(self) -> None:
        """
        Validate that node_type matches the specialized contract class.

        This is enforced in specialized contract models using Literal types.
        """
        # After Pydantic validation, node_type is guaranteed to be EnumNodeType
        # (string-to-enum conversion happens in field validator)
        # Type validation is handled by Pydantic, so no runtime check needed
        # Base validation passed - specialized contracts add additional constraints

    def _validate_protocol_dependencies(self) -> None:
        """
        Validate that all protocol dependencies follow ONEX naming conventions.

        Uses ModelDependency objects to provide consistent validation
        through unified format handling.
        """
        for dependency in self.dependencies:
            # All dependencies are guaranteed to be ModelDependency instances via Pydantic validation
            # Validate dependency follows ONEX patterns
            if not dependency.matches_onex_patterns():
                raise ModelOnexError(
                    message=f"Dependency does not follow ONEX patterns: {dependency.name}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

        for interface in self.protocol_interfaces:
            # Only accept fully qualified protocol paths - no legacy patterns
            if "protocol" in interface.lower():
                continue
            raise ModelOnexError(
                message=f"Protocol interface must contain 'protocol' in the name, got: {interface}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
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
                raise ModelOnexError(
                    message=f"Direct circular dependency: Contract '{self.name}' cannot depend on itself via dependency '{dependency.name}'.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    contract_name=self.name,
                    dependency_name=dependency.name,
                    dependency_type=dependency.dependency_type.value,
                    validation_type="direct_circular_dependency",
                    suggested_fix="Remove self-referencing dependency or use a different dependency name",
                )

            # Check for duplicate dependencies (same name)
            if dep_name in dependency_names:
                raise ModelOnexError(
                    message=f"Duplicate dependency detected: '{dependency.name}' is already defined in this contract.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    contract_name=self.name,
                    duplicate_dependency=dependency.name,
                    dependency_type=dependency.dependency_type.value,
                    validation_type="duplicate_dependency",
                    suggested_fix="Remove duplicate dependency or use different names for different versions",
                )

            dependency_names.add(dep_name)

            # Additional validation for module-based circular dependencies
            if dependency.module and self.name.lower() in dependency.module.lower():
                # This could indicate a potential circular dependency through module references
                raise ModelOnexError(
                    message=f"Potential circular dependency: Contract '{self.name}' depends on module '{dependency.module}' which contains the contract name.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    contract_name=self.name,
                    dependency_name=dependency.name,
                    dependency_module=dependency.module,
                    validation_type="module_circular_dependency",
                    warning="This may indicate a circular dependency through module references",
                    suggested_fix="Verify that the module does not depend back on this contract",
                )

        # Validate maximum dependency complexity to prevent over-complex contracts
        max_dependencies = 50  # Reasonable limit for contract complexity
        if len(self.dependencies) > max_dependencies:
            raise ModelOnexError(
                message=f"Contract has too many dependencies: {len(self.dependencies)}. Maximum recommended: {max_dependencies}.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                contract_name=self.name,
                dependency_count=len(self.dependencies),
                max_recommended=max_dependencies,
                validation_type="complexity_limit",
                architectural_guidance="Consider breaking complex contracts into smaller, more focused contracts",
            )

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers)
    model_config = ConfigDict(
        extra="forbid",  # Strict typing - reject unknown fields (Strict typing is enforced)
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
        str_strip_whitespace=True,
        validate_default=True,  # Enable model validation caching for performance
        from_attributes=True,
    )


# Resolve forward references after class definition.
# These imports are deferred to avoid circular import during module loading.
# The TYPE_CHECKING imports above are used for static type checking only.
def _rebuild_model_contract_base() -> None:
    """Rebuild ModelContractBase to resolve forward references."""
    from omnibase_core.models.contracts.model_consumed_event_entry import (
        ModelConsumedEventEntry,
    )
    from omnibase_core.models.contracts.model_published_event_entry import (
        ModelPublishedEventEntry,
    )
    from omnibase_core.models.contracts.subcontracts.model_handler_routing_subcontract import (
        ModelHandlerRoutingSubcontract,
    )
    from omnibase_core.models.runtime.model_handler_behavior import (
        ModelHandlerBehavior,
    )

    # Pass the types in the namespace so Pydantic can resolve forward references
    ModelContractBase.model_rebuild(
        _types_namespace={
            "ModelHandlerBehavior": ModelHandlerBehavior,
            "ModelHandlerRoutingSubcontract": ModelHandlerRoutingSubcontract,
            "ModelConsumedEventEntry": ModelConsumedEventEntry,
            "ModelPublishedEventEntry": ModelPublishedEventEntry,
        }
    )


_rebuild_model_contract_base()
