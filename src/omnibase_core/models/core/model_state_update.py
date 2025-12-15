"""
Model for state updates in tool-based state management.

This model represents state updates that can be applied to the current state
as part of contract-driven state transitions.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_state_update_operation import EnumStateUpdateOperation
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_state_field_update import ModelStateFieldUpdate
from omnibase_core.types.type_serializable_value import SerializableValue

# ModelStateFieldUpdate has been extracted to model_state_field_update.py


class ModelStateUpdate(BaseModel):
    """
    Represents a state update that can be applied to the current state.

    This model is returned by state computation tools and applied by
    the generated reducer to update the node's state.

    Thread Safety:
        This model is NOT thread-safe due to mutable fields (field_updates list)
        and methods that mutate state (add_field_update, set_field, etc.).

        - **NOT Safe**: Sharing instances across threads without synchronization
        - **NOT Safe**: Calling mutating methods from multiple threads concurrently
        - **Safe**: Reading fields after all mutations complete (before sharing)

        For thread-safe usage:
        1. Build the complete state update in a single thread before sharing
        2. Use external synchronization if building collaboratively across threads
        3. Create new instances rather than modifying shared ones

        See docs/guides/THREADING.md for thread-safe patterns.
    """

    # Field updates to apply
    field_updates: list[ModelStateFieldUpdate] = Field(
        default_factory=list,
        description="List of field updates to apply to the state",
    )

    # Metadata about the update
    update_id: UUID | None = Field(
        default=None,
        description="Unique identifier for this update (for tracking/debugging)",
    )

    update_source: str | None = Field(
        default=None,
        description="Tool or component that generated this update",
    )

    update_timestamp: str | None = Field(
        default=None,
        description="ISO timestamp when update was generated",
    )

    # Validation and constraints
    requires_validation: bool = Field(
        default=True,
        description="Whether state validation should run after applying update",
    )

    validation_rules: list[str] | None = Field(
        default=None,
        description="Specific validation rules to run (None means run all)",
    )

    # Side effects and notifications
    emit_events: list[dict[str, str]] | None = Field(
        default=None,
        description="Events to emit after successful state update",
    )

    log_messages: list[str] | None = Field(
        default=None,
        description="Messages to log when applying update",
    )

    # Error handling
    rollback_on_error: bool = Field(
        default=True,
        description="Whether to rollback all changes if any update fails",
    )

    error_strategy: str | None = Field(
        default=None,
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
        value: ModelSchemaValue | SerializableValue,
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
        """Convenience method to merge a dictionary field."""
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
        value: ModelSchemaValue | SerializableValue,
        condition: str | None = None,
    ) -> None:
        """Convenience method to append to a list field."""
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
