"""
Serialization Subcontract Model.



Dedicated subcontract model for serialization functionality providing:
- Serialization format configuration (yaml, json, toml)
- Canonical serialization mode control
- Output formatting options (indentation, sorting)
- Value filtering (None, defaults exclusion)
- Compression and size limits
- Format validation and normalization

This model is composed into node contracts that require serialization functionality,
providing clean separation between node logic and serialization behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelSerializationSubcontract(BaseModel):
    """
    Serialization subcontract model for serialization functionality.

    Comprehensive serialization subcontract providing format configuration,
    canonical mode control, output formatting options, and size management.
    Designed for composition into node contracts requiring serialization
    functionality.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Subcontract version (auto-generated if not provided)",
    )

    # Serialization format configuration
    serialization_format: str = Field(
        default="yaml",
        description="Serialization format (yaml, json, toml)",
    )

    enable_canonical_mode: bool = Field(
        default=True,
        description="Use canonical serialization for deterministic output",
    )

    # Output value filtering
    exclude_none_values: bool = Field(
        default=True,
        description="Exclude None values from serialized output",
    )

    exclude_defaults: bool = Field(
        default=False,
        description="Exclude default values from serialized output",
    )

    # Output formatting
    indent_spaces: int = Field(
        default=2,
        description="Number of spaces for indentation in pretty formatting",
        ge=0,
        le=8,
    )

    sort_keys: bool = Field(
        default=True,
        description="Sort keys alphabetically in serialized output",
    )

    # Compression and size limits
    enable_compression: bool = Field(
        default=False,
        description="Enable output compression (gzip)",
    )

    max_serialized_size_bytes: int = Field(
        default=10485760,  # 10MB default
        description="Maximum serialized output size in bytes",
        ge=1024,  # 1KB minimum
        le=104857600,  # 100MB maximum
    )

    @model_validator(mode="after")
    def validate_format(self) -> "ModelSerializationSubcontract":
        """Validate and normalize serialization format."""
        allowed_formats = ["yaml", "json", "toml"]
        v = self.serialization_format
        normalized = v.lower().strip()

        if normalized not in allowed_formats:
            msg = f"serialization_format must be one of {allowed_formats}, got '{v}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("serialization_format"),
                        "value": ModelSchemaValue.from_value(v),
                        "allowed_formats": ModelSchemaValue.from_value(
                            ",".join(allowed_formats)
                        ),
                    },
                ),
            )

        # Use object.__setattr__ to bypass validation recursion
        object.__setattr__(self, "serialization_format", normalized)
        return self

    @model_validator(mode="after")
    def validate_indent(self) -> "ModelSerializationSubcontract":
        """Validate indent_spaces is non-negative and reasonable."""
        v = self.indent_spaces
        if v < 0:
            msg = "indent_spaces must be non-negative"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("indent_spaces"),
                        "value": ModelSchemaValue.from_value(str(v)),
                    },
                ),
            )

        if v > 16:
            msg = "indent_spaces should not exceed 16 for readability"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("indent_spaces"),
                        "value": ModelSchemaValue.from_value(str(v)),
                    },
                ),
            )

        return self

    @model_validator(mode="after")
    def validate_max_size(self) -> "ModelSerializationSubcontract":
        """Validate max_serialized_size_bytes is reasonable."""
        v = self.max_serialized_size_bytes
        if v < 1024:
            msg = "max_serialized_size_bytes must be at least 1KB (1024 bytes)"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value(
                            "max_serialized_size_bytes"
                        ),
                        "value": ModelSchemaValue.from_value(str(v)),
                    },
                ),
            )

        if v > 1073741824:  # 1GB
            msg = "max_serialized_size_bytes cannot exceed 1GB (1073741824 bytes)"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value(
                            "max_serialized_size_bytes"
                        ),
                        "value": ModelSchemaValue.from_value(str(v)),
                    },
                ),
            )

        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,  # Validate on assignment after creation
    )
