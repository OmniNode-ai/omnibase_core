from typing import Any, List, Optional

from pydantic import Field, model_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

"""
Model for state updates in tool-based state management.

This model represents state updates that can be applied to the current state
as part of contract-driven state transitions.
"""

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_state_update_operation import (
    EnumStateUpdateOperation,
)
from omnibase_core.models.core.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_state_field_update import ModelStateFieldUpdate

# ModelStateFieldUpdate has been extracted to model_state_field_update.py


class ModelStateUpdate(BaseModel):
    """
    Represents a state update that can be applied to the current state.

    This model is returned by state computation tools and applied by
    the generated reducer to update the node's state.
    """

    # Field updates to apply
    field_updates: list[ModelStateFieldUpdate] = Field(
        default_factory=list,
        description="List of field updates to apply to the state",
    )

    # Metadata about the update
    update_id: str | None = Field(
        None,
        description="Unique identifier for this update (for tracking/debugging)",
    )

    update_source: str | None = Field(
        None,
        description="Tool or component that generated this update",
    )

    update_timestamp: str | None = Field(
        None,
        description="ISO timestamp when update was generated",
    )

    # Validation and constraints
    requires_validation: bool = Field(
        default=True,
        description="Whether state validation should run after applying update",
    )

    validation_rules: list[str] | None = Field(
        None,
        description="Specific validation rules to run (None means run all)",
    )

    # Side effects and notifications
    emit_events: list[dict[str, str]] | None = Field(
        None,
        description="Events to emit after successful state update",
    )

    log_messages: list[str] | None = Field(
        None,
        description="Messages to log when applying update",
    )

    # Error handling
    rollback_on_error: bool = Field(
        default=True,
        description="Whether to rollback all changes if any update fails",
    )

    error_strategy: str | None = Field(
        None,
        description="How to handle errors: 'fail', 'skip', 'retry'",
    )

    def add_field_update(
        self,
        field_path: str,
        operation: EnumStateUpdateOperation | str,
        value: ModelSchemaValue | None = None,
        condition: str | None = None,
    ) -> None:
        """Add a field update to this state update."""
        if isinstance(operation, str):
            operation = EnumStateUpdateOperation(operation)

        # Convert raw value to ModelSchemaValue if needed
        if value is not None and not isinstance(value, ModelSchemaValue):
            value = ModelSchemaValue.from_value(value)

        update = ModelStateFieldUpdate(
            field_path=field_path,
            operation=operation,
            value=value,
            condition=condition,
        )
        self.field_updates.append(update)

    def set_field(
        self,
        field_path: str,
        value: (
            ModelSchemaValue
            | int
            | float
            | str
            | bool
            | list[Any]
            | dict[str, Any]
            | None
        ),
        condition: str | None = None,
    ) -> None:
        """Convenience method to set a field value."""
        # Convert to ModelSchemaValue if needed
        if not isinstance(value, ModelSchemaValue) and value is not None:
            value = ModelSchemaValue.from_value(value)
        self.add_field_update(
            field_path,
            EnumStateUpdateOperation.SET,
            value,
            condition,
        )

    def delete_field(self, field_path: str, condition: str | None = None) -> None:
        """Convenience method to delete a field."""
        self.add_field_update(
            field_path,
            EnumStateUpdateOperation.DELETE,
            None,
            condition,
        )

    def increment_field(
        self,
        field_path: str,
        amount: int | float = 1,
        condition: str | None = None,
    ) -> None:
        """Convenience method to increment a numeric field."""
        # Convert to ModelSchemaValue
        schema_value = ModelSchemaValue.from_value(amount)
        self.add_field_update(
            field_path,
            EnumStateUpdateOperation.INCREMENT,
            schema_value,
            condition,
        )

    def merge_field(
        self,
        field_path: str,
        value: dict[str, str | int | float | bool],
        condition: str | None = None,
    ) -> None:
        """Convenience method to merge a dict[str, Any]ionary field."""
        # Convert to ModelSchemaValue
        schema_value = ModelSchemaValue.from_value(value)
        self.add_field_update(
            field_path,
            EnumStateUpdateOperation.MERGE,
            schema_value,
            condition,
        )

    def append_to_field(
        self,
        field_path: str,
        value: (
            ModelSchemaValue
            | int
            | float
            | str
            | bool
            | list[Any]
            | dict[str, Any]
            | None
        ),
        condition: str | None = None,
    ) -> None:
        """Convenience method to append to a list[Any]field."""
        # Convert to ModelSchemaValue if needed
        if not isinstance(value, ModelSchemaValue) and value is not None:
            value = ModelSchemaValue.from_value(value)
        self.add_field_update(
            field_path,
            EnumStateUpdateOperation.APPEND,
            value,
            condition,
        )

    @classmethod
    def create_empty(cls) -> "ModelStateUpdate":
        """Create an empty state update (no changes)."""
        return cls(field_updates=[])

    def is_empty(self) -> bool:
        """Check if this update has any field updates."""
        return len(self.field_updates) == 0
