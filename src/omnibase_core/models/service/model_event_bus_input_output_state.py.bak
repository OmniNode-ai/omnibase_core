from typing import Any

from pydantic import Field

"""
Event Bus Input/Output State Composite Model.

This module provides a composite model that combines the input and output states
for event bus operations, enabling unified handling of both states.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus

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
    """

    input_state: ModelEventBusInputState = Field(
        ...,
        description="Input state for the event bus operation",
    )

    output_state: ModelEventBusOutputState = Field(
        ...,
        description="Output state for the event bus operation",
    )

    # === Utility Methods ===

    def is_successful(self) -> bool:
        """Check if the operation was successful based on output state."""
        return self.output_state.status.value == "success"

    def get_version_match(self) -> bool:
        """Check if input and output versions match."""
        return str(self.input_state.version) == str(self.output_state.version)

    def get_operation_summary(self) -> dict[str, Any]:
        """Get a summary of the operation for logging/monitoring."""
        return {
            "input_version": str(self.input_state.version),
            "output_version": str(self.output_state.version),
            "status": self.output_state.status.value,
            "message": self.output_state.message,
            "version_match": self.get_version_match(),
            "successful": self.is_successful(),
        }

    # === Factory Methods ===

    @classmethod
    def create_from_versions(
        cls,
        input_version: str,
        output_version: str,
        input_field: str,
        status: str,
        message: str,
    ) -> "ModelEventBusInputOutputState":
        """Create a composite state from basic parameters."""
        from omnibase_core.enums.onex_status import OnexStatus

        input_state = ModelEventBusInputState(
            version=input_version,
            input_field=input_field,
        )

        output_state = ModelEventBusOutputState(
            version=output_version,
            status=OnexStatus(status),
            message=message,
        )

        return cls(input_state=input_state, output_state=output_state)

    @classmethod
    def create_successful(
        cls,
        version: str,
        input_field: str,
        message: str = "Operation completed successfully",
    ) -> "ModelEventBusInputOutputState":
        """Create a successful operation state."""
        return cls.create_from_versions(
            input_version=version,
            output_version=version,
            input_field=input_field,
            status=EnumOnexStatus.SUCCESS,
            message=message,
        )

    @classmethod
    def create_failed(
        cls,
        version: str,
        input_field: str,
        error_message: str,
    ) -> "ModelEventBusInputOutputState":
        """Create a failed operation state."""
        return cls.create_from_versions(
            input_version=version,
            output_version=version,
            input_field=input_field,
            status="error",
            message=error_message,
        )
