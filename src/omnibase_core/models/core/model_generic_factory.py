"""
Generic Factory Pattern for Model Creation.

Provides a consistent, type-safe factory pattern to replace repetitive
factory methods across CLI, Config, Nodes, and Validation domains.

Restructured to reduce string field violations through logical grouping.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Unpack

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_severity_level import EnumSeverityLevel
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictFactoryKwargs

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict


class ModelGenericFactory[T: BaseModel]:
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

    def __init__(self, model_class: type[T]) -> None:
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
            factory: Callable[..., Any]that returns an instance of T
        """
        self._factories[name] = factory

    def register_builder(self, name: str, builder: Callable[..., T]) -> None:
        """
        Register a builder method for creating instances with parameters.

        Args:
            name: Builder identifier
            builder: Callable[..., Any]that takes keyword arguments and returns an instance of T
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
            ModelOnexError: If factory name is not registered
        """
        if name not in self._factories:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.NOT_FOUND,
                message=f"Unknown factory: {name} for {self.model_class.__name__}",
                details=ModelErrorContext.with_context(
                    {
                        "factory_name": ModelSchemaValue.from_value(name),
                        "model_class": ModelSchemaValue.from_value(
                            self.model_class.__name__,
                        ),
                    },
                ),
            )
        return self._factories[name]()

    def build(self, builder_name: str, **kwargs: Unpack[TypedDictFactoryKwargs]) -> T:
        """
        Build instance using registered builder method.

        Args:
            builder_name: Builder name to use
            **kwargs: Arguments to pass to the builder

        Returns:
            New instance of T

        Raises:
            ModelOnexError: If builder name is not registered
        """
        if builder_name not in self._builders:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.NOT_FOUND,
                message=f"Unknown builder: {builder_name} for {self.model_class.__name__}",
                details=ModelErrorContext.with_context(
                    {
                        "builder_name": ModelSchemaValue.from_value(builder_name),
                        "model_class": ModelSchemaValue.from_value(
                            self.model_class.__name__,
                        ),
                    },
                ),
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
        model_class: type[T],
        result_data: ModelSchemaValue | None = None,
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
        cls,
        model_class: type[T],
        error: str,
        **kwargs: Unpack[TypedDictFactoryKwargs],
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

    # Export core factory class

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""

        # Factory instances don't have model_dump - serialize factory state instead
        result: SerializedDict = {
            "model_class": self.model_class.__name__,
            "factories": list(self._factories.keys()),
            "builders": list(self._builders.keys()),
        }
        return result

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

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


__all__ = [
    "ModelGenericFactory",
]
