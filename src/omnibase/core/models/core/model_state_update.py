"""
Model for state updates in tool-based state management.

This model represents state updates that can be applied to the current state
as part of contract-driven state transitions.
"""

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator

from omnibase.model.core.model_schema_value import ModelSchemaValue


class EnumStateUpdateOperation(str, Enum):
    """Operations that can be performed on state fields."""

    SET = "set"  # Replace field value
    MERGE = "merge"  # Merge with existing value (for dicts)
    APPEND = "append"  # Append to list
    INCREMENT = "increment"  # Increment numeric value
    DECREMENT = "decrement"  # Decrement numeric value
    DELETE = "delete"  # Remove field from state


class ModelStateFieldUpdate(BaseModel):
    """Update for a single state field."""

    field_path: str = Field(
        ..., description="Dot-separated path to the field (e.g., 'user.profile.name')"
    )
    operation: EnumStateUpdateOperation = Field(
        ..., description="Operation to perform on the field"
    )
    value: Optional[ModelSchemaValue] = Field(
        None, description="Value to use in the operation (not needed for DELETE)"
    )
    condition: Optional[str] = Field(
        None,
        description="Optional condition expression that must be true for update to apply",
    )

    @model_validator(mode="after")
    def validate_value_for_operation(self) -> "ModelStateFieldUpdate":
        """Validate that value is appropriate for the operation."""
        if self.operation == EnumStateUpdateOperation.DELETE and self.value is not None:
            raise ValueError("DELETE operation should not have a value")

        if self.operation in [
            EnumStateUpdateOperation.INCREMENT,
            EnumStateUpdateOperation.DECREMENT,
        ]:
            if self.value is not None:
                # Check if the value is numeric when converted
                actual_value = self.value.to_value()
                if not isinstance(actual_value, (int, float)):
                    raise ValueError(
                        f"{self.operation} operation requires numeric value or None"
                    )

        return self


class ModelStateUpdate(BaseModel):
    """
    Represents a state update that can be applied to the current state.

    This model is returned by state computation tools and applied by
    the generated reducer to update the node's state.
    """

    # Field updates to apply
    field_updates: List[ModelStateFieldUpdate] = Field(
        default_factory=list, description="List of field updates to apply to the state"
    )

    # Metadata about the update
    update_id: Optional[str] = Field(
        None, description="Unique identifier for this update (for tracking/debugging)"
    )

    update_source: Optional[str] = Field(
        None, description="Tool or component that generated this update"
    )

    update_timestamp: Optional[str] = Field(
        None, description="ISO timestamp when update was generated"
    )

    # Validation and constraints
    requires_validation: bool = Field(
        default=True,
        description="Whether state validation should run after applying update",
    )

    validation_rules: Optional[List[str]] = Field(
        None, description="Specific validation rules to run (None means run all)"
    )

    # Side effects and notifications
    emit_events: Optional[List[Dict[str, str]]] = Field(
        None, description="Events to emit after successful state update"
    )

    log_messages: Optional[List[str]] = Field(
        None, description="Messages to log when applying update"
    )

    # Error handling
    rollback_on_error: bool = Field(
        default=True, description="Whether to rollback all changes if any update fails"
    )

    error_strategy: Optional[str] = Field(
        None, description="How to handle errors: 'fail', 'skip', 'retry'"
    )

    def add_field_update(
        self,
        field_path: str,
        operation: Union[EnumStateUpdateOperation, str],
        value: Optional[ModelSchemaValue] = None,
        condition: Optional[str] = None,
    ) -> None:
        """Add a field update to this state update."""
        if isinstance(operation, str):
            operation = EnumStateUpdateOperation(operation)

        # Convert raw value to ModelSchemaValue if needed
        if value is not None and not isinstance(value, ModelSchemaValue):
            value = ModelSchemaValue.from_value(value)

        update = ModelStateFieldUpdate(
            field_path=field_path, operation=operation, value=value, condition=condition
        )
        self.field_updates.append(update)

    def set_field(
        self,
        field_path: str,
        value: Union[ModelSchemaValue, int, float, str, bool, list, dict, None],
        condition: Optional[str] = None,
    ) -> None:
        """Convenience method to set a field value."""
        # Convert to ModelSchemaValue if needed
        if not isinstance(value, ModelSchemaValue) and value is not None:
            value = ModelSchemaValue.from_value(value)
        self.add_field_update(
            field_path, EnumStateUpdateOperation.SET, value, condition
        )

    def delete_field(self, field_path: str, condition: Optional[str] = None) -> None:
        """Convenience method to delete a field."""
        self.add_field_update(
            field_path, EnumStateUpdateOperation.DELETE, None, condition
        )

    def increment_field(
        self,
        field_path: str,
        amount: Union[int, float] = 1,
        condition: Optional[str] = None,
    ) -> None:
        """Convenience method to increment a numeric field."""
        self.add_field_update(
            field_path, EnumStateUpdateOperation.INCREMENT, amount, condition
        )

    def merge_field(
        self,
        field_path: str,
        value: Dict[str, Union[str, int, float, bool]],
        condition: Optional[str] = None,
    ) -> None:
        """Convenience method to merge a dictionary field."""
        # Convert to ModelSchemaValue
        schema_value = ModelSchemaValue.from_value(value)
        self.add_field_update(
            field_path, EnumStateUpdateOperation.MERGE, schema_value, condition
        )

    def append_to_field(
        self,
        field_path: str,
        value: Union[ModelSchemaValue, int, float, str, bool, list, dict, None],
        condition: Optional[str] = None,
    ) -> None:
        """Convenience method to append to a list field."""
        # Convert to ModelSchemaValue if needed
        if not isinstance(value, ModelSchemaValue) and value is not None:
            value = ModelSchemaValue.from_value(value)
        self.add_field_update(
            field_path, EnumStateUpdateOperation.APPEND, value, condition
        )

    @classmethod
    def create_empty(cls) -> "ModelStateUpdate":
        """Create an empty state update (no changes)."""
        return cls(field_updates=[])

    def is_empty(self) -> bool:
        """Check if this update has any field updates."""
        return len(self.field_updates) == 0
