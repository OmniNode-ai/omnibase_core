"""
Parsed Arguments Model

Type-safe parsed CLI arguments with validation results, command definition,
and parsing metadata for complete argument handling.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_argument_map import ModelArgumentMap
from omnibase_core.models.core.model_argument_value import ArgumentValueType
from omnibase_core.models.core.model_cli_command_definition import (
    ModelCliCommandDefinition,
)
from omnibase_core.models.core.model_node_reference import ModelNodeReference
from omnibase_core.models.core.model_parse_metadata import ModelParseMetadata
from omnibase_core.models.core.model_validation_summary import (
    ModelValidationErrorSummary,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_validation_error import ModelValidationError


class ModelParsedArguments(BaseModel):
    """
    Type-safe parsed CLI arguments with validation and metadata.

    This model represents the complete result of parsing CLI arguments
    including the parsed values, validation results, and metadata.
    """

    arguments: ModelArgumentMap = Field(
        default=...,
        description="Parsed argument values in type-safe container",
    )

    command_definition: ModelCliCommandDefinition = Field(
        default=...,
        description="Command definition used for parsing",
    )

    target_node: ModelNodeReference = Field(
        default=...,
        description="Target node reference for execution",
    )

    validation_errors: list[ModelValidationError] = Field(
        default_factory=list,
        description="Validation errors encountered during parsing",
    )

    validation_warnings: list[ModelValidationError] = Field(
        default_factory=list,
        description="Validation warnings (non-blocking issues)",
    )

    parse_metadata: ModelParseMetadata | None = Field(
        default=None,
        description="Parsing metadata and performance information",
    )

    is_help_request: bool = Field(
        default=False,
        description="Whether this was a help request (--help, -h)",
    )

    is_version_request: bool = Field(
        default=False,
        description="Whether this was a version request (--version)",
    )

    raw_command_line: str = Field(
        default="",
        description="Original command line string",
    )

    parsed_successfully: bool = Field(
        default=True,
        description="Whether parsing completed without critical errors",
    )

    def is_valid(self) -> bool:
        """Check if arguments are valid (no validation errors)."""
        return len(self.validation_errors) == 0 and self.parsed_successfully

    def has_warnings(self) -> bool:
        """Check if there are validation warnings."""
        return len(self.validation_warnings) > 0

    def has_critical_errors(self) -> bool:
        """Check if there are critical validation errors."""
        return any(error.is_critical() for error in self.validation_errors)

    def get_error_summary(self) -> ModelValidationErrorSummary:
        """Get summary of validation issues."""
        return ModelValidationErrorSummary(
            errors=len(self.validation_errors),
            warnings=len(self.validation_warnings),
            critical_errors=len(
                [e for e in self.validation_errors if e.is_critical()],
            ),
            total_issues=len(self.validation_errors) + len(self.validation_warnings),
        )

    def get_all_errors(self) -> list[ModelValidationError]:
        """Get all validation errors and warnings combined."""
        return self.validation_errors + self.validation_warnings

    def get_critical_errors(self) -> list[ModelValidationError]:
        """Get only critical validation errors."""
        return [error for error in self.validation_errors if error.is_critical()]

    def get_error_messages(self) -> list[str]:
        """Get formatted error messages for display."""
        messages = []
        for error in self.validation_errors:
            messages.append(error.message)
        return messages

    def get_warning_messages(self) -> list[str]:
        """Get formatted warning messages for display."""
        messages = []
        for warning in self.validation_warnings:
            messages.append(warning.message)
        return messages

    def add_validation_error(self, error: ModelValidationError) -> None:
        """Add a validation error."""
        if error.is_warning():
            self.validation_warnings.append(error)
        else:
            self.validation_errors.append(error)
            if error.is_critical():
                self.parsed_successfully = False

    def to_execution_dict(self) -> dict[str, object]:
        """Convert to dictionary suitable for node execution.

        Returns:
            A dictionary containing argument values and command metadata
            including _command_name, _target_node, _action, and optionally
            _parse_duration_ms and _parsing_strategy.

        Raises:
            ModelOnexError: If arguments are not valid (validation errors exist
                or parsing was not successful).
        """
        if not self.is_valid():
            msg = "Cannot convert invalid arguments to execution dict"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # Start with the argument map dictionary
        result: dict[str, object] = self.arguments.to_dict()

        # Add command metadata
        result["_command_name"] = self.command_definition.command_name
        result["_target_node"] = self.target_node.node_name
        result["_action"] = self.command_definition.action

        # Add parsing metadata if available
        if self.parse_metadata:
            result["_parse_duration_ms"] = self.parse_metadata.parse_duration_ms
            result["_parsing_strategy"] = self.parse_metadata.parsing_strategy

        return result

    def get_argument_value(
        self, name: str, default: ArgumentValueType | None = None
    ) -> ArgumentValueType | None:
        """Get argument value by name with optional default.

        Args:
            name: The argument name to look up.
            default: Default value to return if argument not found. Defaults to None.
                Must be a valid ArgumentValueType (str, int, bool, float, or list thereof).

        Returns:
            The argument value if found, otherwise the default value.
            Returns None if the argument is not found and no default is provided.
            The return type is ArgumentValueType | None for type safety.
        """
        if self.arguments.has_argument(name):
            return self.arguments.named_args[name].value
        return default

    def get_required_arguments(self) -> list[str]:
        """Get list of required argument names from command definition."""
        return [arg.name for arg in self.command_definition.required_args]

    def validate_required_arguments(self) -> list[ModelValidationError]:
        """Validate that all required arguments are present."""
        errors = []
        required_args = self.get_required_arguments()

        for arg_name in required_args:
            if not self.arguments.has_argument(arg_name):
                error = ModelValidationError.create_error(
                    message=f"Required argument '{arg_name}' missing for command {self.command_definition.command_name}",
                    field_name=arg_name,
                    error_code="MISSING_REQUIRED_ARGUMENT",
                )
                errors.append(error)

        return errors

    @classmethod
    def create_help_request(
        cls,
        command_definition: ModelCliCommandDefinition,
        target_node: ModelNodeReference,
        raw_command_line: str,
    ) -> "ModelParsedArguments":
        """Create parsed arguments for a help request."""
        return cls(
            arguments=ModelArgumentMap(),
            command_definition=command_definition,
            target_node=target_node,
            is_help_request=True,
            raw_command_line=raw_command_line,
            parsed_successfully=True,
        )

    @classmethod
    def create_version_request(
        cls,
        command_definition: ModelCliCommandDefinition,
        target_node: ModelNodeReference,
        raw_command_line: str,
    ) -> "ModelParsedArguments":
        """Create parsed arguments for a version request."""
        return cls(
            arguments=ModelArgumentMap(),
            command_definition=command_definition,
            target_node=target_node,
            is_version_request=True,
            raw_command_line=raw_command_line,
            parsed_successfully=True,
        )

    @classmethod
    def create_invalid(
        cls,
        command_definition: ModelCliCommandDefinition,
        target_node: ModelNodeReference,
        errors: list[ModelValidationError],
        raw_command_line: str = "",
    ) -> "ModelParsedArguments":
        """Create parsed arguments for invalid input."""
        return cls(
            arguments=ModelArgumentMap(),
            command_definition=command_definition,
            target_node=target_node,
            validation_errors=errors,
            raw_command_line=raw_command_line,
            parsed_successfully=False,
        )
