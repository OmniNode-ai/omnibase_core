"""
Timeout Model.

Clean timeout wrapper that delegates to ModelTimeBased with proper ONEX patterns.
This provides a convenient timeout interface built on the unified time-based model.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import cached_property, lru_cache

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_runtime_category import EnumRuntimeCategory
from omnibase_core.enums.enum_time_unit import EnumTimeUnit
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_time_based import ModelTimeBased
from .model_timeout_data import ModelTimeoutData


class ModelTimeout(BaseModel):
    """
    Timeout wrapper for ModelTimeout.

    This model provides a timeout-specific interface
    that delegates all operations to the unified ModelTimeBased model.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    time_based: ModelTimeBased[int] = Field(
        default_factory=lambda: ModelTimeBased.timeout(
            value=30,
            unit=EnumTimeUnit.SECONDS,
            description="Default timeout",
        ),
        exclude=True,
        description="Internal time-based model",
    )

    # Direct storage for custom metadata using proper ONEX pattern
    custom_metadata: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Custom metadata using ModelSchemaValue",
    )

    def __init__(self, **data: object) -> None:
        """Initialize timeout model."""
        # Extract timeout-specific fields with proper type checking
        timeout_seconds_raw = data.pop("timeout_seconds", 30)
        warning_threshold_seconds_raw = data.pop("warning_threshold_seconds", None)
        is_strict_raw = data.pop("is_strict", True)
        allow_extension_raw = data.pop("allow_extension", False)
        extension_limit_seconds_raw = data.pop("extension_limit_seconds", None)
        runtime_category_raw = data.pop("runtime_category", None)
        description_raw = data.pop("description", None)
        custom_metadata_raw = data.pop("custom_metadata", {})

        # Type validation and conversion
        if not isinstance(timeout_seconds_raw, (int, float)):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="timeout_seconds must be a number",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("typeerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        timeout_seconds = int(timeout_seconds_raw)

        warning_threshold_seconds = None
        if warning_threshold_seconds_raw is not None:
            if not isinstance(warning_threshold_seconds_raw, (int, float)):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="warning_threshold_seconds must be a number",
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("typeerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
            warning_threshold_seconds = int(warning_threshold_seconds_raw)

        if not isinstance(is_strict_raw, bool):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="is_strict must be a boolean",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("typeerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        is_strict = is_strict_raw

        if not isinstance(allow_extension_raw, bool):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="allow_extension must be a boolean",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("typeerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )
        allow_extension = allow_extension_raw

        extension_limit_seconds = None
        if extension_limit_seconds_raw is not None:
            if not isinstance(extension_limit_seconds_raw, (int, float)):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="extension_limit_seconds must be a number",
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("typeerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
            extension_limit_seconds = int(extension_limit_seconds_raw)

        runtime_category = None
        if runtime_category_raw is not None:
            if not isinstance(runtime_category_raw, EnumRuntimeCategory):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="runtime_category must be an EnumRuntimeCategory",
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("typeerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
            runtime_category = runtime_category_raw

        description = None
        if description_raw is not None:
            if not isinstance(description_raw, str):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="description must be a string",
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("typeerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
            description = description_raw

        # Convert custom_metadata to ModelSchemaValue format if needed
        processed_metadata = {}
        if isinstance(custom_metadata_raw, dict):
            for key, value in custom_metadata_raw.items():
                if isinstance(value, ModelSchemaValue):
                    processed_metadata[key] = value
                else:
                    processed_metadata[key] = ModelSchemaValue.from_value(value)
        elif custom_metadata_raw != {}:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="custom_metadata must be a dictionary",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("typeerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        # Initialize parent with processed custom metadata
        super().__init__(custom_metadata=processed_metadata, **data)

        # Create the underlying time-based model
        metadata = {"type": "timeout"}
        if description:
            metadata["description"] = description

        self.time_based = ModelTimeBased.timeout(
            value=timeout_seconds,
            unit=EnumTimeUnit.SECONDS,
            description=description,
            is_strict=is_strict,
            warning_threshold_value=warning_threshold_seconds,
            allow_extension=allow_extension,
            extension_limit_value=extension_limit_seconds,
        )

        if runtime_category:
            self.time_based.runtime_category = runtime_category

    @property
    def timeout_seconds(self) -> int:
        """Get timeout value in seconds."""
        return int(self.time_based.to_seconds())

    @cached_property
    def warning_threshold_seconds(self) -> int | None:
        """Get warning threshold in seconds.

        Performance Optimization: Uses @cached_property to avoid creating
        ModelTimeBased objects on every access.
        """
        if self.time_based.warning_threshold_value is None:
            return None
        warning_time_based = ModelTimeBased(
            value=self.time_based.warning_threshold_value,
            unit=self.time_based.unit,
        )
        return int(warning_time_based.to_seconds())

    @property
    def is_strict(self) -> bool:
        """Whether timeout is strictly enforced."""
        return self.time_based.is_strict

    @property
    def allow_extension(self) -> bool:
        """Whether timeout can be extended during execution."""
        return self.time_based.allow_extension

    @cached_property
    def extension_limit_seconds(self) -> int | None:
        """Maximum extension time in seconds.

        Performance Optimization: Uses @cached_property to avoid creating
        ModelTimeBased objects on every access.
        """
        if self.time_based.extension_limit_value is None:
            return None
        extension_time_based = ModelTimeBased(
            value=self.time_based.extension_limit_value,
            unit=self.time_based.unit,
        )
        return int(extension_time_based.to_seconds())

    @property
    def runtime_category(self) -> EnumRuntimeCategory | None:
        """Runtime category for this timeout."""
        return self.time_based.runtime_category

    @property
    def description(self) -> str | None:
        """Human-readable timeout description."""
        return self.time_based.metadata.get("description")

    @cached_property
    def custom_properties(self) -> ModelCustomProperties:
        """Custom timeout properties using typed model.

        Performance Optimization: Uses @cached_property to avoid expensive conversion
        operations on every access. Cache is invalidated when the object is modified.
        """
        # Convert ModelSchemaValue metadata to basic types for
        # ModelCustomProperties
        metadata: dict[str, ModelSchemaValue] = {}
        for key, schema_value in self.custom_metadata.items():
            # Convert to Python value then back to ModelSchemaValue for type
            # consistency
            python_value = schema_value.to_value()
            metadata[key] = ModelSchemaValue.from_value(python_value)

        # Create ModelCustomProperties from the metadata values
        # Convert ModelSchemaValue objects to primitive types for from_metadata
        primitive_metadata: dict[str, object] = {}
        for key, val in metadata.items():
            # val is always ModelSchemaValue, extract primitive value for proper typing
            primitive_value = val.to_value()
            if isinstance(primitive_value, (str, int, float, bool)):
                primitive_metadata[key] = primitive_value
            else:
                # Keep as ModelSchemaValue if not a primitive type
                primitive_metadata[key] = val

        return ModelCustomProperties.from_metadata(primitive_metadata)

    @property
    def timeout_timedelta(self) -> timedelta:
        """Get timeout as timedelta object."""
        return self.time_based.to_timedelta()

    @property
    def timeout_minutes(self) -> float:
        """Get timeout in minutes."""
        return self.time_based.to_minutes()

    @property
    def timeout_hours(self) -> float:
        """Get timeout in hours."""
        return self.time_based.to_hours()

    @property
    def warning_threshold_timedelta(self) -> timedelta | None:
        """Get warning threshold as timedelta object."""
        if self.warning_threshold_seconds is None:
            return None
        return timedelta(seconds=self.warning_threshold_seconds)

    @property
    def extension_limit_timedelta(self) -> timedelta | None:
        """Get extension limit as timedelta object."""
        if self.extension_limit_seconds is None:
            return None
        return timedelta(seconds=self.extension_limit_seconds)

    @property
    def max_total_seconds(self) -> int:
        """Get maximum total seconds including extensions."""
        base = self.timeout_seconds
        if self.allow_extension and self.extension_limit_seconds is not None:
            return base + self.extension_limit_seconds
        return base

    def get_deadline(self, start_time: datetime | None = None) -> datetime:
        """Get deadline datetime for this timeout."""
        return self.time_based.get_deadline(start_time)

    def get_warning_time(self, start_time: datetime | None = None) -> datetime | None:
        """Get warning datetime for this timeout."""
        return self.time_based.get_warning_time(start_time)

    def is_expired(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> bool:
        """Check if timeout has expired."""
        return self.time_based.is_expired(start_time, current_time)

    def is_warning_triggered(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> bool:
        """Check if warning threshold has been reached."""
        return self.time_based.is_warning_triggered(start_time, current_time)

    def get_remaining_seconds(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> float:
        """Get remaining seconds until timeout."""
        return self.time_based.get_remaining_seconds(start_time, current_time)

    def get_elapsed_seconds(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> float:
        """Get elapsed seconds since start."""
        return self.time_based.get_elapsed_seconds(start_time, current_time)

    def get_progress_percentage(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> float:
        """Get timeout progress as percentage (0-100)."""
        return self.time_based.get_progress_percentage(start_time, current_time)

    def extend_timeout(self, additional_seconds: int) -> bool:
        """Extend timeout by additional seconds if allowed."""
        return self.time_based.extend_time(additional_seconds)

    def set_custom_metadata(self, key: str, value: object) -> None:
        """Set custom metadata value with bounded types.

        Performance Note: Invalidates custom_properties cache when metadata changes.
        """
        self.custom_metadata[key] = ModelSchemaValue.from_value(value)
        # Invalidate cached property when metadata changes
        if hasattr(self, "custom_properties"):
            delattr(self, "custom_properties")

    def get_custom_metadata(self, key: str) -> object:
        """Get custom metadata value with bounded return type."""
        schema_value = self.custom_metadata.get(key)
        if schema_value is None:
            return None
        value = schema_value.to_value()
        # Ensure bounded return type
        if isinstance(value, (str, int, float, bool)):
            return value
        return None

    @classmethod
    def from_seconds(
        cls,
        seconds: int,
        description: str | None = None,
        is_strict: bool = True,
    ) -> ModelTimeout:
        """Create timeout from seconds."""
        return cls(
            timeout_seconds=seconds,
            description=description,
            is_strict=is_strict,
        )

    @classmethod
    def from_minutes(
        cls,
        minutes: float,
        description: str | None = None,
        is_strict: bool = True,
    ) -> ModelTimeout:
        """Create timeout from minutes."""
        seconds = int(minutes * 60)
        return cls.from_seconds(seconds, description, is_strict)

    @classmethod
    def from_hours(
        cls,
        hours: float,
        description: str | None = None,
        is_strict: bool = True,
    ) -> ModelTimeout:
        """Create timeout from hours."""
        seconds = int(hours * 3600)
        return cls.from_seconds(seconds, description, is_strict)

    @classmethod
    @lru_cache(maxsize=32)
    def _calculate_timeout_from_category(
        cls,
        category: EnumRuntimeCategory,
        use_max_estimate: bool = True,
    ) -> int:
        """Calculate timeout seconds from runtime category with caching.

        Performance Optimization: Caches runtime category calculations since
        the same categories are often used repeatedly. Cache size of 32 covers
        all enum values with room for different configurations.
        """
        min_seconds, max_seconds = category.estimated_seconds
        if use_max_estimate and max_seconds is not None:
            return int(max_seconds)
        # Use minimum with some buffer
        return max(int(min_seconds * 2), 30)

    @classmethod
    def from_runtime_category(
        cls,
        category: EnumRuntimeCategory,
        description: str | None = None,
        use_max_estimate: bool = True,
    ) -> ModelTimeout:
        """Create timeout from runtime category."""
        timeout_seconds = cls._calculate_timeout_from_category(
            category,
            use_max_estimate,
        )

        return cls(
            timeout_seconds=timeout_seconds,
            runtime_category=category,
            description=description,
        )

    def get_time_based(self) -> ModelTimeBased[int]:
        """Get the underlying time-based model for migration purposes."""
        return self.time_based

    def to_typed_data(self) -> ModelTimeoutData:
        """Serialize model with proper strong typing."""
        return ModelTimeoutData(
            timeout_seconds=self.timeout_seconds,
            warning_threshold_seconds=self.warning_threshold_seconds or 0,
            is_strict=self.is_strict,
            allow_extension=self.allow_extension,
            extension_limit_seconds=self.extension_limit_seconds or 0,
            runtime_category=self.runtime_category or EnumRuntimeCategory.FAST,
            description=self.description or "",
            custom_properties=self.custom_properties,
        )

    @classmethod
    def model_validate_typed(cls, data: ModelTimeoutData) -> ModelTimeout:
        """Create ModelTimeout from typed data using Pydantic validation."""
        # Convert ModelTimeoutData to dict[str, Any]for initialization
        init_data = data.model_dump()

        # Convert custom_properties to custom_metadata format
        custom_props = init_data.pop("custom_properties", {})
        if custom_props:
            # Extract metadata from ModelCustomProperties
            metadata = {
                **custom_props.get("custom_strings", {}),
                **custom_props.get("custom_numbers", {}),
                **custom_props.get("custom_flags", {}),
            }
            init_data["custom_metadata"] = metadata

        # Handle optional fields that shouldn't be zero
        if init_data.get("warning_threshold_seconds") == 0:
            init_data["warning_threshold_seconds"] = None
        if init_data.get("extension_limit_seconds") == 0:
            init_data["extension_limit_seconds"] = None
        if init_data.get("description") == "":
            init_data["description"] = None

        return cls(**init_data)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            ModelOnexError: If execution fails with details about the failure
        """
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Execution failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            ModelOnexError: If configuration fails with details about the failure
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Configuration failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            ModelOnexError: If validation fails with details about the failure
        """
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Instance validation failed: {e}",
            ) from e


# Export for use
__all__ = ["ModelTimeout"]
