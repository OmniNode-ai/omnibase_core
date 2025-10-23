from __future__ import annotations

import uuid
from typing import Optional

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"\nNode Type Model\n\nReplaces EnumNodeType with a proper model that includes metadata,\ndescriptions, and categorization for each node type.\n"
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from omnibase_core.enums.enum_config_category import EnumConfigCategory
from omnibase_core.enums.enum_return_type import EnumReturnType
from omnibase_core.enums.enum_type_name import EnumTypeName
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.primitives.model_semver import ModelSemVer
from omnibase_core.types.constraints import (
    Identifiable,
    ProtocolMetadataProvider,
    ProtocolValidatable,
    Serializable,
)


class ModelNodeType(BaseModel):
    """
    Node type with metadata and configuration.

    Replaces the EnumNodeType enum to provide richer information
    about each node type.
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    type_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the node type entity"
    )
    type_name: EnumTypeName = Field(
        default=..., description="Node type identifier (e.g., CONTRACT_TO_MODEL)"
    )
    description: str = Field(
        default=..., description="Human-readable description of the node"
    )
    category: EnumConfigCategory = Field(
        default=..., description="Node category for organization"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Other node type names this node depends on"
    )
    version_compatibility: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version compatibility constraint",
    )
    execution_priority: int = Field(
        default=50,
        description="Execution priority (0-100, higher = more priority)",
        ge=0,
        le=100,
    )
    is_generator: bool = Field(
        default=False, description="Whether this node generates code/files"
    )
    is_validator: bool = Field(
        default=False, description="Whether this node validates existing code/files"
    )
    requires_contract: bool = Field(
        default=False, description="Whether this node requires a contract.yaml"
    )
    output_type: EnumReturnType | None = Field(
        default=None,
        description="Type of output produced (models, files, reports, etc.)",
    )

    @classmethod
    def CONTRACT_TO_MODEL(cls) -> ModelNodeType:
        """Generates Pydantic models from contract.yaml."""
        return cls(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Generates Pydantic models from contract.yaml",
            category=EnumConfigCategory.GENERATION,
            is_generator=True,
            requires_contract=True,
            output_type=EnumReturnType.MODELS,
        )

    @classmethod
    def MULTI_DOC_MODEL_GENERATOR(cls) -> ModelNodeType:
        """Generates models from multiple YAML documents."""
        return cls(
            type_name=EnumTypeName.MULTI_DOC_MODEL_GENERATOR,
            description="Generates models from multiple YAML documents",
            category=EnumConfigCategory.GENERATION,
            is_generator=True,
            output_type=EnumReturnType.MODELS,
        )

    @classmethod
    def GENERATE_ERROR_CODES(cls) -> ModelNodeType:
        """Generates error code enums from contract."""
        return cls(
            type_name=EnumTypeName.GENERATE_ERROR_CODES,
            description="Generates error code enums from contract",
            category=EnumConfigCategory.GENERATION,
            is_generator=True,
            requires_contract=True,
            output_type=EnumReturnType.ENUMS,
        )

    @classmethod
    def GENERATE_INTROSPECTION(cls) -> ModelNodeType:
        """Generates introspection metadata."""
        return cls(
            type_name=EnumTypeName.GENERATE_INTROSPECTION,
            description="Generates introspection metadata",
            category=EnumConfigCategory.GENERATION,
            is_generator=True,
            output_type=EnumReturnType.METADATA,
        )

    @classmethod
    def NODE_GENERATOR(cls) -> ModelNodeType:
        """Generates complete node structure from templates."""
        return cls(
            type_name=EnumTypeName.NODE_GENERATOR,
            description="Generates complete node structure from templates",
            category=EnumConfigCategory.GENERATION,
            is_generator=True,
            execution_priority=90,
            output_type=EnumReturnType.METADATA,
        )

    @classmethod
    def TEMPLATE_ENGINE(cls) -> ModelNodeType:
        """Processes templates with token replacement."""
        return cls(
            type_name=EnumTypeName.TEMPLATE_ENGINE,
            description="Processes templates with token replacement",
            category=EnumConfigCategory.TEMPLATE,
            is_generator=True,
            output_type=EnumReturnType.TEXT,
        )

    @classmethod
    def FILE_GENERATOR(cls) -> ModelNodeType:
        """Generates files from templates."""
        return cls(
            type_name=EnumTypeName.FILE_GENERATOR,
            description="Generates files from templates",
            category=EnumConfigCategory.TEMPLATE,
            is_generator=True,
            dependencies=["TEMPLATE_ENGINE"],
            output_type=EnumReturnType.FILES,
        )

    @classmethod
    def TEMPLATE_VALIDATOR(cls) -> ModelNodeType:
        """Validates node templates for consistency."""
        return cls(
            type_name=EnumTypeName.TEMPLATE_VALIDATOR,
            description="Validates node templates for consistency",
            category=EnumConfigCategory.VALIDATION,
            is_validator=True,
            output_type=EnumReturnType.REPORTS,
        )

    @classmethod
    def VALIDATION_ENGINE(cls) -> ModelNodeType:
        """Validates node structure and contracts."""
        return cls(
            type_name=EnumTypeName.VALIDATION_ENGINE,
            description="Validates node structure and contracts",
            category=EnumConfigCategory.VALIDATION,
            is_validator=True,
            requires_contract=True,
            execution_priority=80,
            output_type=EnumReturnType.REPORTS,
        )

    @classmethod
    def STANDARDS_COMPLIANCE_FIXER(cls) -> ModelNodeType:
        """Fixes code to comply with ONEX standards."""
        return cls(
            type_name=EnumTypeName.STANDARDS_COMPLIANCE_FIXER,
            description="Fixes code to comply with ONEX standards",
            category=EnumConfigCategory.MAINTENANCE,
            is_generator=True,
            is_validator=True,
            output_type=EnumReturnType.FILES,
        )

    @classmethod
    def PARITY_VALIDATOR_WITH_FIXES(cls) -> ModelNodeType:
        """Validates and fixes parity issues."""
        return cls(
            type_name=EnumTypeName.PARITY_VALIDATOR_WITH_FIXES,
            description="Validates and fixes parity issues",
            category=EnumConfigCategory.VALIDATION,
            is_validator=True,
            is_generator=True,
            output_type=EnumReturnType.REPORTS,
        )

    @classmethod
    def CONTRACT_COMPLIANCE(cls) -> ModelNodeType:
        """Validates contract compliance."""
        return cls(
            type_name=EnumTypeName.CONTRACT_COMPLIANCE,
            description="Validates contract compliance",
            category=EnumConfigCategory.VALIDATION,
            is_validator=True,
            requires_contract=True,
            output_type=EnumReturnType.REPORTS,
        )

    @classmethod
    def INTROSPECTION_VALIDITY(cls) -> ModelNodeType:
        """Validates introspection data."""
        return cls(
            type_name=EnumTypeName.INTROSPECTION_VALIDITY,
            description="Validates introspection data",
            category=EnumConfigCategory.VALIDATION,
            is_validator=True,
            output_type=EnumReturnType.REPORTS,
        )

    @classmethod
    def SCHEMA_CONFORMANCE(cls) -> ModelNodeType:
        """Validates schema conformance."""
        return cls(
            type_name=EnumTypeName.SCHEMA_CONFORMANCE,
            description="Validates schema conformance",
            category=EnumConfigCategory.VALIDATION,
            is_validator=True,
            output_type=EnumReturnType.REPORTS,
        )

    @classmethod
    def ERROR_CODE_USAGE(cls) -> ModelNodeType:
        """Validates error code usage."""
        return cls(
            type_name=EnumTypeName.ERROR_CODE_USAGE,
            description="Validates error code usage",
            category=EnumConfigCategory.VALIDATION,
            is_validator=True,
            output_type=EnumReturnType.REPORTS,
        )

    @classmethod
    def CLI_COMMANDS(cls) -> ModelNodeType:
        """Handles CLI command generation."""
        return cls(
            type_name=EnumTypeName.CLI_COMMANDS,
            description="Handles CLI command generation",
            category=EnumConfigCategory.CLI,
            is_generator=True,
            output_type=EnumReturnType.TEXT,
        )

    @classmethod
    def CLI_NODE_PARITY(cls) -> ModelNodeType:
        """Validates CLI and node parity."""
        return cls(
            type_name=EnumTypeName.CLI_NODE_PARITY,
            description="Validates CLI and node parity",
            category=EnumConfigCategory.CLI,
            is_validator=True,
            output_type=EnumReturnType.REPORTS,
        )

    @classmethod
    def NODE_DISCOVERY(cls) -> ModelNodeType:
        """Discovers nodes in the codebase."""
        return cls(
            type_name=EnumTypeName.NODE_DISCOVERY,
            description="Discovers nodes in the codebase",
            category=EnumConfigCategory.DISCOVERY,
            execution_priority=95,
            output_type=EnumReturnType.METADATA,
        )

    @classmethod
    def NODE_VALIDATION(cls) -> ModelNodeType:
        """Validates node implementation."""
        return cls(
            type_name=EnumTypeName.NODE_VALIDATION,
            description="Validates node implementation",
            category=EnumConfigCategory.VALIDATION,
            is_validator=True,
            requires_contract=True,
            output_type=EnumReturnType.REPORTS,
        )

    @classmethod
    def METADATA_LOADER(cls) -> ModelNodeType:
        """Loads node metadata."""
        return cls(
            type_name=EnumTypeName.METADATA_LOADER,
            description="Loads node metadata",
            category=EnumConfigCategory.DISCOVERY,
            output_type=EnumReturnType.METADATA,
        )

    @classmethod
    def SCHEMA_GENERATOR(cls) -> ModelNodeType:
        """Generates JSON schemas."""
        return cls(
            type_name=EnumTypeName.SCHEMA_GENERATOR,
            description="Generates JSON schemas",
            category=EnumConfigCategory.SCHEMA,
            is_generator=True,
            output_type=EnumReturnType.SCHEMAS,
        )

    @classmethod
    def SCHEMA_DISCOVERY(cls) -> ModelNodeType:
        """Discovers and parses schemas."""
        return cls(
            type_name=EnumTypeName.SCHEMA_DISCOVERY,
            description="Discovers and parses schemas",
            category=EnumConfigCategory.SCHEMA,
            output_type=EnumReturnType.SCHEMAS,
        )

    @classmethod
    def SCHEMA_TO_PYDANTIC(cls) -> ModelNodeType:
        """Converts schemas to Pydantic models."""
        return cls(
            type_name=EnumTypeName.SCHEMA_TO_PYDANTIC,
            description="Converts schemas to Pydantic models",
            category=EnumConfigCategory.SCHEMA,
            is_generator=True,
            dependencies=["SCHEMA_DISCOVERY"],
            output_type=EnumReturnType.MODELS,
        )

    @classmethod
    def PROTOCOL_GENERATOR(cls) -> ModelNodeType:
        """Generates protocol interfaces."""
        return cls(
            type_name=EnumTypeName.PROTOCOL_GENERATOR,
            description="Generates protocol interfaces",
            category=EnumConfigCategory.GENERATION,
            is_generator=True,
            output_type=EnumReturnType.PROTOCOLS,
        )

    @classmethod
    def BACKEND_SELECTION(cls) -> ModelNodeType:
        """Selects appropriate backend."""
        return cls(
            type_name=EnumTypeName.BACKEND_SELECTION,
            description="Selects appropriate backend",
            category=EnumConfigCategory.RUNTIME,
            output_type=EnumReturnType.BACKEND,
        )

    @classmethod
    def NODE_MANAGER_RUNNER(cls) -> ModelNodeType:
        """Runs node manager operations."""
        return cls(
            type_name=EnumTypeName.NODE_MANAGER_RUNNER,
            description="Runs node manager operations",
            category=EnumConfigCategory.RUNTIME,
            execution_priority=100,
            output_type=EnumReturnType.RESULT,
        )

    @classmethod
    def MAINTENANCE(cls) -> ModelNodeType:
        """Handles maintenance operations."""
        return cls(
            type_name=EnumTypeName.MAINTENANCE,
            description="Handles maintenance operations",
            category=EnumConfigCategory.MAINTENANCE,
            output_type=EnumReturnType.STATUS,
        )

    @classmethod
    def LOGGER_EMIT_LOG_EVENT(cls) -> ModelNodeType:
        """Emits structured log events."""
        return cls(
            type_name=EnumTypeName.NODE_LOGGER_EMIT_LOG_EVENT,
            description="Emits structured log events",
            category=EnumConfigCategory.LOGGING,
            output_type=EnumReturnType.LOGS,
        )

    @classmethod
    def LOGGING_UTILS(cls) -> ModelNodeType:
        """Logging utility functions."""
        return cls(
            type_name=EnumTypeName.LOGGING_UTILS,
            description="Logging utility functions",
            category=EnumConfigCategory.LOGGING,
            output_type=EnumReturnType.LOGS,
        )

    @classmethod
    def SCENARIO_RUNNER(cls) -> ModelNodeType:
        """Runs test scenarios."""
        return cls(
            type_name=EnumTypeName.SCENARIO_RUNNER,
            description="Runs test scenarios",
            category=EnumConfigCategory.TESTING,
            output_type=EnumReturnType.RESULTS,
        )

    @classmethod
    def from_string(cls, name: str) -> ModelNodeType:
        """
        Create ModelNodeType instance from string name.

        Factory method that creates a ModelNodeType instance from a string
        identifier. Supports all registered node type names with proper
        factory method mapping and fallback to generic node creation for
        valid enum values.

        Args:
            name: String identifier for the node type. Must match a factory
                method name (e.g., "CONTRACT_TO_MODEL", "NODE_GENERATOR")
                or be a valid EnumTypeName value.

        Returns:
            ModelNodeType instance configured with appropriate metadata,
            category, and capabilities for the specified node type.

        Raises:
            ModelOnexError: If the name is not a recognized node type and not
                a valid EnumTypeName value. Error includes validation_error
                code and suggestions for valid node types.

        Example:
            ```python
            # Create from factory method name
            node = ModelNodeType.from_string("CONTRACT_TO_MODEL")
            assert node.type_name == EnumTypeName.CONTRACT_TO_MODEL
            assert node.is_generator is True
            assert node.requires_contract is True

            # Create from enum value
            node = ModelNodeType.from_string("VALIDATION_ENGINE")
            assert node.category == EnumConfigCategory.VALIDATION

            # Invalid name raises ModelOnexError
            try:
                invalid_node = ModelNodeType.from_string("INVALID_TYPE")
            except ModelOnexError as e:
                print(f"Unknown node type: {e.message}")
            ```

        Note:
            For known node types with dedicated factory methods, this
            returns a fully configured instance with all metadata. For
            valid EnumTypeName values without factory methods, creates
            a generic node with UNKNOWN category. Use factory methods
            directly when possible for better type safety and IDE support.
        """
        factory_map = {
            "CONTRACT_TO_MODEL": cls.CONTRACT_TO_MODEL,
            "MULTI_DOC_MODEL_GENERATOR": cls.MULTI_DOC_MODEL_GENERATOR,
            "GENERATE_ERROR_CODES": cls.GENERATE_ERROR_CODES,
            "GENERATE_INTROSPECTION": cls.GENERATE_INTROSPECTION,
            "NODE_GENERATOR": cls.NODE_GENERATOR,
            "TEMPLATE_ENGINE": cls.TEMPLATE_ENGINE,
            "FILE_GENERATOR": cls.FILE_GENERATOR,
            "TEMPLATE_VALIDATOR": cls.TEMPLATE_VALIDATOR,
            "VALIDATION_ENGINE": cls.VALIDATION_ENGINE,
            "STANDARDS_COMPLIANCE_FIXER": cls.STANDARDS_COMPLIANCE_FIXER,
            "PARITY_VALIDATOR_WITH_FIXES": cls.PARITY_VALIDATOR_WITH_FIXES,
            "CONTRACT_COMPLIANCE": cls.CONTRACT_COMPLIANCE,
            "INTROSPECTION_VALIDITY": cls.INTROSPECTION_VALIDITY,
            "SCHEMA_CONFORMANCE": cls.SCHEMA_CONFORMANCE,
            "ERROR_CODE_USAGE": cls.ERROR_CODE_USAGE,
            "CLI_COMMANDS": cls.CLI_COMMANDS,
            "CLI_NODE_PARITY": cls.CLI_NODE_PARITY,
            "NODE_DISCOVERY": cls.NODE_DISCOVERY,
            "NODE_VALIDATION": cls.NODE_VALIDATION,
            "METADATA_LOADER": cls.METADATA_LOADER,
            "SCHEMA_GENERATOR": cls.SCHEMA_GENERATOR,
            "SCHEMA_DISCOVERY": cls.SCHEMA_DISCOVERY,
            "SCHEMA_TO_PYDANTIC": cls.SCHEMA_TO_PYDANTIC,
            "PROTOCOL_GENERATOR": cls.PROTOCOL_GENERATOR,
            "BACKEND_SELECTION": cls.BACKEND_SELECTION,
            "NODE_MANAGER_RUNNER": cls.NODE_MANAGER_RUNNER,
            "MAINTENANCE": cls.MAINTENANCE,
            "NODE_LOGGER_EMIT_LOG_EVENT": cls.LOGGER_EMIT_LOG_EVENT,
            "LOGGING_UTILS": cls.LOGGING_UTILS,
            "SCENARIO_RUNNER": cls.SCENARIO_RUNNER,
        }
        factory = factory_map.get(name)
        if factory:
            return factory()
        try:
            enum_value = EnumTypeName(name)
            return cls(
                type_name=enum_value,
                description=f"Node: {name}",
                category=EnumConfigCategory.UNKNOWN,
            )
        except ValueError:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown node type: {name}. Must be one of {list[Any](EnumTypeName)}",
            )

    @property
    def name(self) -> str:
        """
        Get the node type name as a string.

        Convenience property that returns the string value of the type_name
        enum. Useful for logging, display, and serialization scenarios.

        Returns:
            String representation of the node type name (e.g., "CONTRACT_TO_MODEL").

        Example:
            ```python
            node = ModelNodeType.CONTRACT_TO_MODEL()
            print(node.name)  # Output: "CONTRACT_TO_MODEL"
            assert node.name == "CONTRACT_TO_MODEL"
            ```
        """
        return self.type_name.value

    def __str__(self) -> str:
        """
        String representation of the ModelNodeType.

        Returns the type name value for string conversion operations.
        Used for logging, debugging, and display purposes.

        Returns:
            String representation of the node type name.

        Example:
            ```python
            node = ModelNodeType.VALIDATION_ENGINE()
            print(str(node))  # Output: "VALIDATION_ENGINE"
            log_message = f"Processing {node}"  # Uses __str__ implicitly
            ```
        """
        return self.type_name.value

    def __eq__(self, other: object) -> bool:
        """
        Equality comparison for ModelNodeType instances.

        Supports comparison with strings, other ModelNodeType instances,
        and EnumTypeName values for flexible equality checking.

        Args:
            other: Object to compare with. Can be str, ModelNodeType, or EnumTypeName.

        Returns:
            True if the objects represent the same node type, False otherwise.

        Example:
            ```python
            node = ModelNodeType.CONTRACT_TO_MODEL()

            # Compare with string
            assert node == "CONTRACT_TO_MODEL"

            # Compare with another instance
            node2 = ModelNodeType.CONTRACT_TO_MODEL()
            assert node == node2

            # Compare with enum
            assert node == EnumTypeName.CONTRACT_TO_MODEL

            # Different types are not equal
            assert node != "DIFFERENT_TYPE"
            ```
        """
        if isinstance(other, str):
            return self.type_name.value == other
        if isinstance(other, ModelNodeType):
            return self.type_name == other.type_name
        if isinstance(other, EnumTypeName):
            return self.type_name == other
        return False

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    def get_id(self) -> str:
        """
        Get unique identifier for the node type instance.

        Implements the Identifiable protocol by returning a stable string
        identifier. The method searches for ID fields in priority order to
        ensure deterministic, unique identification across serialization cycles.

        ID Generation Strategy:
            The method implements a priority-based search for stable identifiers:

            Priority order:
            1. type_id (UUID) - Most stable, preferred for node types
            2. id, uuid - Alternative UUID fields from protocols
            3. identifier, node_id - Named identifiers from specific contexts
            4. execution_id, metadata_id - Context-specific IDs
            5. Fallback: ClassName_instance_id (non-deterministic across runs)

            Rationale:
            - UUID fields provide cryptographic uniqueness and stability
            - Type-specific IDs (type_id) take precedence for semantic clarity
            - Named identifiers support protocol implementations
            - Memory address fallback ensures all instances have an ID

        Returns:
            String identifier for this instance. Uses type_id (UUID) if available,
            falls back to other ID fields in priority order, or generates a
            unique identifier based on class name and instance memory address.

        Example:
            ```python
            # UUID-based identification (stable)
            node = ModelNodeType.CONTRACT_TO_MODEL()
            node_id = node.get_id()
            print(f"Node ID: {node_id}")  # e.g., "550e8400-e29b-41d4-a716-446655440000"

            # ID is consistent for the same instance
            assert node.get_id() == node.get_id()

            # Serialization stability
            serialized = node.serialize()
            restored = ModelNodeType(**serialized)
            assert node.get_id() == restored.get_id()  # Same UUID preserved
            ```

        Warning:
            The fallback using id(self) is NOT stable across process restarts
            or serialization cycles. Always ensure models have proper UUID fields
            (type_id, id, uuid, etc.) for production use where identity persistence
            is required. The fallback exists only to guarantee every instance has
            an identifier for in-memory operations.

        Note:
            This method is called by protocol implementations (Identifiable)
            and should not be overridden unless you have specific requirements
            for identity semantics. The priority order is carefully designed
            to balance stability, uniqueness, and semantic clarity.
        """
        for field in [
            "type_id",
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field (type_id, id, uuid, identifier, etc.). Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> dict[str, Any]:
        """
        Get node type metadata as a dict[str, Any]ionary.

        Implements the ProtocolMetadataProvider protocol by extracting
        metadata from common fields. Useful for serialization, logging,
        and metadata-driven processing.

        Returns:
            Dictionary containing metadata fields such as name, description,
            version, tags, and other metadata attributes if present.

        Example:
            ```python
            node = ModelNodeType.CONTRACT_TO_MODEL()
            metadata = node.get_metadata()
            print(metadata)
            # Output: {'description': 'Generates Pydantic models from contract.yaml'}

            # Access specific metadata
            if 'description' in metadata:
                print(f"Description: {metadata['description']}")
            ```

        Note:
            Only includes fields that exist on the instance and have non-None
            values. Common metadata fields checked: name, description, version,
            tags, metadata.
        """
        metadata = {}
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """
        Set node type metadata from a dict[str, Any]ionary.

        Implements the ProtocolMetadataProvider protocol by updating
        instance attributes from a metadata dict[str, Any]ionary. Only updates
        attributes that already exist on the instance.

        Args:
            metadata: Dictionary of metadata key-value pairs to set.
                Keys should match attribute names on the instance.

        Returns:
            True if metadata was successfully set, False if an error occurred.

        Example:
            ```python
            node = ModelNodeType.CONTRACT_TO_MODEL()

            # Update description
            success = node.set_metadata({
                'description': 'Updated description',
                'execution_priority': 80
            })
            assert success is True
            assert node.description == 'Updated description'
            assert node.execution_priority == 80

            # Unknown attributes are ignored
            node.set_metadata({'unknown_field': 'value'})  # Silently ignored
            ```

        Note:
            This method silently ignores metadata keys that don't correspond
            to existing attributes. Returns False if any exception occurs
            during the update process.
        """
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            # fallback-ok: Metadata update failures should not break the system
            return False

    def serialize(self) -> dict[str, Any]:
        """
                Serialize the node type to a dict[str, Any]ionary.

                Implements the Serializable protocol by converting the instance
                to a dict[str, Any]ionary representation suitable for JSON serialization,
                storage, or transmission.

                Returns:
                    Dictionary representation of the node type with all fields
                    including None values, using field aliases if defined.

                Example:
                    ```python
                    node = ModelNodeType.CONTRACT_TO_MODEL()
                    serialized = node.serialize()

                    # Contains all fields
                    assert 'type_name' in serialized
                    assert 'description' in serialized
                    assert 'category' in serialized

                    # Can be used for JSON serialization
                    import json
        from omnibase_core.primitives.model_semver import ModelSemVer
                    json_str = json.dumps(serialized, default=str)
                    ```

                Note:
                    This method includes all fields regardless of their value,
                    including None values. Uses Pydantic's model_dump with
                    by_alias=True to support field aliases.
        """
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """
        Validate the integrity of this node type instance.

        Implements the ProtocolValidatable protocol by performing basic
        validation checks on the instance. Currently performs minimal
        validation as Pydantic handles most validation automatically.

        Returns:
            True if the instance is valid, False if validation fails.

        Example:
            ```python
            node = ModelNodeType.CONTRACT_TO_MODEL()
            is_valid = node.validate_instance()
            assert is_valid is True

            # Can be used in validation workflows
            if node.validate_instance():
                print("Node type is valid")
            else:
                print("Node type has validation errors")
            ```

        Note:
            This method provides a hook for custom validation logic.
            Override in subclasses to implement specific validation
            requirements. Pydantic validation occurs automatically
            during instantiation and assignment.
        """
        try:
            return True
        except Exception:
            # fallback-ok: Validation failures should not raise exceptions
            return False
