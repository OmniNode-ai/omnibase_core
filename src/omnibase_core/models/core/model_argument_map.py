"""
Argument Map Model

Type-safe container for parsed CLI arguments that provides both positional
and named argument access with type conversion capabilities.
"""

from typing import TypeVar, cast

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_argument_value import (
    ArgumentValueType,
    ModelArgumentValue,
)

T = TypeVar("T")


class ModelArgumentMap(BaseModel):
    """
    Type-safe argument container for parsed CLI arguments.

    This model provides structured access to both positional and named
    arguments with type-safe retrieval methods.
    """

    positional_args: list[ModelArgumentValue] = Field(
        default_factory=list,
        description="Positional arguments in order",
    )

    named_args: dict[str, ModelArgumentValue] = Field(
        default_factory=dict,
        description="Named arguments by name",
    )

    raw_args: list[str] = Field(
        default_factory=list,
        description="Original raw argument strings",
    )

    def get_typed(
        self,
        name: str,
        expected_type: type[T],
        default: T | None = None,
    ) -> T | None:
        """
        Type-safe argument retrieval with optional default.

        This method provides runtime type conversion for common types. When the
        stored value doesn't match expected_type, automatic conversion is attempted
        for str, int, float, and bool types.

        Type Conversion Behavior:
            - str: Any value converted via str()
            - int: Numeric strings/values converted via int()
            - float: Numeric strings/values converted via float()
            - bool: String values "true", "1", "yes", "on" (case-insensitive) → True;
                    other values converted via bool()

        Note:
            The type: ignore comments in this method are necessary because TypeVar T
            cannot be narrowed at runtime after the expected_type comparison. The
            conversions are type-safe by construction (e.g., str() always returns str).

        Args:
            name: Argument name to retrieve
            expected_type: Expected type for the argument value (supports str, int,
                float, bool with automatic conversion)
            default: Default value if argument not found or conversion fails

        Returns:
            The argument value cast to expected_type, or default if not found
            or conversion fails
        """
        if name in self.named_args:
            value = self.named_args[name].value
            if isinstance(value, expected_type):
                return value
            # Try to convert if possible
            # Note: type: ignore comments below are required because mypy cannot narrow
            # TypeVar T based on runtime expected_type comparison. Each conversion is
            # guarded by an if-check ensuring the return type matches T.
            try:
                if expected_type == str:
                    # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because str() always returns str.
                    return str(value)  # type: ignore[return-value]
                if expected_type == int:
                    # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because int() returns int; arg-type ignored for Any input.
                    return int(value)  # type: ignore[return-value,arg-type]
                if expected_type == float:
                    # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because float() returns float; arg-type ignored for Any input.
                    return float(value)  # type: ignore[return-value,arg-type]
                if expected_type == bool:
                    if isinstance(value, str):
                        # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because bool comparison returns bool.
                        return value.lower() in ("true", "1", "yes", "on")  # type: ignore[return-value]
                    # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because bool() always returns bool.
                    return bool(value)  # type: ignore[return-value]
            except (ValueError, TypeError):
                pass
        return default

    def get_string(self, name: str, default: str = "") -> str:
        """Get string argument value."""
        result = self.get_typed(name, str, default)
        return result if result is not None else default

    def get_int(self, name: str, default: int = 0) -> int:
        """Get integer argument value."""
        result = self.get_typed(name, int, default)
        return result if result is not None else default

    def get_float(self, name: str, default: float = 0.0) -> float:
        """Get float argument value."""
        result = self.get_typed(name, float, default)
        return result if result is not None else default

    def get_bool(self, name: str, default: bool = False) -> bool:
        """Get boolean argument value."""
        result = self.get_typed(name, bool, default)
        return result if result is not None else default

    def get_list(self, name: str, default: list[str] | None = None) -> list[str]:
        """Get list argument value."""
        if default is None:
            default = []
        # Use bare 'list' for isinstance check at runtime (generic list[str] not valid).
        result = self.get_typed(name, list, default)
        # Ensure we return list[str] by converting items
        if result is not None and isinstance(result, list):
            return [str(item) for item in result]
        return default

    def has_argument(self, name: str) -> bool:
        """Check if named argument exists."""
        return name in self.named_args

    def get_positional(
        self,
        index: int,
        expected_type: type[T],
        default: T | None = None,
    ) -> T | None:
        """
        Get positional argument by index with type conversion.

        This method provides runtime type conversion for common types, identical
        to get_typed(). When the stored value doesn't match expected_type,
        automatic conversion is attempted for str, int, float, and bool types.

        Type Conversion Behavior:
            - str: Any value converted via str()
            - int: Numeric strings/values converted via int()
            - float: Numeric strings/values converted via float()
            - bool: String values "true", "1", "yes", "on" (case-insensitive) -> True;
                    other values converted via bool()

        Note:
            The type: ignore comments in this method are necessary because TypeVar T
            cannot be narrowed at runtime after the expected_type comparison. The
            conversions are type-safe by construction (e.g., str() always returns str).

        Args:
            index: Position index (0-based)
            expected_type: Expected type for the argument value (supports str, int,
                float, bool with automatic conversion)
            default: Default value if argument not found or conversion fails

        Returns:
            The argument value cast to expected_type, or default if not found,
            index out of bounds, or conversion fails
        """
        if 0 <= index < len(self.positional_args):
            value = self.positional_args[index].value
            if isinstance(value, expected_type):
                return value
            # Try to convert if possible
            # Note: type: ignore comments below are required because mypy cannot narrow
            # TypeVar T based on runtime expected_type comparison. Each conversion is
            # guarded by an if-check ensuring the return type matches T.
            try:
                if expected_type == str:
                    # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because str() always returns str.
                    return str(value)  # type: ignore[return-value]
                if expected_type == int:
                    # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because int() returns int; arg-type ignored for Any input.
                    return int(value)  # type: ignore[return-value,arg-type]
                if expected_type == float:
                    # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because float() returns float; arg-type ignored for Any input.
                    return float(value)  # type: ignore[return-value,arg-type]
                if expected_type == bool:
                    if isinstance(value, str):
                        # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because bool comparison returns bool.
                        return value.lower() in ("true", "1", "yes", "on")  # type: ignore[return-value]
                    # NOTE(OMN-1302): TypeVar T cannot be narrowed by expected_type check. Safe because bool() always returns bool.
                    return bool(value)  # type: ignore[return-value]
            except (ValueError, TypeError):
                pass
        return default

    def add_named_argument(
        self,
        name: str,
        value: object,
        arg_type: str = "string",
    ) -> None:
        """Add a named argument to the map."""
        # Caller is responsible for passing ArgumentValueType-compatible values
        arg_value = ModelArgumentValue(
            value=cast(ArgumentValueType, value),
            original_string=str(value),
            type_name=arg_type,
        )
        self.named_args[name] = arg_value

    def add_positional_argument(self, value: object, arg_type: str = "string") -> None:
        """Add a positional argument to the map."""
        # Caller is responsible for passing ArgumentValueType-compatible values
        arg_value = ModelArgumentValue(
            value=cast(ArgumentValueType, value),
            original_string=str(value),
            type_name=arg_type,
        )
        self.positional_args.append(arg_value)

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for easy serialization."""
        # Custom serialization logic for argument map format
        result: dict[str, object] = {}

        # Add positional args
        for i, arg in enumerate(self.positional_args):
            result[f"pos_{i}"] = arg.value

        # Add named args
        for name, arg in self.named_args.items():
            result[name] = arg.value

        return result

    def get_argument_count(self) -> int:
        """Get total number of arguments (positional + named)."""
        return len(self.positional_args) + len(self.named_args)

    def get_argument_names(self) -> list[str]:
        """Get list of all named argument names."""
        return list(self.named_args.keys())
