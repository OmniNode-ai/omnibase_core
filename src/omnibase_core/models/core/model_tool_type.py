from pydantic import Field

"\nTool Type Model\n\nReplaces EnumToolType with a proper model that includes metadata,\ndescriptions, and categorization for each tool type.\n"
from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelToolType(BaseModel):
    """
    Tool type with metadata and configuration.

    Replaces the EnumToolType enum to provide richer information
    about each tool while maintaining compatibility.
    """

    name: str = Field(
        default=...,
        description="Tool type identifier (e.g., CONTRACT_TO_MODEL)",
        pattern="^[A-Z][A-Z0-9_]*$",
    )
    description: str = Field(
        default=..., description="Human-readable description of the tool"
    )
    category: str = Field(
        default=...,
        description="Tool category for organization",
        pattern="^[a-z][a-z0-9_]*$",
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Other tools this tool depends on"
    )
    version_compatibility: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version compatibility constraint",
    )
    execution_priority: int = Field(
        default=50,
        description="Execution priority (0-100, higher = more priority)",
        ge=0,
        le=100,
    )
    is_generator: bool = Field(
        default=False, description="Whether this tool generates code/files"
    )
    is_validator: bool = Field(
        default=False, description="Whether this tool validates existing code/files"
    )
    requires_contract: bool = Field(
        default=False, description="Whether this tool requires a contract.yaml"
    )
    output_type: str | None = Field(
        default=None,
        description="Type of output produced (models, files, reports, etc.)",
    )

    @classmethod
    def CONTRACT_TO_MODEL(cls) -> "ModelToolType":
        """Generates Pydantic models from contract.yaml."""
        return cls(
            name="CONTRACT_TO_MODEL",
            description="Generates Pydantic models from contract.yaml",
            category="generation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            requires_contract=True,
            output_type="models",
        )

    @classmethod
    def MULTI_DOC_MODEL_GENERATOR(cls) -> "ModelToolType":
        """Generates models from multiple YAML documents."""
        return cls(
            name="MULTI_DOC_MODEL_GENERATOR",
            description="Generates models from multiple YAML documents",
            category="generation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            output_type="models",
        )

    @classmethod
    def GENERATE_ERROR_CODES(cls) -> "ModelToolType":
        """Generates error code enums from contract."""
        return cls(
            name="GENERATE_ERROR_CODES",
            description="Generates error code enums from contract",
            category="generation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            requires_contract=True,
            output_type="enums",
        )

    @classmethod
    def GENERATE_INTROSPECTION(cls) -> "ModelToolType":
        """Generates introspection metadata."""
        return cls(
            name="GENERATE_INTROSPECTION",
            description="Generates introspection metadata",
            category="generation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            output_type="metadata",
        )

    @classmethod
    def NODE_GENERATOR(cls) -> "ModelToolType":
        """Generates complete node structure from templates."""
        return cls(
            name="NODE_GENERATOR",
            description="Generates complete node structure from templates",
            category="generation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            execution_priority=90,
            output_type="node",
        )

    @classmethod
    def TEMPLATE_ENGINE(cls) -> "ModelToolType":
        """Processes templates with token replacement."""
        return cls(
            name="TEMPLATE_ENGINE",
            description="Processes templates with token replacement",
            category="template",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            output_type="text",
        )

    @classmethod
    def FILE_GENERATOR(cls) -> "ModelToolType":
        """Generates files from templates."""
        return cls(
            name="FILE_GENERATOR",
            description="Generates files from templates",
            category="template",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            dependencies=["TEMPLATE_ENGINE"],
            output_type="files",
        )

    @classmethod
    def TEMPLATE_VALIDATOR(cls) -> "ModelToolType":
        """Validates node templates for consistency."""
        return cls(
            name="TEMPLATE_VALIDATOR",
            description="Validates node templates for consistency",
            category="validation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_validator=True,
            output_type="report",
        )

    @classmethod
    def VALIDATION_ENGINE(cls) -> "ModelToolType":
        """Validates node structure and contracts."""
        return cls(
            name="VALIDATION_ENGINE",
            description="Validates node structure and contracts",
            category="validation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_validator=True,
            requires_contract=True,
            execution_priority=80,
            output_type="report",
        )

    @classmethod
    def STANDARDS_COMPLIANCE_FIXER(cls) -> "ModelToolType":
        """Fixes code to comply with ONEX standards."""
        return cls(
            name="STANDARDS_COMPLIANCE_FIXER",
            description="Fixes code to comply with ONEX standards",
            category="maintenance",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            is_validator=True,
            output_type="fixes",
        )

    @classmethod
    def PARITY_VALIDATOR_WITH_FIXES(cls) -> "ModelToolType":
        """Validates and fixes parity issues."""
        return cls(
            name="PARITY_VALIDATOR_WITH_FIXES",
            description="Validates and fixes parity issues",
            category="validation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_validator=True,
            is_generator=True,
            output_type="report_and_fixes",
        )

    @classmethod
    def CONTRACT_COMPLIANCE(cls) -> "ModelToolType":
        """Validates contract compliance."""
        return cls(
            name="CONTRACT_COMPLIANCE",
            description="Validates contract compliance",
            category="validation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_validator=True,
            requires_contract=True,
            output_type="report",
        )

    @classmethod
    def INTROSPECTION_VALIDITY(cls) -> "ModelToolType":
        """Validates introspection data."""
        return cls(
            name="INTROSPECTION_VALIDITY",
            description="Validates introspection data",
            category="validation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_validator=True,
            output_type="report",
        )

    @classmethod
    def SCHEMA_CONFORMANCE(cls) -> "ModelToolType":
        """Validates schema conformance."""
        return cls(
            name="SCHEMA_CONFORMANCE",
            description="Validates schema conformance",
            category="validation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_validator=True,
            output_type="report",
        )

    @classmethod
    def ERROR_CODE_USAGE(cls) -> "ModelToolType":
        """Validates error code usage."""
        return cls(
            name="ERROR_CODE_USAGE",
            description="Validates error code usage",
            category="validation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_validator=True,
            output_type="report",
        )

    @classmethod
    def CLI_COMMANDS(cls) -> "ModelToolType":
        """Handles CLI command generation."""
        return cls(
            name="CLI_COMMANDS",
            description="Handles CLI command generation",
            category="cli",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            output_type="commands",
        )

    @classmethod
    def CLI_NODE_PARITY(cls) -> "ModelToolType":
        """Validates CLI and node parity."""
        return cls(
            name="CLI_NODE_PARITY",
            description="Validates CLI and node parity",
            category="cli",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_validator=True,
            output_type="report",
        )

    @classmethod
    def NODE_DISCOVERY(cls) -> "ModelToolType":
        """Discovers nodes in the codebase."""
        return cls(
            name="NODE_DISCOVERY",
            description="Discovers nodes in the codebase",
            category="discovery",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            execution_priority=95,
            output_type="nodes",
        )

    @classmethod
    def NODE_VALIDATION(cls) -> "ModelToolType":
        """Validates node implementation."""
        return cls(
            name="NODE_VALIDATION",
            description="Validates node implementation",
            category="validation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_validator=True,
            requires_contract=True,
            output_type="report",
        )

    @classmethod
    def METADATA_LOADER(cls) -> "ModelToolType":
        """Loads node metadata."""
        return cls(
            name="METADATA_LOADER",
            description="Loads node metadata",
            category="discovery",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            output_type="metadata",
        )

    @classmethod
    def SCHEMA_GENERATOR(cls) -> "ModelToolType":
        """Generates JSON schemas."""
        return cls(
            name="SCHEMA_GENERATOR",
            description="Generates JSON schemas",
            category="schema",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            output_type="schemas",
        )

    @classmethod
    def SCHEMA_DISCOVERY(cls) -> "ModelToolType":
        """Discovers and parses schemas."""
        return cls(
            name="SCHEMA_DISCOVERY",
            description="Discovers and parses schemas",
            category="schema",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            output_type="schemas",
        )

    @classmethod
    def SCHEMA_TO_PYDANTIC(cls) -> "ModelToolType":
        """Converts schemas to Pydantic models."""
        return cls(
            name="SCHEMA_TO_PYDANTIC",
            description="Converts schemas to Pydantic models",
            category="schema",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            dependencies=["SCHEMA_DISCOVERY"],
            output_type="models",
        )

    @classmethod
    def PROTOCOL_GENERATOR(cls) -> "ModelToolType":
        """Generates protocol interfaces."""
        return cls(
            name="PROTOCOL_GENERATOR",
            description="Generates protocol interfaces",
            category="generation",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            is_generator=True,
            output_type="protocols",
        )

    @classmethod
    def BACKEND_SELECTION(cls) -> "ModelToolType":
        """Selects appropriate backend."""
        return cls(
            name="BACKEND_SELECTION",
            description="Selects appropriate backend",
            category="runtime",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            output_type="backend",
        )

    @classmethod
    def NODE_MANAGER_RUNNER(cls) -> "ModelToolType":
        """Runs node manager operations."""
        return cls(
            name="NODE_MANAGER_RUNNER",
            description="Runs node manager operations",
            category="runtime",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            execution_priority=100,
            output_type="result",
        )

    @classmethod
    def MAINTENANCE(cls) -> "ModelToolType":
        """Handles maintenance operations."""
        return cls(
            name="MAINTENANCE",
            description="Handles maintenance operations",
            category="maintenance",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            output_type="status",
        )

    @classmethod
    def LOGGER_EMIT_LOG_EVENT(cls) -> "ModelToolType":
        """Emits structured log events."""
        return cls(
            name="tool_logger_emit_log_event",
            description="Emits structured log events",
            category="logging",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            output_type="logs",
        )

    @classmethod
    def LOGGING_UTILS(cls) -> "ModelToolType":
        """Logging utility functions."""
        return cls(
            name="LOGGING_UTILS",
            description="Logging utility functions",
            category="logging",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            output_type="logs",
        )

    @classmethod
    def SCENARIO_RUNNER(cls) -> "ModelToolType":
        """Runs test scenarios."""
        return cls(
            name="scenario_runner",
            description="Runs test scenarios",
            category="testing",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            output_type="results",
        )

    @classmethod
    def from_string(cls, name: str) -> "ModelToolType":
        """Create ModelToolType from string name for current standards."""
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
            "tool_logger_emit_log_event": cls.LOGGER_EMIT_LOG_EVENT,
            "LOGGING_UTILS": cls.LOGGING_UTILS,
            "scenario_runner": cls.SCENARIO_RUNNER,
        }
        factory = factory_map.get(name)
        if factory:
            return factory()
        return cls(
            name=name,
            description=f"Tool: {name}",
            category="unknown",
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
        )

    def __str__(self) -> str:
        """String representation for current standards."""
        return self.name

    def __eq__(self, other: object) -> bool:
        """Equality comparison for current standards."""
        if isinstance(other, str):
            return self.name == other
        if isinstance(other, ModelToolType):
            return self.name == other.name
        return False
