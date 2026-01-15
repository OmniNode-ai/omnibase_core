"""
Base field accessor pattern for replacing dict[str, Any]-like interfaces.

Provides unified field access across CLI, Config, and Data domains with
dot notation support and type safety.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.errors.exception_groups import (
    ATTRIBUTE_ACCESS_ERRORS,
    PYDANTIC_MODEL_ERRORS,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_result import ModelResult
from omnibase_core.types.type_constraints import PrimitiveValueType


class ModelFieldAccessor(BaseModel):
    """Generic field accessor with dot notation support and type safety.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    def get_field(
        self,
        path: str,
        default: ModelSchemaValue | None = None,
    ) -> ModelResult[ModelSchemaValue, str]:
        """Get field using dot notation: 'metadata.custom_fields.key'"""
        try:
            obj: object = self
            for part in path.split("."):
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif (
                    hasattr(obj, "__getitem__")
                    and hasattr(obj, "__contains__")
                    and part in obj
                ):
                    obj = obj[part]
                else:
                    if default is not None:
                        return ModelResult.ok(default)
                    return ModelResult.err(
                        f"Field path '{path}' not found, stopped at part '{part}'",
                    )
            # Type checking for return value - convert to ModelSchemaValue
            if isinstance(obj, (str, int, float, bool, list)):
                return ModelResult.ok(ModelSchemaValue.from_value(obj))
            if default is not None:
                return ModelResult.ok(default)
            return ModelResult.err(
                f"Field at '{path}' has unsupported type: {type(obj)}",
            )
        except ATTRIBUTE_ACCESS_ERRORS as e:
            # fallback-ok: return default or error result when dot-notation path access fails
            if default is not None:
                return ModelResult.ok(default)
            return ModelResult.err(f"Error accessing field '{path}': {e!s}")

    def set_field(
        self,
        path: str,
        value: PrimitiveValueType | ModelSchemaValue,
    ) -> bool:
        """Set field using dot notation. Accepts raw values or ModelSchemaValue."""
        try:
            parts = path.split(".")
            obj: object = self

            # Navigate to parent object
            for part in parts[:-1]:
                if hasattr(obj, part):
                    next_obj = getattr(obj, part)
                    # If the attribute exists but is None, initialize it as a dict
                    if next_obj is None:
                        try:
                            setattr(obj, part, {})
                            next_obj = getattr(obj, part)
                        except (AttributeError, TypeError):
                            # fallback-ok: return False if initializing nested dict fails
                            return False
                    obj = next_obj
                elif hasattr(obj, "__getitem__") and hasattr(obj, "__setitem__"):
                    if hasattr(obj, "__contains__") and part not in obj:
                        obj[part] = {}
                    obj = obj[part]
                else:
                    return False

            # Set the final value - convert input to ModelSchemaValue first, then to raw value
            final_key = parts[-1]
            if isinstance(value, ModelSchemaValue):
                schema_value = value
                raw_value = schema_value.to_value()
            elif value is not None:
                schema_value = ModelSchemaValue.from_value(value)
                raw_value = schema_value.to_value()
            else:
                raw_value = None
            # First try setting as attribute if the object has the field (even if None)
            # This handles Pydantic model fields that are initially None
            if hasattr(obj, final_key) or hasattr(obj, "__dict__"):
                try:
                    setattr(obj, final_key, raw_value)
                    return True
                except (AttributeError, TypeError):
                    # fallback-ok: try dict-style access if attribute setting fails
                    pass
            # Fall back to dict[str, Any]-like access
            if hasattr(obj, "__setitem__"):
                obj[final_key] = raw_value
                return True

            return False
        except ATTRIBUTE_ACCESS_ERRORS:
            # fallback-ok: return False on any attribute access failure in set operation
            return False

    def has_field(self, path: str) -> bool:
        """Check if field exists using dot notation."""
        try:
            obj: object = self
            for part in path.split("."):
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif (
                    hasattr(obj, "__getitem__")
                    and hasattr(obj, "__contains__")
                    and part in obj
                ):
                    obj = obj[part]
                else:
                    return False
            return True
        except ATTRIBUTE_ACCESS_ERRORS:
            # fallback-ok: return False on any attribute access failure in existence check
            return False

    def remove_field(self, path: str) -> bool:
        """Remove field using dot notation."""
        try:
            parts = path.split(".")
            obj: object = self

            # Navigate to parent object
            for part in parts[:-1]:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif (
                    hasattr(obj, "__getitem__")
                    and hasattr(obj, "__contains__")
                    and part in obj
                ):
                    obj = obj[part]
                else:
                    return False

            # Remove the final field
            final_key = parts[-1]
            if hasattr(obj, final_key):
                delattr(obj, final_key)
            elif (
                hasattr(obj, "__delitem__")
                and hasattr(obj, "__contains__")
                and final_key in obj
            ):
                del obj[final_key]
            else:
                return False

            return True
        except ATTRIBUTE_ACCESS_ERRORS:
            # fallback-ok: return False on any attribute access failure in removal operation
            return False

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except PYDANTIC_MODEL_ERRORS:
            # fallback-ok: Configurable protocol requires boolean return for graceful config failure
            # setattr on Pydantic models can raise AttributeError, TypeError, ValidationError, ValueError
            return False

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        This base implementation always returns True. Subclasses should override
        this method to perform custom validation and catch specific exceptions
        (e.g., ValidationError, ValueError) when implementing validation logic.
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return


# Export for use
__all__ = ["ModelFieldAccessor"]
