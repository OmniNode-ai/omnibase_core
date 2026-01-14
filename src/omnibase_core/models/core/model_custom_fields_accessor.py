"""
Generic custom fields accessor with comprehensive field management.

Provides generic type support and comprehensive field operations for managing
typed custom fields with automatic initialization and type safety.
"""

from __future__ import annotations

import copy

from pydantic import ConfigDict, Field, model_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.types.type_constraints import PrimitiveValueType

from .model_field_accessor import ModelFieldAccessor

# Type alias for schema values that can be stored in custom fields
# Simplified to PrimitiveValueType for ONEX compliance (removing List[Any] primitive soup)
SchemaValueType = PrimitiveValueType | None


class ModelCustomFieldsAccessor[T](ModelFieldAccessor):
    """Generic custom fields accessor with comprehensive field management.

    List Homogeneity Assumption:
        The `list_fields` storage uses `list[ModelSchemaValue]` type. Homogeneity
        of list elements is maintained through **method discipline**, not runtime
        validation enforcement. All list-modifying methods (set_field, merge_fields,
        validate_and_distribute_fields) ensure that lists are converted to
        ModelSchemaValue format. This assumption holds because:

        1. All list mutations go through class methods that enforce conversion
        2. Lists originate from serialization sources with uniform types
        3. First-element type checking is used as an optimization (if first element
           is ModelSchemaValue, all elements are assumed to be as well)

        Callers should not directly mutate `list_fields` contents without using
        the provided accessor methods.
    """

    # Typed field storage
    string_fields: dict[str, str] = Field(default_factory=dict)
    int_fields: dict[str, int] = Field(default_factory=dict)
    bool_fields: dict[str, bool] = Field(default_factory=dict)
    list_fields: dict[str, list[ModelSchemaValue]] = Field(default_factory=dict)
    float_fields: dict[str, float] = Field(default_factory=dict)
    # Custom fields storage - can be overridden by subclasses to have default=None
    custom_fields: dict[str, PrimitiveValueType] | None = None

    # Pydantic configuration to allow extra fields
    model_config = ConfigDict(
        extra="allow",  # Allow dynamic fields,
        use_enum_values=False,
        validate_assignment=False,  # Disable strict validation for dynamic fields,
    )

    @model_validator(mode="before")
    @classmethod
    def validate_and_distribute_fields(
        cls, values: dict[str, object] | object
    ) -> dict[str, object]:
        """Validate and distribute incoming fields to appropriate typed storages."""
        # Handle empty dict edge case - returns empty typed field storages
        if not isinstance(values, dict):
            return {}

        # Create empty typed field storages, but only if they don't exist
        # Convert existing list_fields to ModelSchemaValue if needed
        existing_list_fields = values.get("list_fields", {})
        converted_list_fields: dict[str, list[ModelSchemaValue]] = {}
        if isinstance(existing_list_fields, dict):
            for key, value_list in existing_list_fields.items():
                if isinstance(value_list, list):
                    # Empty lists are explicitly handled here - no conversion needed
                    if not value_list:
                        converted_list_fields[key] = []
                    # SAFETY: Homogeneous list assumption - if first element is
                    # ModelSchemaValue, all elements are assumed to be as well.
                    # This is maintained through method discipline (all list-modifying
                    # methods enforce homogeneity), not runtime validation enforcement.
                    # Lists come from single serialization source with uniform type.
                    elif isinstance(value_list[0], ModelSchemaValue):
                        converted_list_fields[key] = value_list
                    else:
                        converted_list_fields[key] = [
                            ModelSchemaValue.from_value(item) for item in value_list
                        ]
                else:
                    # Handle non-list values by wrapping in single-element list.
                    # Assumption: Non-list values in list_fields are converted to
                    # homogeneous single-element lists for consistency.
                    converted_list_fields[key] = [
                        ModelSchemaValue.from_value(value_list)
                    ]

        # Use properly typed local variables to avoid mypy indexed assignment errors
        # on result["field_name"][key] where result["field_name"] has type 'object'
        string_fields: dict[str, str] = {}
        int_fields: dict[str, int] = {}
        bool_fields: dict[str, bool] = {}
        float_fields: dict[str, float] = {}
        list_fields_typed: dict[str, list[ModelSchemaValue]] = converted_list_fields

        # Copy existing typed fields if provided
        existing_string = values.get("string_fields")
        if isinstance(existing_string, dict):
            for k, v in existing_string.items():
                if isinstance(v, str):
                    string_fields[k] = v

        existing_int = values.get("int_fields")
        if isinstance(existing_int, dict):
            for k, v in existing_int.items():
                if isinstance(v, int) and not isinstance(v, bool):
                    int_fields[k] = v

        existing_bool = values.get("bool_fields")
        if isinstance(existing_bool, dict):
            for k, v in existing_bool.items():
                if isinstance(v, bool):
                    bool_fields[k] = v

        existing_float = values.get("float_fields")
        if isinstance(existing_float, dict):
            for k, v in existing_float.items():
                if isinstance(v, float):
                    float_fields[k] = v

        # Build result dict with proper types
        result: dict[str, object] = {
            "string_fields": string_fields,
            "int_fields": int_fields,
            "bool_fields": bool_fields,
            "list_fields": list_fields_typed,
            "float_fields": float_fields,
        }

        # Don't automatically create custom_fields - let it be None if not defined
        if "custom_fields" in values:
            result["custom_fields"] = values["custom_fields"]

        # Set of known field storage keys to skip during distribution
        field_storage_keys = {
            "string_fields",
            "int_fields",
            "bool_fields",
            "list_fields",
            "float_fields",
            "custom_fields",
        }

        # Distribute values to appropriate typed storages
        for key, value in values.items():
            # Skip if this is a typed field storage key
            if key in field_storage_keys:
                continue

            # Distribute based on value type
            # NOTE: Check bool before int since bool is a subclass of int in Python
            if isinstance(value, bool):
                bool_fields[key] = value
            elif isinstance(value, str):
                string_fields[key] = value
            elif isinstance(value, int):
                int_fields[key] = value
            elif isinstance(value, list):
                # Convert list to list[ModelSchemaValue] for type safety
                # SAFETY: Homogeneous list assumption - if first element is
                # ModelSchemaValue, all elements are assumed to be as well.
                # Maintained through method discipline, not validation enforcement.
                if value and isinstance(value[0], ModelSchemaValue):
                    list_fields_typed[key] = value
                else:
                    list_fields_typed[key] = [
                        ModelSchemaValue.from_value(item) for item in value
                    ]
            elif isinstance(value, float):
                float_fields[key] = value
            elif isinstance(value, dict):
                # Convert dict to string representation
                string_fields[key] = str(value)
            else:
                # Store as string fallback
                string_fields[key] = str(value)

        return result

    def set_field(
        self,
        path: str,
        value: PrimitiveValueType | ModelSchemaValue | None,
    ) -> bool:
        """Set a field value with automatic type detection and storage.

        Args:
            path: The field path. Dot notation (e.g., "nested.path") delegates
                to parent class. Simple keys store directly in typed storages.
            value: The value to set. Type determines storage location:
                - bool -> bool_fields
                - str -> string_fields
                - int -> int_fields
                - float -> float_fields
                - list -> list_fields (converted to ModelSchemaValue)
                - None -> stored as empty string in string_fields
                - ModelSchemaValue -> converted to string representation

        Returns:
            True if the field was set successfully, False if an exception occurred.

        Note:
            This method catches all exceptions and returns False on failure
            rather than propagating errors.
        """
        try:
            # Handle nested field paths
            if "." in path:
                # Convert value to parent-compatible type if needed
                if value is None:
                    # Convert None to ModelSchemaValue for parent class compatibility
                    parent_value: PrimitiveValueType | ModelSchemaValue = (
                        ModelSchemaValue.from_value(value)
                    )
                elif isinstance(value, ModelSchemaValue):
                    parent_value = value
                else:
                    # For PrimitiveValueType (str, int, float, bool) - pass through directly
                    parent_value = value
                return super().set_field(path, parent_value)
            # Handle simple field names (no dots)
            # Store in appropriate typed field based on value type
            # Use runtime type checking to avoid MyPy type narrowing issues
            if value is None:
                # Handle None by storing as empty string
                self.string_fields[path] = ""
            elif isinstance(value, ModelSchemaValue):
                # Convert ModelSchemaValue to string representation
                self.string_fields[path] = str(value.to_value())
            # Runtime type checking for primitive values using isinstance
            # for proper mypy type narrowing.
            # NOTE: Check bool before int since bool is a subclass of int in Python
            # (isinstance(True, int) returns True, so bool must be checked first)
            elif isinstance(value, bool):
                self.bool_fields[path] = value
            elif isinstance(value, str):
                self.string_fields[path] = value
            elif isinstance(value, int):
                self.int_fields[path] = value
            elif isinstance(value, float):
                self.float_fields[path] = value
            elif isinstance(value, list):
                # Require ModelSchemaValue lists - convert if needed
                # SAFETY: Homogeneous list assumption - if first element is
                # ModelSchemaValue, all elements are assumed to be as well.
                # Maintained through method discipline, not validation enforcement.
                if value and isinstance(value[0], ModelSchemaValue):
                    self.list_fields[path] = value
                else:
                    # Convert raw list to ModelSchemaValue list
                    self.list_fields[path] = [
                        ModelSchemaValue.from_value(item) for item in value
                    ]
            else:
                # Fallback to string storage for any other type
                self.string_fields[path] = str(value)

            return True
        except Exception:  # fallback-ok: set_field method signature returns bool for success/failure rather than raising
            return False

    def get_field(  # type: ignore[override]
        self, path: str, default: object = None
    ) -> object:
        """Get a field value from the appropriate typed storage.

        Note: Intentional override of parent's ModelResult return type.
        This class provides a simpler API for direct key-value access:

        - Simple paths (no dots): Returns raw values directly (str, int, bool, etc.)
        - Nested paths (with dots): Delegates to parent, returns ModelResult

        Examples:
            >>> fields.get_field("name")  # Returns "value" directly
            >>> fields.get_field("nested.path")  # Returns ModelResult

        For guaranteed type safety, use the typed accessors instead:
        get_string(), get_int(), get_bool(), get_float(), get_list()

        Args:
            path: The field path to look up. Simple keys or dot-notation paths.
            default: Value to return if field not found.

        Returns:
            The field value (raw type for simple paths, ModelResult for nested).
        """
        try:
            # Handle nested field paths - return ModelResult for dot notation support
            if "." in path:
                result = super().get_field(
                    path,
                    (
                        ModelSchemaValue.from_value(default)
                        if default is not None
                        else None
                    ),
                )
                return result  # Return ModelResult for nested paths

            # For simple field names, return raw values from typed storages
            # Check each typed field storage
            if path in self.string_fields:
                return self.string_fields[path]
            if path in self.int_fields:
                return self.int_fields[path]
            if path in self.bool_fields:
                return self.bool_fields[path]
            if path in self.list_fields:
                # Return ModelSchemaValue list directly
                return self.list_fields[path]
            if path in self.float_fields:
                return self.float_fields[path]
            if (
                hasattr(self, "custom_fields")
                and getattr(self, "custom_fields", None) is not None
                and path in getattr(self, "custom_fields", {})
            ):
                custom_fields = getattr(self, "custom_fields", {})
                return custom_fields[path]
            return default
        except Exception:  # fallback-ok: get_field returns default value on error for graceful field access
            return default

    def get_string(self, key: str, default: str = "") -> str:
        """Get a string field value.

        Args:
            key: The field name to look up.
            default: Value to return if field not found. Defaults to "".

        Returns:
            The string value if found, or converted to string from other types,
            or the default value.
        """
        if key in self.string_fields:
            return self.string_fields[key]
        # Try to convert from other types
        value = self.get_field(key)
        if value is not None and not isinstance(value, str):
            return str(value) if value != default else default
        return value if isinstance(value, str) else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer field value.

        Args:
            key: The field name to look up.
            default: Value to return if field not found or not an int. Defaults to 0.

        Returns:
            The integer value if found and is an int, otherwise the default value.
        """
        if key in self.int_fields:
            return self.int_fields[key]
        # Try to convert from other types
        value = self.get_field(key)
        if value is not None and isinstance(value, int):
            return int(value)  # Explicit cast for type safety
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean field value.

        Args:
            key: The field name to look up.
            default: Value to return if field not found or not a bool. Defaults to False.

        Returns:
            The boolean value if found and is a bool, otherwise the default value.
        """
        if key in self.bool_fields:
            return self.bool_fields[key]
        # Try to convert from other types
        value = self.get_field(key)
        if value is not None and isinstance(value, bool):
            return bool(value)  # Explicit cast for type safety
        return default

    def get_list(
        self, key: str, default: list[ModelSchemaValue] | None = None
    ) -> list[ModelSchemaValue]:
        """Get a list field value.

        Args:
            key: The field name to look up.
            default: Value to return if field not found. Defaults to None (returns []).

        Returns:
            list[ModelSchemaValue] for type safety. If the field contains a raw list,
            it is converted to ModelSchemaValue list.

        Note:
            Breaking API change in v0.4.0: Previously returned list[Any].
            Now returns list[ModelSchemaValue] for ONEX type safety compliance.
            To get raw values, use: [item.to_value() for item in accessor.get_list(key)]
        """
        if default is None:
            default = []
        if key in self.list_fields:
            return self.list_fields[key]
        # Try to get from other types and convert
        value = self.get_field(key)
        if value is not None and isinstance(value, list):
            # Convert raw list to ModelSchemaValue list
            return [ModelSchemaValue.from_value(item) for item in value]
        return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float field value.

        Args:
            key: The field name to look up.
            default: Value to return if field not found or not a float. Defaults to 0.0.

        Returns:
            The float value if found and is a float, otherwise the default value.
        """
        if key in self.float_fields:
            return self.float_fields[key]
        # Try to convert from other types
        value = self.get_field(key)
        if value is not None and isinstance(value, float):
            return float(value)  # Explicit cast for type safety
        return default

    def has_field(self, path: str) -> bool:
        """Check if a field exists in any typed storage.

        Args:
            path: The field path to check. Dot notation (e.g., "nested.path")
                delegates to parent class. Special case: "custom_fields" returns
                True only if custom_fields is not None and has at least one entry.

        Returns:
            True if the field exists in any storage, False otherwise.
        """
        if "." in path:
            return super().has_field(path)

        # Special case for custom_fields - return False if None, True if has any fields
        if path == "custom_fields":
            custom_fields = getattr(self, "custom_fields", None)
            return (
                hasattr(self, "custom_fields")
                and custom_fields is not None
                and len(custom_fields) > 0
            )

        return (
            path in self.string_fields
            or path in self.int_fields
            or path in self.bool_fields
            or path in self.list_fields
            or path in self.float_fields
            or (
                hasattr(self, "custom_fields")
                and getattr(self, "custom_fields", None) is not None
                and path in getattr(self, "custom_fields", {})
            )
        )

    def remove_field(self, path: str) -> bool:
        """Remove a field from the appropriate typed storage.

        Args:
            path: The field path to remove. Dot notation (e.g., "nested.path")
                delegates to parent class. Simple keys are removed from all
                typed storages where they exist.

        Returns:
            True if the field was found and removed from at least one storage,
            False if the field was not found or an exception occurred.

        Note:
            This method catches all exceptions and returns False on failure
            rather than propagating errors.
        """
        try:
            if "." in path:
                return super().remove_field(path)

            removed = False
            if path in self.string_fields:
                del self.string_fields[path]
                removed = True
            if path in self.int_fields:
                del self.int_fields[path]
                removed = True
            if path in self.bool_fields:
                del self.bool_fields[path]
                removed = True
            if path in self.list_fields:
                del self.list_fields[path]
                removed = True
            if path in self.float_fields:
                del self.float_fields[path]
                removed = True
            if (
                hasattr(self, "custom_fields")
                and getattr(self, "custom_fields", None) is not None
                and path in getattr(self, "custom_fields", {})
            ):
                custom_fields = getattr(self, "custom_fields", {})
                del custom_fields[path]
                removed = True
            return removed
        except Exception:  # fallback-ok: remove_field method signature returns bool for success/failure rather than raising
            return False

    def get_field_count(self) -> int:
        """Get the total number of fields across all typed storages."""
        custom_count = 0
        if hasattr(self, "custom_fields") and self.custom_fields is not None:
            custom_count = len(self.custom_fields)

        return (
            len(self.string_fields)
            + len(self.int_fields)
            + len(self.bool_fields)
            + len(self.list_fields)
            + len(self.float_fields)
            + custom_count
        )

    def get_all_field_names(self) -> list[str]:
        """Get all field names across all typed storages."""
        all_names: set[str] = set()
        all_names.update(self.string_fields.keys())
        all_names.update(self.int_fields.keys())
        all_names.update(self.bool_fields.keys())
        all_names.update(self.list_fields.keys())
        all_names.update(self.float_fields.keys())
        if (
            hasattr(self, "custom_fields")
            and getattr(self, "custom_fields", None) is not None
        ):
            custom_fields = getattr(self, "custom_fields", {})
            all_names.update(custom_fields.keys())
        return list(all_names)

    def clear_all_fields(self) -> None:
        """Clear all fields from all typed storages."""
        self.string_fields.clear()
        self.int_fields.clear()
        self.bool_fields.clear()
        self.list_fields.clear()
        self.float_fields.clear()
        if (
            hasattr(self, "custom_fields")
            and getattr(self, "custom_fields", None) is not None
        ):
            custom_fields = getattr(self, "custom_fields", {})
            custom_fields.clear()

    def get_field_type(self, key: str) -> str:
        """Get the type of a field.

        Args:
            key: The field name to look up.

        Returns:
            A string indicating the field's storage type: "string", "int", "bool",
            "list[Any]", "float", "custom", or "unknown" if not found.
        """
        if key in self.string_fields:
            return "string"
        if key in self.int_fields:
            return "int"
        if key in self.bool_fields:
            return "bool"
        if key in self.list_fields:
            return "list[Any]"
        if key in self.float_fields:
            return "float"
        if hasattr(self, "custom_fields") and key in getattr(
            self,
            "custom_fields",
            {},
        ):
            return "custom"
        return "unknown"

    def validate_field_value(self, key: str, value: SchemaValueType) -> bool:
        """Validate if a value is compatible with a field's existing type.

        Args:
            key: The field name to check.
            value: The value to validate for type compatibility.

        Returns:
            True if the value is compatible with the field's existing type,
            or if the field doesn't exist (new fields are always valid),
            or if value is None. False if the types are incompatible.
        """
        if not self.has_field(key):
            return True  # New fields are always valid

        if value is None:
            return True  # None is always acceptable

        field_type = self.get_field_type(key)

        # Use runtime type checking to avoid MyPy type narrowing issues
        value_type = type(value)

        if field_type == "string":
            return value_type is str
        if field_type == "int":
            return value_type is int
        if field_type == "bool":
            return value_type is bool
        if field_type == "float":
            return value_type is float
        if field_type == "list":
            return isinstance(value, list)
        if field_type == "custom":
            return True  # Custom fields accept any type
        return False

    def get_fields_by_type(self, field_type: str) -> dict[str, object]:
        """Get all fields of a specific type.

        Args:
            field_type: The type to filter by. One of: "string", "int", "bool",
                "list", "float", "custom".

        Returns:
            A dictionary of field names to values for the specified type.
            Returns empty dict for unknown field types.
        """
        if field_type == "string":
            return dict(self.string_fields)
        if field_type == "int":
            return dict(self.int_fields)
        if field_type == "bool":
            return dict(self.bool_fields)
        if field_type == "list":
            # Return ModelSchemaValue lists directly
            return dict(self.list_fields)
        if field_type == "float":
            return dict(self.float_fields)
        if field_type == "custom":
            custom_fields = getattr(self, "custom_fields", {})
            return dict(custom_fields) if custom_fields else {}
        return {}

    def copy_fields(self) -> ModelCustomFieldsAccessor[T]:
        """Create a deep copy of this field accessor."""
        new_instance = self.__class__()
        new_instance.string_fields = copy.deepcopy(self.string_fields)
        new_instance.int_fields = copy.deepcopy(self.int_fields)
        new_instance.bool_fields = copy.deepcopy(self.bool_fields)
        # Deep copy list_fields using copy.deepcopy for consistency with other field types
        new_instance.list_fields = copy.deepcopy(self.list_fields)
        new_instance.float_fields = copy.deepcopy(self.float_fields)

        # Only copy custom_fields if it exists
        if (
            hasattr(self, "custom_fields")
            and getattr(self, "custom_fields", None) is not None
        ):
            custom_fields = getattr(self, "custom_fields", {})
            new_instance.custom_fields = copy.deepcopy(custom_fields)

        return new_instance

    def merge_fields(self, other: ModelCustomFieldsAccessor[T]) -> None:
        """Merge fields from another accessor into this one."""
        self.string_fields.update(other.string_fields)
        self.int_fields.update(other.int_fields)
        self.bool_fields.update(other.bool_fields)
        # Merge list_fields (ModelSchemaValue lists) - create new instances
        for key, value in other.list_fields.items():
            self.list_fields[key] = [
                ModelSchemaValue.from_value(item.to_value()) for item in value
            ]
        self.float_fields.update(other.float_fields)

        # Only merge custom_fields if both objects have them
        self_custom_fields = getattr(self, "custom_fields", None)
        other_custom_fields = getattr(other, "custom_fields", None)

        if (
            hasattr(self, "custom_fields")
            and self_custom_fields is not None
            and hasattr(other, "custom_fields")
            and other_custom_fields is not None
        ):
            self_custom_fields.update(other_custom_fields)
        elif hasattr(other, "custom_fields") and other_custom_fields is not None:
            # Initialize our custom_fields if other has them but we don't
            self.custom_fields = copy.deepcopy(other_custom_fields)

    def model_dump(
        self,
        *,
        exclude_none: bool = False,
        **kwargs: object,
    ) -> dict[str, object]:
        """Override model_dump to include all field data.

        Note: This override intentionally changes base class semantics.
        Uses custom field iteration instead of Pydantic serialization.
        Only `exclude_none` is used; other kwargs are accepted for API
        compatibility but ignored (by_alias, mode, include, exclude, etc.).
        """
        # kwargs intentionally unused - accepted for base class API compatibility
        _ = kwargs

        data: dict[str, object] = {}

        # Add all fields to the output
        for key in self.get_all_field_names():
            value = self.get_field(key)
            if not exclude_none or value is not None:
                data[key] = value

        return data

    # Custom field convenience methods
    def get_custom_field(
        self,
        key: str,
        default: SchemaValueType = None,
    ) -> SchemaValueType:
        """Get a custom field value as raw value. Returns raw value or default."""
        if (
            hasattr(self, "custom_fields")
            and self.custom_fields is not None
            and key in self.custom_fields
        ):
            return self.custom_fields[key]
        return default

    def get_custom_field_value(
        self,
        key: str,
        default: SchemaValueType = None,
    ) -> SchemaValueType:
        """Get custom field value as raw value. Returns raw value or default."""
        return self.get_custom_field(key, default)

    def set_custom_field(
        self,
        key: str,
        value: PrimitiveValueType | ModelSchemaValue | None,
    ) -> bool:
        """Set a custom field value.

        Args:
            key: The field name to set.
            value: The value to store. Accepts PrimitiveValueType, ModelSchemaValue,
                or None. ModelSchemaValue is converted to its raw value.

        Returns:
            True if the field was set successfully, False if an exception occurred.

        Note:
            This method catches all exceptions and returns False on failure
            rather than propagating errors.
        """
        try:
            # Initialize custom_fields if it's None with explicit type annotation
            # Note: custom_fields is a defined model field, so hasattr check is redundant
            if self.custom_fields is None:
                # Explicitly type the dictionary to avoid MyPy inference issues
                self.custom_fields: dict[str, PrimitiveValueType] = {}

            # Store raw values directly in custom_fields
            raw_value: PrimitiveValueType
            if isinstance(value, ModelSchemaValue):
                to_val = value.to_value()
                # Ensure to_val is compatible with PrimitiveValueType
                if not isinstance(to_val, (str, int, float, bool, list, type(None))):
                    raw_value = str(to_val)  # Convert unsupported types to string
                else:
                    raw_value = to_val
            else:
                raw_value = value

            # Store in custom_fields - raw_value is already validated as PrimitiveValueType
            # compatible (str, int, float, bool, list, or None)
            self.custom_fields[key] = raw_value
            return True
        except Exception:  # fallback-ok: set_custom_field method signature returns bool for success/failure rather than raising
            return False

    def has_custom_field(self, key: str) -> bool:
        """Check if a custom field exists."""
        return (
            hasattr(self, "custom_fields")
            and self.custom_fields is not None
            and key in self.custom_fields
        )

    def remove_custom_field(self, key: str) -> bool:
        """Remove a custom field.

        Args:
            key: The field name to remove.

        Returns:
            True if the field existed and was removed, False if the field
            was not found or an exception occurred.

        Note:
            This method catches all exceptions and returns False on failure
            rather than propagating errors.
        """
        try:
            if (
                hasattr(self, "custom_fields")
                and self.custom_fields is not None
                and key in self.custom_fields
            ):
                del self.custom_fields[key]
                return True
            return False
        except Exception:  # fallback-ok: remove_custom_field method signature returns bool for success/failure rather than raising
            return False

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: protocol method must return bool, not raise
            return False

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol).

        Note:
            This method uses the overridden model_dump() which performs custom
            field iteration. Standard Pydantic serialization options like
            by_alias, mode, include, exclude are not applicable here since
            this class uses its own field storage mechanism.
        """
        return self.model_dump(exclude_none=False)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
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
__all__ = ["ModelCustomFieldsAccessor"]
