"""
Node Type Model

Replaces EnumNodeType with a proper model that includes metadata,
descriptions, and categorization for each node type.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_config_category import EnumConfigCategory
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_return_type import EnumReturnType
from omnibase_core.enums.enum_type_name import EnumTypeName
from omnibase_core.exceptions.onex_error import OnexError


class ModelNodeType(BaseModel):
    """
    Node type with metadata and configuration.

    Replaces the EnumNodeType enum to provide richer information
    about each node type.
    """

    # Core fields (required) - Entity reference with UUID
    type_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the node type entity",
    )
    type_name: EnumTypeName = Field(
        ...,
        description="Node type identifier (e.g., CONTRACT_TO_MODEL)",
    )

    description: str = Field(..., description="Human-readable description of the node")

    category: EnumConfigCategory = Field(
        ...,
        description="Node category for organization",
    )

    # Optional metadata
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="Other node UUIDs this node depends on",
    )

    version_compatibility: str = Field(
        default=">=1.0.0",
        description="Version compatibility constraint",
    )

    execution_priority: int = Field(
        default=50,
        description="Execution priority (0-100, higher = more priority)",
        ge=0,
        le=100,
    )

    is_generator: bool = Field(
        default=False,
        description="Whether this node generates code/files",
    )

    is_validator: bool = Field(
        default=False,
        description="Whether this node validates existing code/files",
    )

    requires_contract: bool = Field(
        default=False,
        description="Whether this node requires a contract.yaml",
    )

    output_type: EnumReturnType | None = Field(
        default=None,
        description="Type of output produced (models, files, reports, etc.)",
    )

    # Factory methods for all node types
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
            dependencies=[],  # Dependencies should be set at runtime with actual UUIDs
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
            dependencies=[],  # Dependencies should be set at runtime with actual UUIDs
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
        """Create ModelNodeType from string name for current standards."""
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
        # Unknown node type - create generic
        # Try to create from known enum values, otherwise create generic
        try:
            enum_value = EnumTypeName(name)
            return cls(
                type_name=enum_value,
                description=f"Node: {name}",
                category=EnumConfigCategory.UNKNOWN,
            )
        except ValueError:
            # If name is not in enum, we can't create it - this maintains type safety
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown node type: {name}. Must be one of {list(EnumTypeName)}",
            )

    @property
    def name(self) -> str:
        """Get type name as string."""
        return self.type_name.value

    def __str__(self) -> str:
        """String representation for current standards."""
        return self.type_name.value

    def __eq__(self, other: object) -> bool:
        """Equality comparison for current standards."""
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
