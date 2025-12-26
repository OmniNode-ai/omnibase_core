# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Action parameters model for typed action execution parameters.

This module provides ModelActionParameters, a typed model for action execution
parameters that replaces untyped dict[str, ModelSchemaValue] fields. It captures
common action execution configuration with explicit typed fields while allowing
domain-specific extensions through a typed extensions field.

Thread Safety:
    ModelActionParameters is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.context.model_session_context: Session context
    - omnibase_core.models.common.model_schema_value: Schema value type
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_decorators import allow_dict_str_any

__all__ = ["ModelActionParameters"]


@allow_dict_str_any(
    "Extensions field intentionally allows flexible dict for domain-specific "
    "parameters that cannot be pre-defined."
)
class ModelActionParameters(BaseModel):
    """Typed parameters for action execution.

    Provides explicit typed fields for common action execution parameters.
    All fields are optional as different actions may require different subsets
    of parameters. The extensions field allows domain-specific parameters
    while maintaining type safety.

    Attributes:
        action_name: Name of the action to execute. Used for action routing
            and logging.
        action_version: Semantic version of the action using ModelSemVer type.
            Enables version-specific behavior and compatibility checks.
        idempotency_key: Unique key for idempotent execution. When provided,
            duplicate executions with the same key will return cached results
            instead of re-executing.
        timeout_override_seconds: Override the default action timeout in seconds.
            Must be positive. Use for long-running actions that exceed defaults.
        input_path: Input file or resource path for file-based actions.
            Can be absolute or relative to the action's working directory.
        output_path: Output file or resource path for file-based actions.
            Can be absolute or relative to the action's working directory.
        format: Data format identifier (e.g., "json", "yaml", "xml", "csv").
            Used for serialization/deserialization of input and output data.
        validate_input: Whether to validate input before execution.
            Defaults to True for safety.
        validate_output: Whether to validate output after execution.
            Defaults to True for safety.
        extensions: Extension parameters for domain-specific needs.
            This is the ONLY dict field allowed - all common parameters
            must be explicit fields.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelActionParameters
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>>
        >>> params = ModelActionParameters(
        ...     action_name="transform_data",
        ...     action_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     idempotency_key="txn-12345",
        ...     format="json",
        ...     validate_input=True,
        ...     validate_output=True,
        ... )
        >>> params.action_name
        'transform_data'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    action_name: str | None = Field(
        default=None,
        description="Name of the action to execute",
    )
    action_version: ModelSemVer | None = Field(
        default=None,
        description="Semantic version of the action using ModelSemVer type.",
    )
    idempotency_key: str | None = Field(
        default=None,
        description=(
            "Unique key for idempotent execution. Duplicate executions with the "
            "same key return cached results instead of re-executing."
        ),
    )
    timeout_override_seconds: int | None = Field(
        default=None,
        description="Override default action timeout in seconds. Must be positive.",
        gt=0,
    )
    input_path: str | None = Field(
        default=None,
        description="Input file or resource path for file-based actions",
    )
    output_path: str | None = Field(
        default=None,
        description="Output file or resource path for file-based actions",
    )
    format: str | None = Field(
        default=None,
        description="Data format identifier (e.g., 'json', 'yaml', 'xml', 'csv')",
    )
    validate_input: bool = Field(
        default=True,
        description="Whether to validate input before execution",
    )
    validate_output: bool = Field(
        default=True,
        description="Whether to validate output after execution",
    )
    # Note: Using dict[str, Any] instead of dict[str, ModelSchemaValue] to avoid
    # circular import. The extensions field is intentionally flexible for
    # domain-specific needs. Common parameters should be explicit typed fields above.
    extensions: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Extension parameters for domain-specific needs. This is the ONLY "
            "dict field allowed - all common parameters must be explicit fields. "
            "Values should be JSON-serializable types."
        ),
    )
