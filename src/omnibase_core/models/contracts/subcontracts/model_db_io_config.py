"""
Database IO Configuration Model.

Database IO configuration for SQL operations with parameterized queries.
Provides SQL query templating with positional parameters ($1, $2, ...),
connection management, and operation-specific settings.

Security:
    Raw queries are validated to prevent SQL injection via ${input.*} patterns.
    Use parameterized queries ($1, $2, ...) for user input instead.

Thread Safety:
    This model is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access.

See Also:
    - :class:`ModelEffectSubcontract`: Parent contract using this IO config
    - :mod:`omnibase_core.models.contracts.subcontracts.model_effect_resolved_context`:
        Resolved context models after template substitution
    - :class:`NodeEffect`: The primary node using these configurations
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
    - examples/contracts/effect/: Example YAML contracts
"""

import re
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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

__all__ = ["ModelDbIOConfig"]


class ModelDbIOConfig(BaseModel):
    """
    Database IO configuration for SQL operations.

    Provides SQL query templating with positional parameters ($1, $2, ...),
    connection management, and operation-specific settings.

    Security:
        Raw queries are validated to prevent SQL injection via ${input.*} patterns.
        Use parameterized queries ($1, $2, ...) for user input instead.

    Attributes:
        handler_type: Discriminator field identifying this as a DB handler.
        operation: Database operation type (select, insert, update, delete, upsert, raw).
        connection_name: Named connection reference from connection pool.
        query_template: SQL query with $1, $2, ... positional parameters.
        query_params: Parameter values/templates for positional placeholders.
        timeout_ms: Query timeout in milliseconds (1s - 10min).
        fetch_size: Fetch size for cursor-based retrieval.
        read_only: Whether to execute in read-only transaction mode.

    Example:
        >>> config = ModelDbIOConfig(
        ...     operation="select",
        ...     connection_name="primary_db",
        ...     query_template="SELECT * FROM users WHERE id = $1 AND status = $2",
        ...     query_params=["${input.user_id}", "${input.status}"],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Pre-compiled regex patterns for better performance in validators
    _INPUT_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\$\{input\.[^}]+\}")
    _PLACEHOLDER_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\$(\d+)")

    handler_type: Literal[EnumEffectHandlerType.DB] = Field(
        default=EnumEffectHandlerType.DB,
        description="Discriminator field for DB handler",
    )

    operation: Literal["select", "insert", "update", "delete", "upsert", "raw"] = Field(
        ...,
        description="Database operation type",
    )

    connection_name: str = Field(
        ...,
        description="Named connection reference from connection pool",
        min_length=1,
    )

    query_template: str = Field(
        ...,
        description="SQL query with $1, $2, ... positional parameters",
        min_length=1,
    )

    query_params: list[str] = Field(
        default_factory=list,
        description="Parameter values/templates for positional placeholders",
    )

    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Query timeout in milliseconds (1s - 10min)",
    )

    fetch_size: int | None = Field(
        default=None,
        ge=1,
        le=100000,
        description="Fetch size for cursor-based retrieval",
    )

    read_only: bool = Field(
        default=False,
        description="Whether to execute in read-only transaction mode",
    )

    @field_validator("operation", mode="before")
    @classmethod
    def normalize_operation(cls, value: object) -> object:
        """
        Normalize operation to lowercase.

        Ensures consistent operation type comparison by converting string
        values to lowercase and stripping whitespace.

        Args:
            value: The operation field value to normalize.

        Returns:
            Normalized lowercase string if input is string, otherwise unchanged.
        """
        if isinstance(value, str):
            return value.lower().strip()
        # Return non-string values as-is; Pydantic will validate them
        return value

    @model_validator(mode="after")
    def validate_sql_injection_prevention(self) -> "ModelDbIOConfig":
        """
        Prevent SQL injection via ${input.*} patterns in raw queries.

        Raw queries must use parameterized placeholders ($1, $2, ...) instead
        of direct template substitution to prevent SQL injection attacks.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If raw query contains ${input.*} patterns.
        """
        if self.operation == "raw":
            # Check for potentially dangerous ${input.*} patterns in query_template
            if self._INPUT_PATTERN.search(self.query_template):
                raise ModelOnexError(
                    message="Raw queries must not contain ${input.*} patterns. "
                    "Use parameterized queries ($1, $2, ...) with query_params instead.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("securityerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "sql_injection_prevention"
                            ),
                        }
                    ),
                )
        return self

    @model_validator(mode="after")
    def validate_param_count_and_sequence(self) -> "ModelDbIOConfig":
        """
        Validate query_params count and placeholder sequence.

        Ensures:
            1. query_params count matches the highest $N placeholder
            2. Placeholders are sequential starting from $1 (no gaps like $1, $3 missing $2)

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If param count mismatches or placeholders have gaps.
        """
        # Find all $N placeholders (where N is a number)
        matches = self._PLACEHOLDER_PATTERN.findall(self.query_template)

        if not matches:
            # No placeholders, params should be empty
            if self.query_params:
                raise ModelOnexError(
                    message=f"query_params has {len(self.query_params)} items "
                    "but query_template has no $N placeholders",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "param_count_validation"
                            ),
                        }
                    ),
                )
            return self

        # Get unique placeholder numbers as integers, sorted
        placeholder_nums = sorted({int(n) for n in matches})
        max_placeholder = placeholder_nums[-1]

        # Check params count matches highest placeholder
        if len(self.query_params) != max_placeholder:
            raise ModelOnexError(
                message=f"query_params has {len(self.query_params)} items "
                f"but query_template requires {max_placeholder} (highest placeholder: ${max_placeholder})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "param_count_validation"
                        ),
                        "expected_params": ModelSchemaValue.from_value(max_placeholder),
                        "actual_params": ModelSchemaValue.from_value(
                            len(self.query_params)
                        ),
                    }
                ),
            )

        # Check placeholders are sequential starting from $1 (no gaps)
        expected_sequence = list(range(1, max_placeholder + 1))
        if placeholder_nums != expected_sequence:
            missing = sorted(set(expected_sequence) - set(placeholder_nums))
            raise ModelOnexError(
                message=f"Placeholders must be sequential starting from $1. "
                f"Missing placeholders: ${', $'.join(str(n) for n in missing)}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "placeholder_sequence_validation"
                        ),
                        "found_placeholders": ModelSchemaValue.from_value(
                            placeholder_nums
                        ),
                        "missing_placeholders": ModelSchemaValue.from_value(missing),
                    }
                ),
            )

        return self

    @model_validator(mode="after")
    def validate_read_only_semantics(self) -> "ModelDbIOConfig":
        """
        Enforce read_only semantics: only select operations allowed when read_only=True.

        Read-only mode enables database optimizations but restricts operations
        to SELECT queries only.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If read_only=True with non-select operation.
        """
        if self.read_only and self.operation != "select":
            raise ModelOnexError(
                message=f"read_only=True only allows 'select' operation, "
                f"but got '{self.operation}'",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "read_only_semantics"
                        ),
                        "operation": ModelSchemaValue.from_value(self.operation),
                        "read_only": ModelSchemaValue.from_value(self.read_only),
                    }
                ),
            )
        return self
