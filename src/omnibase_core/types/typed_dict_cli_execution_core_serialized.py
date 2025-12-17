"""
TypedDict for CLI execution core serialization output.

Strongly-typed representation for ModelCliExecutionCore.serialize() return value.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from omnibase_core.types.typed_dict_cli_command_option_serialized import (
        TypedDictCliCommandOptionSerialized,
    )


class TypedDictCliExecutionCoreSerialized(TypedDict):
    """
    Strongly-typed representation of ModelCliExecutionCore.serialize() output.

    This replaces dict[str, Any] with proper type safety for serialization output.
    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # Execution identification - UUID serialized as string
    execution_id: str

    # Command information - UUID serialized as string
    command_name_id: str
    command_display_name: str | None
    command_args: list[str]
    command_options: dict[str, TypedDictCliCommandOptionSerialized]

    # Target information - UUID serialized as string, Path as string
    target_node_id: str | None
    target_node_display_name: str | None
    target_path: str | None

    # Execution state - enum serialized as string
    status: str
    current_phase: str | None

    # Timing information - datetime serialized as ISO string
    start_time: str
    end_time: str | None

    # Progress tracking
    progress_percentage: float


# Export for use
__all__ = ["TypedDictCliExecutionCoreSerialized"]
