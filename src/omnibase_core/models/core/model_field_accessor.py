"""
Base field accessor pattern for replacing dict-like interfaces.

Provides unified field access across CLI, Config, and Data domains with
dot notation support and type safety.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_result import ModelResult
from omnibase_core.types import TypedDictFieldValue


class ModelFieldAccessor(BaseModel):
    """Generic field accessor with dot notation support and type safety."""

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
                        f"Field path '{path}' not found, stopped at part '{part}'"
                    )
            # Type checking for return value - convert to ModelSchemaValue
            if isinstance(obj, (str, int, float, bool, list)):
                return ModelResult.ok(ModelSchemaValue.from_value(obj))
            if default is not None:
                return ModelResult.ok(default)
            return ModelResult.err(
                f"Field at '{path}' has unsupported type: {type(obj)}"
            )
        except (AttributeError, KeyError, TypeError) as e:
            if default is not None:
                return ModelResult.ok(default)
            return ModelResult.err(f"Error accessing field '{path}': {str(e)}")

    def set_field(self, path: str, value: ModelSchemaValue) -> bool:
        """Set field using dot notation."""
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
                            return False
                    obj = next_obj
                elif hasattr(obj, "__getitem__") and hasattr(obj, "__setitem__"):
                    if hasattr(obj, "__contains__") and part not in obj:
                        obj[part] = {}
                    obj = obj[part]
                else:
                    return False

            # Set the final value - convert ModelSchemaValue to raw value
            final_key = parts[-1]
            raw_value = value.to_value() if value else None
            # First try setting as attribute if the object has the field (even if None)
            # This handles Pydantic model fields that are initially None
            if hasattr(obj, final_key) or hasattr(obj, "__dict__"):
                try:
                    setattr(obj, final_key, raw_value)
                    return True
                except (AttributeError, TypeError):
                    pass
            # Fall back to dict-like access
            if hasattr(obj, "__setitem__"):
                obj[final_key] = raw_value
                return True

            return False
        except (AttributeError, KeyError, TypeError):
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
        except (AttributeError, KeyError, TypeError):
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
        except (AttributeError, KeyError, TypeError):
            return False

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelFieldAccessor"]
