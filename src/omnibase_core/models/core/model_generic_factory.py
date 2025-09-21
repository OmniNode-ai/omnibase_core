"""
Generic Factory Pattern for Model Creation.

Provides a consistent, type-safe factory pattern to replace repetitive
factory methods across CLI, Config, Nodes, and Validation domains.

Restructured to reduce string field violations through logical grouping.
"""

from __future__ import annotations

from typing import Any, Callable, Generic, Type, TypedDict, TypeVar, Unpack

from pydantic import BaseModel

from ...enums.enum_severity_level import EnumSeverityLevel


# Structured TypedDicts to reduce string field violations
class TypedDictExecutionParams(TypedDict, total=False):
    """Execution-related factory parameters."""

    success: bool
    exit_code: int
    error_message: str | None
    data: str | int | float | bool | None


class TypedDictMetadataParams(TypedDict, total=False):
    """Metadata-related factory parameters."""

    name: str
    value: str
    description: str
    deprecated: bool
    experimental: bool


class TypedDictMessageParams(TypedDict, total=False):
    """Message-related factory parameters."""

    message: str
    severity: EnumSeverityLevel | None


# Main factory kwargs that combines sub-groups
class TypedDictFactoryKwargs(
    TypedDictExecutionParams,
    TypedDictMetadataParams,
    TypedDictMessageParams,
    total=False,
):
    """
    Typed dictionary for factory method parameters.

    Restructured using composition to reduce string field count.
    """

    pass


T = TypeVar("T", bound=BaseModel)


class ModelGenericFactory(Generic[T]):
    """
    Generic factory for creating typed model instances with consistent patterns.

    This factory provides a centralized way to create model instances with
    registered factory methods and builders, ensuring type safety and
    consistent patterns across the codebase.

    Example usage:
        # Create a factory for CLI results
        cli_factory = ModelGenericFactory(ModelCliResult)

        # Register factory methods
        cli_factory.register_factory("success", lambda: ModelCliResult.create_success(...))
        cli_factory.register_builder("custom", lambda **kwargs: ModelCliResult(**kwargs))

        # Use the factory
        result = cli_factory.create("success")
        custom_result = cli_factory.build("custom", execution=execution, success=True)
    """

    def __init__(self, model_class: Type[T]) -> None:
        """
        Initialize the factory for a specific model class.

        Args:
            model_class: The model class this factory will create instances of
        """
        self.model_class = model_class
        self._factories: dict[str, Callable[[], T]] = {}
        self._builders: dict[str, Callable[..., T]] = {}

    def register_factory(self, name: str, factory: Callable[[], T]) -> None:
        """
        Register a factory method for creating instances with no parameters.

        Args:
            name: Factory identifier
            factory: Callable that returns an instance of T
        """
        self._factories[name] = factory

    def register_builder(self, name: str, builder: Callable[..., T]) -> None:
        """
        Register a builder method for creating instances with parameters.

        Args:
            name: Builder identifier
            builder: Callable that takes keyword arguments and returns an instance of T
        """
        self._builders[name] = builder

    def create(self, name: str) -> T:
        """
        Create instance using registered factory method.

        Args:
            name: Factory name to use

        Returns:
            New instance of T

        Raises:
            ValueError: If factory name is not registered
        """
        if name not in self._factories:
            raise ValueError(f"Unknown factory: {name} for {self.model_class.__name__}")
        return self._factories[name]()

    def build(self, builder_name: str, **kwargs: Unpack[TypedDictFactoryKwargs]) -> T:
        """
        Build instance using registered builder method.

        Args:
            builder_name: Builder name to use
            **kwargs: Typed arguments to pass to the builder

        Returns:
            New instance of T

        Raises:
            ValueError: If builder name is not registered
        """
        if builder_name not in self._builders:
            raise ValueError(
                f"Unknown builder: {builder_name} for {self.model_class.__name__}"
            )
        return self._builders[builder_name](**kwargs)

    def list_factories(self) -> list[str]:
        """Get list of registered factory names."""
        return list(self._factories.keys())

    def list_builders(self) -> list[str]:
        """Get list of registered builder names."""
        return list(self._builders.keys())

    def has_factory(self, name: str) -> bool:
        """Check if factory is registered."""
        return name in self._factories

    def has_builder(self, name: str) -> bool:
        """Check if builder is registered."""
        return name in self._builders

    @classmethod
    def create_success_result(
        cls,
        model_class: Type[T],
        result_data: str | int | float | bool | None,
        **kwargs: Unpack[TypedDictFactoryKwargs],
    ) -> T:
        """
        Generic success result factory.

        This is a utility method for creating success results. The model
        must have 'success' and 'data' fields.

        Args:
            model_class: Model class to instantiate
            result_data: Success data
            **kwargs: Additional model fields

        Returns:
            New success result instance
        """
        return model_class(success=True, data=result_data, **kwargs)

    @classmethod
    def create_error_result(
        cls, model_class: Type[T], error: str, **kwargs: Unpack[TypedDictFactoryKwargs]
    ) -> T:
        """
        Generic error result factory.

        This is a utility method for creating error results. The model
        must have 'success' and 'error_message' fields.

        Args:
            model_class: Model class to instantiate
            error: Error message
            **kwargs: Additional model fields

        Returns:
            New error result instance
        """
        # Convert string severity to enum if provided
        if "severity" in kwargs and isinstance(kwargs["severity"], str):
            kwargs["severity"] = EnumSeverityLevel.from_string(kwargs["severity"])

        return model_class(success=False, error_message=error, **kwargs)


# Export core factory class and types
__all__ = [
    "ModelGenericFactory",
    "TypedDictFactoryKwargs",
    "TypedDictExecutionParams",
    "TypedDictMetadataParams",
    "TypedDictMessageParams",
]
