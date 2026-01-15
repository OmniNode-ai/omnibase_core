"""
Resolved Filesystem Context Model for NodeEffect Handler Contract.

This model represents a resolved (template-free) filesystem context that handlers receive
after template resolution by the effect executor.

Thread Safety:
    This model is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

See Also:
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_TIMEOUT_DEFAULT_MS,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


class ModelResolvedFilesystemContext(BaseModel):
    """
    Resolved filesystem context for file and directory operations.

    All template placeholders have been resolved by the effect executor.
    File paths and content are ready for immediate I/O operations.

    Attributes:
        handler_type: Discriminator field for filesystem handler type.
        file_path: Fully resolved file path (no template placeholders).
        operation: Filesystem operation type (read, write, delete, move, copy).
        content: Resolved content for write operations.
        timeout_ms: Operation timeout in milliseconds (1s - 10min).
        atomic: Whether to use atomic write operations (write to temp, then rename).
        create_dirs: Whether to create parent directories if they don't exist.
        encoding: File encoding for text operations.
        mode: Unix file mode (e.g., '0644') for created files.

    Example resolved values:
        - file_path: "/data/exports/report_2024.csv" (was: "${DATA_DIR}/exports/${filename}")
        - content: "id,name,value\\n123,test,100" (was: "${HEADER}\\n${ROW_DATA}")
    """

    handler_type: Literal[EnumEffectHandlerType.FILESYSTEM] = Field(
        default=EnumEffectHandlerType.FILESYSTEM,
        description="Handler type discriminator for filesystem operations",
    )

    file_path: str = Field(
        ...,
        min_length=1,
        description="Fully resolved file path (no template placeholders)",
    )

    operation: Literal["read", "write", "delete", "move", "copy"] = Field(
        ...,
        description="Filesystem operation type",
    )

    content: str | None = Field(
        default=None,
        description="Resolved content for write operations",
    )

    # Timeout bounds: 1s minimum (realistic production I/O), 10min maximum
    # Matches IO config timeout bounds for consistency across the effect layer
    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Operation timeout in milliseconds (1s - 10min)",
    )

    atomic: bool = Field(
        default=True,
        description="Whether to use atomic write operations (write to temp, then rename)",
    )

    create_dirs: bool = Field(
        default=True,
        description="Whether to create parent directories if they don't exist",
    )

    encoding: str = Field(
        default="utf-8",
        description="File encoding for text operations",
    )

    mode: str | None = Field(
        default=None,
        description="Unix file mode (e.g., '0644') for created files",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )
