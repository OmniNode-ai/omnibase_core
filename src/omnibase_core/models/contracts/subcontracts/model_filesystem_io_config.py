"""
Filesystem IO Configuration Model.

Filesystem IO configuration for file operations with path templating,
operation type specification, and atomicity controls.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_TIMEOUT_DEFAULT_MS,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["ModelFilesystemIOConfig"]


class ModelFilesystemIOConfig(BaseModel):
    """
    Filesystem IO configuration for file operations.

    Provides file path templating, operation type specification,
    and atomicity controls for filesystem operations.

    For move/copy operations, both file_path_template (source) and
    destination_path_template (target) are required.

    Attributes:
        handler_type: Discriminator field identifying this as a Filesystem handler.
        file_path_template: File path with ${} placeholders (source for move/copy).
        destination_path_template: Destination path for move/copy operations.
        operation: Filesystem operation type (read, write, delete, move, copy).
        timeout_ms: Operation timeout in milliseconds (1s - 10min).
        atomic: Use atomic operations (write to temp, then rename).
        create_dirs: Create parent directories if they don't exist.
        encoding: Text encoding for file content.
        mode: File permission mode (e.g., '0644').

    Example (write):
        >>> config = ModelFilesystemIOConfig(
        ...     file_path_template="/data/output/${input.date}/${input.filename}.json",
        ...     operation="write",
        ...     atomic=True,
        ...     create_dirs=True,
        ... )

    Example (move):
        >>> config = ModelFilesystemIOConfig(
        ...     file_path_template="/data/inbox/${input.filename}",
        ...     destination_path_template="/data/archive/${input.date}/${input.filename}",
        ...     operation="move",
        ...     create_dirs=True,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    handler_type: Literal[EnumEffectHandlerType.FILESYSTEM] = Field(
        default=EnumEffectHandlerType.FILESYSTEM,
        description="Discriminator field for Filesystem handler",
    )

    file_path_template: str = Field(
        ...,
        description="File path with ${} placeholders for variable substitution. "
        "For move/copy operations, this is the source path.",
        min_length=1,
    )

    destination_path_template: str | None = Field(
        default=None,
        description="Destination path with ${} placeholders for move/copy operations. "
        "Required for 'move' and 'copy' operations, ignored for other operations.",
    )

    operation: Literal["read", "write", "delete", "move", "copy"] = Field(
        ...,
        description="Filesystem operation type",
    )

    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Operation timeout in milliseconds (1s - 10min)",
    )

    atomic: bool = Field(
        default=True,
        description="Use atomic operations (write to temp, then rename)",
    )

    create_dirs: bool = Field(
        default=True,
        description="Create parent directories if they don't exist",
    )

    encoding: str = Field(
        default="utf-8",
        description="Text encoding for file content",
    )

    mode: str | None = Field(
        default=None,
        description="File permission mode (e.g., '0644')",
    )

    @model_validator(mode="after")
    def validate_atomic_for_operation(self) -> "ModelFilesystemIOConfig":
        """
        Validate atomic setting is only applicable to write operations.

        Atomic operations (write to temp file, then rename) only make sense for
        write operations. Enabling atomic=True for read/delete/move/copy operations
        is a configuration error and will raise a validation error.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If atomic=True for non-write operations.
        """
        if self.atomic and self.operation != "write":
            raise ModelOnexError(
                message=f"atomic=True is only valid for 'write' operations, "
                f"not '{self.operation}'",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "atomic_operation_validation"
                        ),
                        "operation": ModelSchemaValue.from_value(self.operation),
                    }
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_destination_for_move_copy(self) -> "ModelFilesystemIOConfig":
        """
        Validate destination_path_template is required for move/copy operations.

        Move and copy operations require both a source path (file_path_template)
        and a destination path (destination_path_template). Without the destination,
        the operation would fail at runtime.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If move/copy operation without destination_path_template.
        """
        operations_requiring_destination = {"move", "copy"}
        if (
            self.operation in operations_requiring_destination
            and self.destination_path_template is None
        ):
            raise ModelOnexError(
                message=f"destination_path_template is required for '{self.operation}' operations",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "destination_path_validation"
                        ),
                        "operation": ModelSchemaValue.from_value(self.operation),
                    }
                ),
            )
        return self
