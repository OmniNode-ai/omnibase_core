"""
Action parameters model for typed action execution parameters.

This module provides ModelActionParameters, a typed model for action execution
parameters that replaces untyped dict[str, ModelSchemaValue] fields. It captures
common action execution configuration with explicit typed fields while allowing
domain-specific extensions through a typed extensions field.

Thread Safety:
    ModelActionParameters is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

    CAVEAT: The extensions dict field contents can still be mutated even on a
    frozen model (Pydantic's frozen only prevents field reassignment, not mutation
    of mutable container contents). Treat extensions as immutable by convention.

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
    "Extensions field intentionally allows flexible dict[str, Any] for domain-specific "
    "parameters that cannot be pre-defined. The extensions dict serves as an escape hatch "
    "for custom configuration that doesn't fit the typed fields above. All common parameters "
    "should use explicit typed fields; extensions is for truly dynamic needs."
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
        timeout_override_ms: Override the default action timeout in milliseconds.
            Must be positive. Use for long-running actions that exceed defaults.
            Uses milliseconds for consistency with ONEX timeout conventions.
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
            must be explicit fields. WARNING: While model is frozen, dict
            contents can still be mutated. Treat as immutable by convention.

    Thread Safety:
        This model is frozen (field reassignment prevented) and safe for
        concurrent read access across threads. CAVEAT: The extensions dict
        contents CAN be mutated even on a frozen model. For true thread safety,
        never modify extensions after model creation.

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
        description="Semantic version of the action using ModelSemVer type",
    )
    idempotency_key: str | None = Field(
        default=None,
        description=(
            "Unique key for idempotent execution. Duplicate executions with the "
            "same key return cached results instead of re-executing."
        ),
    )
    timeout_override_ms: int | None = Field(
        default=None,
        description=(
            "Override the default action timeout in milliseconds. "
            "Must be a positive integer when provided. Uses milliseconds for "
            "consistency with ONEX timeout conventions."
        ),
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
    # ARCHITECTURE DECISION: Using dict[str, Any] for extensions field.
    #
    # Rationale:
    # 1. Avoids circular import with dict[str, ModelSchemaValue]
    # 2. Provides escape hatch for truly dynamic domain-specific needs
    # 3. Common/recurring parameters should be promoted to explicit typed fields
    #
    # See also: @allow_dict_str_any decorator justification above.
    #
    # IMPORTANT - Mutable Dict Limitation:
    # While this model has frozen=True (Pydantic ConfigDict), the dict contents can
    # still be mutated after model creation. Pydantic's frozen setting only prevents
    # reassigning the field itself (e.g., `model.extensions = new_dict` raises an error),
    # but does NOT prevent mutating the dict contents (e.g., `model.extensions["key"] = value`
    # will succeed). For thread safety, treat this dict as immutable by convention:
    # - Never modify the dict contents after model creation
    # - Create a new model instance if you need different extension values
    # - In multi-threaded contexts, create separate model instances per thread
    extensions: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Extension parameters for domain-specific needs. This is the ONLY "
            "dict field allowed - all common parameters must be explicit fields. "
            "Values should be JSON-serializable types. "
            "WARNING: While model is frozen, dict contents can be mutated. "
            "Treat as immutable by convention for thread safety."
        ),
    )
