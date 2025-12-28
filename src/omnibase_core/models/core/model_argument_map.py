"""
Argument Map Model

Type-safe container for parsed CLI arguments that provides both positional
and named argument access with type conversion capabilities.
"""

from typing import TypeVar, cast, overload

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_argument_value import (
    ArgumentValueType,
    ModelArgumentValue,
)
from omnibase_core.types.type_serializable_value import SerializedDict

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

    @overload
    def get_typed(
        self,
        name: str,
        expected_type: type[str],
        default: str | None = None,
    ) -> str | None: ...

    @overload
    def get_typed(
        self,
        name: str,
        expected_type: type[bool],
        default: bool | None = None,
    ) -> bool | None: ...

    @overload
    def get_typed(
        self,
        name: str,
        expected_type: type[int],
        default: int | None = None,
    ) -> int | None: ...

    @overload
    def get_typed(
        self,
        name: str,
        expected_type: type[float],
        default: float | None = None,
    ) -> float | None: ...

    @overload
    def get_typed(
        self,
        name: str,
        expected_type: type[T],
        default: T | None = None,
    ) -> T | None: ...

    def get_typed(
        self,
        name: str,
        expected_type: type[T],
        default: T | None = None,
    ) -> T | None:
        """
        Type-safe argument retrieval with optional default.

        This method provides type-safe access to named arguments with automatic
        type conversion when possible. It uses function overloads to provide
        precise return types for common primitive types (str, bool, int, float)
        while also supporting generic types through a catch-all overload.

        Overload Behavior:
            - ``get_typed(name, str, default)`` -> ``str | None``
            - ``get_typed(name, bool, default)`` -> ``bool | None``
            - ``get_typed(name, int, default)`` -> ``int | None``
            - ``get_typed(name, float, default)`` -> ``float | None``
            - ``get_typed(name, T, default)`` -> ``T | None`` (generic fallback)

        Type Conversion:
            If the stored value doesn't match the expected type, the method
            attempts conversion:

            - ``str``: Converts any value using ``str(value)``
            - ``bool``: Parses strings like "true", "1", "yes", "on" as True
            - ``int``: Converts via ``int(str(value))``
            - ``float``: Converts via ``float(str(value))``

        Args:
            name: Argument name to retrieve from named_args
            expected_type: Expected type for the argument value (str, bool, int,
                float, or any type T)
            default: Default value if argument not found, wrong type, or
                conversion fails. Defaults to None.

        Returns:
            The argument value cast to expected_type if found and convertible,
            otherwise the default value.

        Example:
            >>> args = ModelArgumentMap()
            >>> args.add_named_argument("count", "42", "string")
            >>> args.get_typed("count", int)  # Returns 42 (int)
            >>> args.get_typed("missing", str, "default")  # Returns "default"
            >>> args.get_typed("count", bool)  # Returns True (non-zero)
        """
        if name in self.named_args:
            value = self.named_args[name].value
            if isinstance(value, expected_type):
                return value
            # Try to convert if possible
            try:
                if expected_type == str:
                    return cast(T, str(value))
                if expected_type == bool:
                    if isinstance(value, str):
                        return cast(T, value.lower() in ("true", "1", "yes", "on"))
                    return cast(T, bool(value))
                if expected_type == int:
                    return cast(T, int(str(value)))
                if expected_type == float:
                    return cast(T, float(str(value)))
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
        """Get list argument value, converting all elements to strings."""
        if default is None:
            default = []
        if name in self.named_args:
            return self.named_args[name].get_as_list()
        return default

    def has_argument(self, name: str) -> bool:
        """Check if named argument exists."""
        return name in self.named_args

    @overload
    def get_positional(
        self,
        index: int,
        expected_type: type[str],
        default: str | None = None,
    ) -> str | None: ...

    @overload
    def get_positional(
        self,
        index: int,
        expected_type: type[bool],
        default: bool | None = None,
    ) -> bool | None: ...

    @overload
    def get_positional(
        self,
        index: int,
        expected_type: type[int],
        default: int | None = None,
    ) -> int | None: ...

    @overload
    def get_positional(
        self,
        index: int,
        expected_type: type[float],
        default: float | None = None,
    ) -> float | None: ...

    @overload
    def get_positional(
        self,
        index: int,
        expected_type: type[T],
        default: T | None = None,
    ) -> T | None: ...

    def get_positional(
        self,
        index: int,
        expected_type: type[T],
        default: T | None = None,
    ) -> T | None:
        """
        Get positional argument by index with type conversion.

        This method provides type-safe access to positional arguments with
        automatic type conversion when possible. Like ``get_typed()``, it uses
        function overloads to provide precise return types for common primitive
        types (str, bool, int, float) while also supporting generic types.

        Overload Behavior:
            - ``get_positional(index, str, default)`` -> ``str | None``
            - ``get_positional(index, bool, default)`` -> ``bool | None``
            - ``get_positional(index, int, default)`` -> ``int | None``
            - ``get_positional(index, float, default)`` -> ``float | None``
            - ``get_positional(index, T, default)`` -> ``T | None`` (generic fallback)

        Type Conversion:
            If the stored value doesn't match the expected type, the method
            attempts conversion (same rules as ``get_typed()``):

            - ``str``: Converts any value using ``str(value)``
            - ``bool``: Parses strings like "true", "1", "yes", "on" as True
            - ``int``: Converts via ``int(str(value))``
            - ``float``: Converts via ``float(str(value))``

        Args:
            index: Position index (0-based) into positional_args list
            expected_type: Expected type for the argument value (str, bool, int,
                float, or any type T)
            default: Default value if index out of bounds, wrong type, or
                conversion fails. Defaults to None.

        Returns:
            The argument value cast to expected_type if found and convertible,
            otherwise the default value.

        Example:
            >>> args = ModelArgumentMap()
            >>> args.add_positional_argument("hello", "string")
            >>> args.add_positional_argument("42", "string")
            >>> args.get_positional(0, str)  # Returns "hello"
            >>> args.get_positional(1, int)  # Returns 42 (int)
            >>> args.get_positional(99, str, "default")  # Returns "default"
        """
        if 0 <= index < len(self.positional_args):
            value = self.positional_args[index].value
            if isinstance(value, expected_type):
                return value
            # Try to convert if possible
            try:
                if expected_type == str:
                    return cast(T, str(value))
                if expected_type == bool:
                    if isinstance(value, str):
                        return cast(T, value.lower() in ("true", "1", "yes", "on"))
                    return cast(T, bool(value))
                if expected_type == int:
                    return cast(T, int(str(value)))
                if expected_type == float:
                    return cast(T, float(str(value)))
            except (ValueError, TypeError):
                pass
        return default

    def add_named_argument(
        self,
        name: str,
        value: ArgumentValueType,
        arg_type: str = "string",
    ) -> None:
        """Add a named argument to the map."""
        arg_value = ModelArgumentValue(
            value=value,
            original_string=str(value),
            type_name=arg_type,
        )
        self.named_args[name] = arg_value

    def add_positional_argument(
        self, value: ArgumentValueType, arg_type: str = "string"
    ) -> None:
        """Add a positional argument to the map."""
        arg_value = ModelArgumentValue(
            value=value,
            original_string=str(value),
            type_name=arg_type,
        )
        self.positional_args.append(arg_value)

    def to_dict(self) -> SerializedDict:
        """Convert to dictionary for easy serialization."""
        # Custom serialization logic for argument map format
        result: SerializedDict = {}

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
