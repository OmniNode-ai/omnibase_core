"""
TypedDict for CLI node execution input serialization output.

Strongly-typed representation for ModelCliNodeExecutionInput.serialize() return value.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from omnibase_core.types.typed_dict_cli_advanced_params_serialized import (
        TypedDictCliAdvancedParamsSerialized,
    )


class TypedDictCliNodeExecutionInputSerialized(TypedDict):
    """
    Strongly-typed representation of ModelCliNodeExecutionInput.serialize() output.

    This replaces dict[str, Any] with proper type safety for serialization output.
    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # Core execution parameters - enum serialized as string
    action: str
    node_id: str | None  # UUID serialized as string
    node_display_name: str | None

    # Node-specific parameters
    target_node_id: str | None  # UUID serialized as string
    target_node_display_name: str | None

    # Input/output configuration
    include_metadata: bool
    include_health_info: bool

    # Filtering and selection - enum serialized as string
    health_filter: bool
    category_filter: str | None

    # Performance and timeouts
    timeout_seconds: float | None

    # Output formatting - enum serialized as string
    output_format: str
    verbose: bool

    # Advanced parameters (nested typed model)
    advanced_params: TypedDictCliAdvancedParamsSerialized

    # Execution context - UUID serialized as string
    execution_context: str | None
    request_id: str


# Export for use
__all__ = ["TypedDictCliNodeExecutionInputSerialized"]
