"""
Argument Map Model

Type-safe container for parsed CLI arguments that provides both positional
and named argument access with type conversion capabilities.
"""

from typing import TypeVar, cast, overload

from pydantic import BaseModel, ConfigDict, Field

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

    model_config = ConfigDict(extra="forbid", from_attributes=True)

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
        expected_type: type[T],
        default: None = None,
    ) -> T | None: ...

    @overload
    def get_typed(
        self,
        name: str,
        expected_type: type[T],
        default: T,
    ) -> T: ...

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

        Overloads:
            - get_typed(name, type) -> T | None: Returns None if not found
            - get_typed(name, type, default) -> T: Returns default if not found

        Type Conversion Behavior:
            - str: Any value converted via str()
            - int: Numeric strings/values converted via int()
            - float: Numeric strings/values converted via float()
            - bool: String values "true", "1", "yes", "on" (case-insensitive) -> True;
                    other values converted via bool()

        Note:
            cast(T, ...) is used because mypy cannot narrow TypeVar T based on runtime
            expected_type comparisons. Each conversion is guarded by an if-check ensuring
            the return type matches T at runtime.

        Args:
            name: Argument name to retrieve
            expected_type: Expected type for the argument value (supports str, int,
                float, bool with automatic conversion)
            default: Default value if argument not found or conversion fails

        Returns:
            When default is None (or omitted): T | None - the value or None
            When default is T: T - the value or the provided default (never None)
        """
        if name in self.named_args:
            value = self.named_args[name].value
            if isinstance(value, expected_type):
                return value
            # Try to convert if possible.
            # NOTE(OMN-1073): cast(T, ...) is used because mypy cannot narrow TypeVar T
            # based on runtime expected_type comparison. Each conversion is guarded by an
            # if-check ensuring the return type matches T at runtime. The cast is safe
            # because the converter function (str/int/float/bool) guarantees the output type.
            try:
                if expected_type == str:
                    # NOTE(OMN-1073): Safe cast - str() always returns str.
                    return cast(T, str(value))
                if expected_type == int:
                    # NOTE(OMN-1073): Safe cast - int(value) returns int or raises.
                    # Narrow to types int() accepts (exclude lists).
                    if isinstance(value, str | int | float | bool):
                        return cast(T, int(value))
                if expected_type == float:
                    # NOTE(OMN-1073): Safe cast - float(value) returns float or raises.
                    # Narrow to types float() accepts (exclude lists).
                    if isinstance(value, str | int | float | bool):
                        return cast(T, float(value))
                if expected_type == bool:
                    # NOTE(OMN-1073): Safe cast - comparison result is always bool.
                    if isinstance(value, str):
                        return cast(T, value.lower() in ("true", "1", "yes", "on"))
                    return cast(T, bool(value))
            except (TypeError, ValueError):
                pass
        return default

    def get_string(self, name: str, default: str = "") -> str:
        """Get string argument value."""
        return self.get_typed(name, str, default)

    def get_int(self, name: str, default: int = 0) -> int:
        """Get integer argument value."""
        return self.get_typed(name, int, default)

    def get_float(self, name: str, default: float = 0.0) -> float:
        """Get float argument value."""
        return self.get_typed(name, float, default)

    def get_bool(self, name: str, default: bool = False) -> bool:
        """Get boolean argument value."""
        return self.get_typed(name, bool, default)

    def get_list(self, name: str, default: list[str] | None = None) -> list[str]:
        """Get list argument value with string conversion.

        All list items are converted to strings. Returns empty list if argument
        not found and no default provided.
        """
        if default is None:
            default = []
        # Use bare 'list' for isinstance check at runtime (generic list[str] not valid).
        result = self.get_typed(name, list, default)
        # Ensure we return list[str] by converting items
        return [str(item) for item in result]

    def has_argument(self, name: str) -> bool:
        """Check if named argument exists."""
        return name in self.named_args

    @overload
    def get_positional(
        self,
        index: int,
        expected_type: type[T],
        default: None = None,
    ) -> T | None: ...

    @overload
    def get_positional(
        self,
        index: int,
        expected_type: type[T],
        default: T,
    ) -> T: ...

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

        Overloads:
            - get_positional(index, type) -> T | None: Returns None if not found
            - get_positional(index, type, default) -> T: Returns default if not found

        Type Conversion Behavior:
            - str: Any value converted via str()
            - int: Numeric strings/values converted via int()
            - float: Numeric strings/values converted via float()
            - bool: String values "true", "1", "yes", "on" (case-insensitive) -> True;
                    other values converted via bool()

        Note:
            cast(T, ...) is used because mypy cannot narrow TypeVar T based on runtime
            expected_type comparisons. Each conversion is guarded by an if-check ensuring
            the return type matches T at runtime.

        Args:
            index: Position index (0-based)
            expected_type: Expected type for the argument value (supports str, int,
                float, bool with automatic conversion)
            default: Default value if argument not found or conversion fails

        Returns:
            When default is None (or omitted): T | None - the value or None
            When default is T: T - the value or the provided default (never None)
        """
        if 0 <= index < len(self.positional_args):
            value = self.positional_args[index].value
            if isinstance(value, expected_type):
                return value
            # Try to convert if possible.
            # NOTE(OMN-1073): cast(T, ...) is used because mypy cannot narrow TypeVar T
            # based on runtime expected_type comparison. Each conversion is guarded by an
            # if-check ensuring the return type matches T at runtime. The cast is safe
            # because the converter function (str/int/float/bool) guarantees the output type.
            try:
                if expected_type == str:
                    # NOTE(OMN-1073): Safe cast - str() always returns str.
                    return cast(T, str(value))
                if expected_type == int:
                    # NOTE(OMN-1073): Safe cast - int(value) returns int or raises.
                    # Narrow to types int() accepts (exclude lists).
                    if isinstance(value, str | int | float | bool):
                        return cast(T, int(value))
                if expected_type == float:
                    # NOTE(OMN-1073): Safe cast - float(value) returns float or raises.
                    # Narrow to types float() accepts (exclude lists).
                    if isinstance(value, str | int | float | bool):
                        return cast(T, float(value))
                if expected_type == bool:
                    # NOTE(OMN-1073): Safe cast - comparison result is always bool.
                    if isinstance(value, str):
                        return cast(T, value.lower() in ("true", "1", "yes", "on"))
                    return cast(T, bool(value))
            except (TypeError, ValueError):
                pass
        return default

    def add_named_argument(
        self,
        name: str,
        value: object,
        arg_type: str = "string",
    ) -> None:
        """Add a named argument to the map.

        Note:
            Caller is responsible for passing ArgumentValueType-compatible values
            (str, int, bool, float, list[str], list[int], list[float]).
        """
        # NOTE(OMN-1073): cast(ArgumentValueType, value) is used because the method
        # signature accepts `object` for API flexibility. The cast is safe when callers
        # pass ArgumentValueType-compatible values as documented. Pydantic validation
        # in ModelArgumentValue will raise ValidationError if incompatible types are passed.
        arg_value = ModelArgumentValue(
            value=cast(ArgumentValueType, value),
            original_string=str(value),
            type_name=arg_type,
        )
        self.named_args[name] = arg_value

    def add_positional_argument(self, value: object, arg_type: str = "string") -> None:
        """Add a positional argument to the map.

        Note:
            Caller is responsible for passing ArgumentValueType-compatible values
            (str, int, bool, float, list[str], list[int], list[float]).
        """
        # NOTE(OMN-1073): cast(ArgumentValueType, value) is used because the method
        # signature accepts `object` for API flexibility. The cast is safe when callers
        # pass ArgumentValueType-compatible values as documented. Pydantic validation
        # in ModelArgumentValue will raise ValidationError if incompatible types are passed.
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
