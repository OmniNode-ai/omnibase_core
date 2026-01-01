"""
Strongly-typed FSM state model.

Replaces dict[str, Any] usage in FSM state operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.

Deep Immutability:
    This model uses frozen=True for Pydantic immutability, and also uses
    immutable types (tuple instead of list, tuple-of-tuples instead of dict)
    for deep immutability. This ensures that nested collections cannot be
    modified after construction.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.utils.util_validators import (
    convert_dict_to_frozen_pairs,
    convert_list_to_tuple,
)


class ModelFsmState(BaseModel):
    """
    Strongly-typed FSM state with deep immutability.

    Represents a single state in a finite state machine, including its
    entry/exit actions and custom properties.

    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    Deep Immutability:
        All collection fields use immutable types:
        - entry_actions/exit_actions: tuple instead of list
        - properties: tuple[tuple[str, str], ...] instead of dict

        Validators automatically convert incoming lists/dicts to frozen types
        for convenience during model construction.

    Thread Safety:
        This model uses frozen=True and deeply immutable types (tuples), making it
        fully thread-safe for concurrent access from multiple threads or async tasks.

        - **Safe**: Reading any field from multiple threads simultaneously
        - **Safe**: Passing instances between threads without synchronization
        - **Safe**: Using instances as dict keys or set members (hashable)

        This is one of the few models that provides true deep immutability.

    Accessing dict-like fields:
        For properties, use dict() to convert back:
        >>> state = ModelFsmState(name="example", properties={"key": "value"})
        >>> props_dict = dict(state.properties)  # Convert to dict for lookup

    Attributes:
        name: Unique state identifier (required).
        description: Human-readable description of the state.
        is_initial: Whether this is the initial/starting state.
        is_final: Whether this is a terminal/accepting state.
        entry_actions: Tuple of action names to execute on state entry.
        exit_actions: Tuple of action names to execute on state exit.
        properties: Tuple of key-value pairs for custom state properties.
    """

    name: str = Field(default=..., description="State name")
    description: str = Field(default="", description="State description")
    is_initial: bool = Field(
        default=False, description="Whether this is the initial state"
    )
    is_final: bool = Field(default=False, description="Whether this is a final state")
    entry_actions: tuple[str, ...] = Field(
        default=(), description="Actions on state entry (immutable)"
    )
    exit_actions: tuple[str, ...] = Field(
        default=(), description="Actions on state exit (immutable)"
    )
    properties: tuple[tuple[str, str], ...] = Field(
        default=(), description="State properties as frozen key-value pairs"
    )

    @field_validator("entry_actions", mode="before")
    @classmethod
    def _convert_entry_actions_to_tuple(
        cls, v: list[str] | tuple[str, ...] | object
    ) -> tuple[str, ...]:
        """Convert list of entry actions to tuple for deep immutability."""
        return convert_list_to_tuple(v)

    @field_validator("exit_actions", mode="before")
    @classmethod
    def _convert_exit_actions_to_tuple(
        cls, v: list[str] | tuple[str, ...] | object
    ) -> tuple[str, ...]:
        """Convert list of exit actions to tuple for deep immutability."""
        return convert_list_to_tuple(v)

    @field_validator("properties", mode="before")
    @classmethod
    def _convert_properties_to_frozen(
        cls, v: dict[str, str] | tuple[tuple[str, str], ...] | object
    ) -> tuple[tuple[str, str], ...]:
        """Convert dict to tuple of tuples for deep immutability.

        Keys are sorted for deterministic ordering, which ensures consistent
        hashing and comparison of model instances.
        """
        return convert_dict_to_frozen_pairs(v, sort_keys=True)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        frozen=True,
        from_attributes=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Note: In v1.0, this method returns True without modification.
        The model is frozen (immutable) for thread safety.
        """
        # v1.0: Model is frozen, so setattr is not allowed
        _ = kwargs  # Explicitly mark as unused
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Validates that required fields have valid values:
        - name must be a non-empty, non-whitespace string

        Returns:
            bool: True if validation passed, False otherwise
        """
        # Validate name is non-empty and non-whitespace
        if not self.name or not self.name.strip():
            return False
        return True


# Export for use
__all__ = ["ModelFsmState"]
