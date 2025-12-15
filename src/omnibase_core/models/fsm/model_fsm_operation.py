"""
Reserved FSM operation model for v1.1+ operation definitions.

This model is reserved for future use in v1.1+ of the ONEX NodeReducer.
It defines operation configurations that will be used for advanced
FSM operation handling.

Note:
    This model is part of the forward-compatibility design. Do not use
    in production until v1.1+ is released.

Spec Reference:
    CONTRACT_DRIVEN_NODEREDUCER_V1_0.md: Reserved fields section
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelFSMOperation(BaseModel):
    """
    Reserved FSM operation model for v1.1+ operation definitions.

    This model defines operation configurations for advanced FSM operation
    handling in future NodeReducer versions. It is part of the ONEX
    forward-compatibility design.

    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    Warning:
        This model is RESERVED for v1.1+. Do not use in production
        until the v1.1 release.

    Attributes:
        operation_name: Unique operation identifier (required). Must be non-empty.
        operation_type: Type of operation (required). Must be non-empty.
            Common values: "synchronous", "asynchronous", "batch".
        description: Human-readable description (optional).
        requires_atomic_execution: Whether this operation requires atomic execution
            guarantees. Critical operations (transition, snapshot, restore) should
            set this to True.
        supports_rollback: Whether this operation supports rollback on failure.
            Critical operations should set this to True for error recovery.

    Planned Fields (v1.1+):
        The following fields are planned for v1.1+ but NOT YET IMPLEMENTED
        in this model:
        - retry_count: Number of retry attempts for failed operations
        - timeout_ms: Operation timeout in milliseconds
        - rollback_action: Action to execute on operation failure

    Example:
        >>> operation = ModelFSMOperation(
        ...     operation_name="validate_input",
        ...     operation_type="synchronous",
        ...     description="Validates input data before processing"
        ... )
        >>> operation.operation_name
        'validate_input'

    Spec Reference:
        CONTRACT_DRIVEN_NODEREDUCER_V1_0.md: Reserved fields section
    """

    operation_name: str = Field(
        min_length=1,
        description="Unique operation identifier",
    )
    operation_type: str = Field(
        min_length=1,
        description="Type of operation (e.g., synchronous, asynchronous, batch)",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of the operation",
    )
    requires_atomic_execution: bool = Field(
        default=False,
        description="Whether this operation requires atomic execution guarantees",
    )
    supports_rollback: bool = Field(
        default=False,
        description="Whether this operation supports rollback on failure",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        frozen=True,
        from_attributes=True,
    )

    # Protocol method implementations

    def execute(self, **_kwargs: object) -> bool:
        """Execute the operation (Executable protocol).

        Reserved for v1.1+ implementation. This method is a placeholder
        for future operation execution logic that will handle retry,
        timeout, and rollback behaviors.

        Note:
            This model is frozen (immutable). Execution in v1.1+ will
            return a new model instance with updated state rather than
            modifying this instance in place.

        Args:
            **_kwargs: Reserved for v1.1+ execution parameters (currently unused)

        Returns:
            bool: Always returns True (placeholder behavior)

        Future (v1.1+):
            - Implement actual execution logic
            - Add retry handling based on retry_count
            - Add timeout handling based on timeout_ms
            - Add rollback handling based on rollback_action
        """
        # v1.1+ reserved: actual execution logic will be implemented here
        # Model is frozen, so no in-place mutation is possible
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol).

        Returns:
            dict[str, object]: Dictionary representation of the model
        """
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Performs validation to ensure required fields have valid values.
        Checks that operation_name and operation_type are non-empty and
        non-whitespace-only strings.

        Note:
            Empty strings are now rejected at Pydantic validation level
            (min_length=1). This method provides additional validation for
            whitespace-only strings which pass Pydantic validation but are
            semantically invalid.

        Returns:
            bool: True if validation passed, False otherwise

        Example:
            >>> op = ModelFSMOperation(operation_name="test", operation_type="sync")
            >>> op.validate_instance()
            True
            >>> op2 = ModelFSMOperation(operation_name="  ", operation_type="sync")
            >>> op2.validate_instance()  # Whitespace-only fails validate_instance
            False
        """
        # Validate operation_name is non-empty
        if not self.operation_name or not self.operation_name.strip():
            return False

        # Validate operation_type is non-empty
        if not self.operation_type or not self.operation_type.strip():
            return False

        return True


# Export for use
__all__ = ["ModelFSMOperation"]
