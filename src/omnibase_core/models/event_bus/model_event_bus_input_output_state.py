"""Event Bus Input/Output State Composite Model.

This module provides a composite model that combines the input and output states
for event bus operations, enabling unified handling of both states.

Thread Safety:
    ModelEventBusInputOutputState instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.typed_dict_operation_summary import TypedDictOperationSummary

from .model_event_bus_input_state import ModelEventBusInputState
from .model_event_bus_output_state import ModelEventBusOutputState


class ModelEventBusInputOutputState(BaseModel):
    """
    Composite model combining input and output states for event bus operations.

    This model provides a unified interface for handling both the input and output
    states of event bus operations, useful for testing, validation, and workflow
    management scenarios.

    Features:
    - Type-safe composition of input and output states
    - Unified validation and serialization
    - Clear separation of concerns while enabling joint operations

    Attributes:
        input_state: The input state for the event bus operation.
        output_state: The output state for the event bus operation.
    """

    # Note on frozen=True: This composite state is immutable to prevent accidental
    # mutation after creation.
    # Note on from_attributes=True: Added for pytest-xdist parallel execution
    # compatibility. See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    input_state: ModelEventBusInputState = Field(
        ..., description="Input state for the event bus operation"
    )
    output_state: ModelEventBusOutputState = Field(
        ..., description="Output state for the event bus operation"
    )

    def is_successful(self) -> bool:
        """Check if the operation was successful based on output state."""
        return self.output_state.status == EnumOnexStatus.SUCCESS

    def get_version_match(self) -> bool:
        """Check if input and output versions match."""
        return str(self.input_state.version) == str(self.output_state.version)

    def get_operation_summary(self) -> TypedDictOperationSummary:
        """Get a summary of the operation for logging/monitoring."""
        return TypedDictOperationSummary(
            input_version=str(self.input_state.version),
            output_version=str(self.output_state.version),
            status=self.output_state.status.value,
            message=self.output_state.message,
            version_match=self.get_version_match(),
            successful=self.is_successful(),
        )

    @classmethod
    def create_from_versions(
        cls,
        input_version: ModelSemVer | str,
        output_version: ModelSemVer | str,
        input_field: str,
        status: EnumOnexStatus | str,
        message: str,
    ) -> "ModelEventBusInputOutputState":
        """Create a composite state from basic parameters.

        Args:
            input_version: Version for the input state.
            output_version: Version for the output state.
            input_field: The input field value.
            status: The status for the output state.
            message: The message for the output state.

        Returns:
            A new composite input/output state.
        """
        from omnibase_core.models.primitives.model_semver import (
            parse_semver_from_string,
        )

        # Convert ModelSemVer to str if needed before parsing
        input_version_str = (
            str(input_version)
            if isinstance(input_version, ModelSemVer)
            else input_version
        )
        output_version_str = (
            str(output_version)
            if isinstance(output_version, ModelSemVer)
            else output_version
        )

        input_state = ModelEventBusInputState(
            version=parse_semver_from_string(input_version_str), input_field=input_field
        )
        # Normalize status to EnumOnexStatus
        status_enum = (
            status if isinstance(status, EnumOnexStatus) else EnumOnexStatus(status)
        )
        output_state = ModelEventBusOutputState(
            version=parse_semver_from_string(output_version_str),
            status=status_enum,
            message=message,
        )
        return cls(input_state=input_state, output_state=output_state)

    @classmethod
    def create_successful(
        cls,
        version: ModelSemVer | str,
        input_field: str,
        message: str = "Operation completed successfully",
    ) -> "ModelEventBusInputOutputState":
        """Create a successful operation state.

        Args:
            version: Version for both input and output states.
            input_field: The input field value.
            message: Success message.

        Returns:
            A new composite state with SUCCESS status.
        """
        return cls.create_from_versions(
            input_version=version,
            output_version=version,
            input_field=input_field,
            status=EnumOnexStatus.SUCCESS,
            message=message,
        )

    @classmethod
    def create_failed(
        cls, version: ModelSemVer | str, input_field: str, error_message: str
    ) -> "ModelEventBusInputOutputState":
        """Create a failed operation state.

        Args:
            version: Version for both input and output states.
            input_field: The input field value.
            error_message: Error description.

        Returns:
            A new composite state with ERROR status.
        """
        return cls.create_from_versions(
            input_version=version,
            output_version=version,
            input_field=input_field,
            status=EnumOnexStatus.ERROR,
            message=error_message,
        )


__all__ = ["ModelEventBusInputOutputState"]
