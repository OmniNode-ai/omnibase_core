"""
Argument Map Model

Type-safe container for parsed CLI arguments that provides both positional
and named argument access with type conversion capabilities.
"""

from typing import Any, TypeVar

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_argument_value import ModelArgumentValue
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

    def get_typed(
        self,
        name: str,
        expected_type: type[T],
        default: T | None = None,
    ) -> T | None:
        """
        Type-safe argument retrieval with optional default.

        Args:
            name: Argument name to retrieve
            expected_type: Expected type for the argument value
            default: Default value if argument not found or wrong type

        Returns:
            The argument value cast to expected_type, or default
        """
        if name in self.named_args:
            value = self.named_args[name].value
            if isinstance(value, expected_type):
                return value
            # Try to convert if possible
            try:
                if expected_type == str:
                    return str(value)  # type: ignore[return-value]
                if expected_type == int:
                    return int(value)  # type: ignore[return-value,arg-type]
                if expected_type == float:
                    return float(value)  # type: ignore[return-value,arg-type]
                if expected_type == bool:
                    if isinstance(value, str):
                        return value.lower() in ("true", "1", "yes", "on")  # type: ignore[return-value]
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
        """Get list[Any]argument value."""
        if default is None:
            default = []
        result = self.get_typed(name, list[Any], default)
        return result if result is not None else default

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

        Args:
            index: Position index (0-based)
            expected_type: Expected type for the argument value
            default: Default value if argument not found or wrong type

        Returns:
            The argument value cast to expected_type, or default
        """
        if 0 <= index < len(self.positional_args):
            value = self.positional_args[index].value
            if isinstance(value, expected_type):
                return value
            # Try to convert if possible
            try:
                if expected_type == str:
                    return str(value)  # type: ignore[return-value]
                if expected_type == int:
                    return int(value)  # type: ignore[return-value,arg-type]
                if expected_type == float:
                    return float(value)  # type: ignore[return-value,arg-type]
                if expected_type == bool:
                    if isinstance(value, str):
                        return value.lower() in ("true", "1", "yes", "on")  # type: ignore[return-value]
                    return bool(value)  # type: ignore[return-value]
            except (ValueError, TypeError):
                pass
        return default

    def add_named_argument(
        self,
        name: str,
        value: Any,
        arg_type: str = "string",
    ) -> None:
        """Add a named argument to the map."""
        arg_value = ModelArgumentValue(
            value=value,
            original_string=str(value),
            type_name=arg_type,
        )
        self.named_args[name] = arg_value

    def add_positional_argument(self, value: Any, arg_type: str = "string") -> None:
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
        """Get list[Any]of all named argument names."""
        return list(self.named_args.keys())
