"""
Simple Tool Execution Result Model.

Domain-specific result model for tool execution results.
Replaces the generic ModelExecutionResult with a focused tool-specific model.

Strict typing is enforced: No Any types allowed in implementation.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field, model_validator

from omnibase_core.types.constraints import PrimitiveValueType

# Type aliases for structured data
StructuredData = dict[str, PrimitiveValueType]


class ModelToolExecutionResult(BaseModel):
    """
    Simple tool execution result for ONEX tools.

    Provides tool-specific execution results with success/failure tracking,
    output data, and error handling.

    Strict typing is enforced: No Any types allowed.

    Success Tracking - Single Source of Truth:
        The `success` field is the CANONICAL source of truth for execution status.
        Use `result.success` or `result.is_success` for all success checks.

        A model validator enforces consistency between related fields:
        - When `success=True`: `error` must be None
        - When `success=False`: `error` should contain a message (warning if missing)
        - `status_code` provides granular error classification (0=success, >0=error codes)

    Field Relationships:
        - success: Boolean indicating overall execution success/failure.
          This is the authoritative field - use for all conditional logic.
        - error: Error message string, must be None when success=True.
        - status_code: Numeric code providing granular error classification.
          0 indicates success, values >0 represent specific error categories.
          Use when you need to distinguish between different failure modes
          (e.g., 1=validation error, 2=timeout, 3=resource not found).

    Example:
        >>> result = ModelToolExecutionResult(tool_name="my_tool", success=True)
        >>> if result.success:  # Canonical way to check success
        ...     print("Success!")
    """

    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique execution identifier",
    )

    tool_name: str = Field(default=..., description="Name of the executed tool")

    success: bool = Field(
        default=..., description="Whether the tool execution succeeded"
    )

    output: StructuredData = Field(
        default_factory=dict,
        description="Tool execution output data",
    )

    error: str | None = Field(
        default=None,
        description="Error message if tool execution failed",
    )

    execution_time_ms: int = Field(
        default=0,
        description="Execution duration in milliseconds",
        ge=0,
    )

    status_code: int = Field(
        default=0,
        description="Tool execution status code (0=success, >0=error codes)",
        ge=0,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    @model_validator(mode="after")
    def _ensure_success_consistency(self) -> "ModelToolExecutionResult":
        """Ensure consistency between success flag and error field.

        This validator enforces the single source of truth principle:
        - If success=True, error must be None (raises ValueError if not)
        - If success=False and error is None, sets a default error message

        Returns:
            Self with consistent state.

        Raises:
            ValueError: If success=True but error is not None.
        """
        if self.success and self.error is not None:
            raise ValueError(
                f"Inconsistent state: success=True but error is set to '{self.error}'. "
                "When success=True, error must be None."
            )

        # If failure but no error message, set a default
        if not self.success and self.error is None:
            # Use object.__setattr__ to bypass frozen validation during construction
            object.__setattr__(
                self, "error", "Execution failed (no error message provided)"
            )

        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_success(self) -> bool:
        """Single source of truth for execution success.

        This computed property consolidates success tracking by using
        the `success` field as the canonical source of truth.

        Returns:
            bool: True if execution succeeded, False otherwise.

        Note:
            The `success` field is the authoritative indicator.
            The `status_code` field provides additional context (e.g., HTTP codes)
            but does not determine success/failure on its own.
        """
        return self.success

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_failure(self) -> bool:
        """Convenience property for checking failure state.

        Returns:
            bool: True if execution failed, False otherwise.
        """
        return not self.success


__all__ = ["ModelToolExecutionResult"]
