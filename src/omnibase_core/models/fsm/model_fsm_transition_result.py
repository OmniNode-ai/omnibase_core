"""
FSM transition result model.

Contains the result of an FSM transition execution, including the outcome,
state changes, intents for side effects, and execution metadata.

Deep Immutability:
    This model uses frozen=True for Pydantic immutability, and also uses
    immutable types (tuple instead of list) for deep immutability. This
    ensures that nested collections cannot be modified after construction.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.types.type_serializable_value import SerializableValue


class ModelFSMTransitionResult(BaseModel):
    """
    Result of FSM transition execution with deep immutability.

    Pure data structure containing transition outcome and intents for side effects.
    Implements frozen Pydantic model pattern for thread safety.

    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    Deep Immutability:
        All collection fields use immutable types:
        - intents: tuple[ModelIntent, ...] instead of list[ModelIntent]
        - metadata: tuple[tuple[str, SerializableValue], ...] instead of dict

        Validators automatically convert incoming lists/dicts to frozen types
        for convenience during model construction.

    Accessing dict-like fields:
        For metadata, use dict() to convert back:
        >>> result = ModelFSMTransitionResult(...)
        >>> meta_dict = dict(result.metadata)  # Convert to dict for lookup

    Attributes:
        success: Whether the transition succeeded.
        new_state: Name of the resulting state after transition.
        old_state: Name of the state before transition.
        transition_name: Name of the transition executed, or None if failed.
        intents: Tuple of intents generated for side effect execution.
        metadata: Tuple of key-value pairs for execution metadata.
        error: Error message if the transition failed, None otherwise.
        timestamp: ISO-format timestamp of when the result was created.
    """

    success: bool = Field(
        default=...,
        description="Whether the transition succeeded",
    )
    new_state: str = Field(
        default=...,
        description="Resulting state name after transition",
    )
    old_state: str = Field(
        default=...,
        description="Previous state name before transition",
    )
    transition_name: str | None = Field(
        default=None,
        description="Name of transition executed (None if failed)",
    )
    intents: tuple[ModelIntent, ...] = Field(
        default=(),
        description="Intents for side effects (immutable)",
    )
    metadata: tuple[tuple[str, SerializableValue], ...] = Field(
        default=(),
        description="Execution metadata as frozen key-value pairs",
    )
    error: str | None = Field(
        default=None,
        description="Error message if transition failed",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO-format timestamp of result creation",
    )

    @field_validator("intents", mode="before")
    @classmethod
    def _convert_intents_to_tuple(
        cls, v: list[Any] | tuple[Any, ...] | Any
    ) -> tuple[Any, ...]:
        """Convert list of intents to tuple for deep immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def _convert_metadata_to_frozen(
        cls,
        v: dict[str, SerializableValue]
        | tuple[tuple[str, SerializableValue], ...]
        | None,
    ) -> tuple[tuple[str, SerializableValue], ...]:
        """Convert dict to tuple of tuples for deep immutability."""
        if v is None:
            return ()
        if isinstance(v, dict):
            return tuple(v.items())
        return v

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=False,
    )

    # Protocol method implementations

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol).

        Returns:
            dict[str, object]: Dictionary representation of the model
        """
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Performs validation to ensure required fields have valid values:
        - new_state must be a non-empty, non-whitespace string
        - old_state must be a non-empty, non-whitespace string
        - If success is False, error should typically be set

        Returns:
            bool: True if validation passed, False otherwise
        """
        # Validate new_state is non-empty
        if not self.new_state or not self.new_state.strip():
            return False

        # Validate old_state is non-empty
        if not self.old_state or not self.old_state.strip():
            return False

        return True


__all__ = ["ModelFSMTransitionResult"]
