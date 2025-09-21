"""
Generic Factory Pattern for Model Creation.

Provides a consistent, type-safe factory pattern to replace repetitive
factory methods across CLI, Config, Nodes, and Validation domains.
"""

from typing import Any, Callable, Generic, Type, TypedDict, TypeVar, Unpack

from pydantic import BaseModel

from ...enums.enum_validation_severity import EnumValidationSeverity


# TypedDict for factory kwargs to replace loose **kwargs: Any
class FactoryKwargs(TypedDict, total=False):
    """Typed dictionary for factory method parameters."""

    success: bool
    exit_code: int
    error_message: str | None
    data: str | int | float | bool | None
    name: str
    value: str
    description: str
    deprecated: bool
    experimental: bool
    message: str
    severity: str


# TypedDict for result factory specific kwargs
class ResultFactoryKwargs(TypedDict, total=False):
    """Typed dictionary for result factory parameters."""

    success: bool
    exit_code: int
    error_message: str | None
    data: str | int | float | bool | None
    output_text: str | None
    warnings: list[str]


# TypedDict for capability factory specific kwargs
class CapabilityFactoryKwargs(TypedDict, total=False):
    """Typed dictionary for capability factory parameters."""

    name: str
    value: str
    description: str
    deprecated: bool
    experimental: bool
    enabled: bool


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

    def build(self, name: str, **kwargs: Unpack[FactoryKwargs]) -> T:
        """
        Build instance using registered builder method.

        Args:
            name: Builder name to use
            **kwargs: Typed arguments to pass to the builder

        Returns:
            New instance of T

        Raises:
            ValueError: If builder name is not registered
        """
        if name not in self._builders:
            raise ValueError(f"Unknown builder: {name} for {self.model_class.__name__}")
        return self._builders[name](**kwargs)

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
        data: str | int | float | bool | None,
        **kwargs: Unpack[FactoryKwargs],
    ) -> T:
        """
        Generic success result factory.

        This is a utility method for creating success results. The model
        must have 'success' and 'data' fields.

        Args:
            model_class: Model class to instantiate
            data: Success data
            **kwargs: Additional model fields

        Returns:
            New success result instance
        """
        return model_class(success=True, data=data, **kwargs)

    @classmethod
    def create_error_result(
        cls, model_class: Type[T], error: str, **kwargs: Unpack[FactoryKwargs]
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
        return model_class(success=False, error_message=error, **kwargs)


class ResultFactory(ModelGenericFactory[T]):
    """
    Specialized factory for result-type models.

    Provides common patterns for success/error result creation with
    standardized field names and behavior.
    """

    def __init__(self, model_class: Type[T]) -> None:
        """Initialize result factory with common patterns."""
        super().__init__(model_class)

        # Register common result builders
        self.register_builder("success", self._build_success_result)
        self.register_builder("error", self._build_error_result)
        self.register_builder("validation_error", self._build_validation_error_result)

    def _build_success_result(self, **kwargs: Unpack[ResultFactoryKwargs]) -> T:
        """Build a success result with standard fields."""
        # Remove conflicting fields and set standard success values
        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k not in ["success", "error_message"]
        }
        return self.model_class(
            success=True,
            exit_code=kwargs.get("exit_code", 0),
            error_message=None,
            **filtered_kwargs,
        )

    def _build_error_result(self, **kwargs: Unpack[ResultFactoryKwargs]) -> T:
        """Build an error result with standard fields."""
        # Remove conflicting fields and set standard error values
        filtered_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ["success", "exit_code", "error_message"]
        }
        return self.model_class(
            success=False,
            exit_code=kwargs.get("exit_code", 1),
            error_message=kwargs.get("error_message", "Unknown error"),
            **filtered_kwargs,
        )

    def _build_validation_error_result(
        self, **kwargs: Unpack[ResultFactoryKwargs]
    ) -> T:
        """Build a validation error result with standard fields."""
        # Remove conflicting fields and set standard validation error values
        filtered_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ["success", "exit_code", "error_message"]
        }
        return self.model_class(
            success=False,
            exit_code=kwargs.get("exit_code", 2),
            error_message=kwargs.get("error_message", "Validation failed"),
            **filtered_kwargs,
        )


class CapabilityFactory(ModelGenericFactory[T]):
    """
    Specialized factory for capability-type models.

    Provides patterns for creating capability instances with
    standardized naming and metadata.
    """

    def __init__(self, model_class: Type[T]) -> None:
        """Initialize capability factory with common patterns."""
        super().__init__(model_class)

        # Register common capability builders
        self.register_builder("standard", self._build_standard_capability)
        self.register_builder("deprecated", self._build_deprecated_capability)
        self.register_builder("experimental", self._build_experimental_capability)

    def _build_standard_capability(
        self, **kwargs: Unpack[CapabilityFactoryKwargs]
    ) -> T:
        """Build a standard capability with consistent naming."""
        name = kwargs.get("name", "UNKNOWN")
        value = kwargs.get("value", name.lower())

        # Remove processed fields to avoid duplication
        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k not in ["name", "value", "description"]
        }

        return self.model_class(
            name=name,
            value=value,
            description=kwargs.get("description", f"Standard capability: {name}"),
            **filtered_kwargs,
        )

    def _build_deprecated_capability(
        self, **kwargs: Unpack[CapabilityFactoryKwargs]
    ) -> T:
        """Build a deprecated capability with warning metadata."""
        # Ensure deprecated flag is set
        kwargs["deprecated"] = True
        return self._build_standard_capability(**kwargs)

    def _build_experimental_capability(
        self, **kwargs: Unpack[CapabilityFactoryKwargs]
    ) -> T:
        """Build an experimental capability with appropriate metadata."""
        # Set experimental flag if the model supports it
        if "experimental" not in kwargs:
            kwargs["experimental"] = True
        return self._build_standard_capability(**kwargs)


class ValidationErrorFactory(ModelGenericFactory[T]):
    """
    Specialized factory for validation error models.

    Provides patterns for creating validation errors with
    appropriate severity levels and error codes.
    """

    def __init__(self, model_class: Type[T]) -> None:
        """Initialize validation error factory with severity patterns."""
        super().__init__(model_class)

        # Register severity-based builders
        self.register_builder("error", self._build_error)
        self.register_builder("warning", self._build_warning)
        self.register_builder("critical", self._build_critical)
        self.register_builder("info", self._build_info)

    def _build_error(self, **kwargs: Unpack[FactoryKwargs]) -> T:
        """Build a standard error with ERROR severity."""
        severity: EnumValidationSeverity = EnumValidationSeverity.ERROR

        # Remove processed fields to avoid duplication
        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k not in ["message", "severity"]
        }

        return self.model_class(
            message=kwargs.get("message", "Validation error"),
            severity=severity,
            **filtered_kwargs,
        )

    def _build_warning(self, **kwargs: Unpack[FactoryKwargs]) -> T:
        """Build a warning with WARNING severity."""
        severity: EnumValidationSeverity = EnumValidationSeverity.WARNING

        # Remove processed fields to avoid duplication
        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k not in ["message", "severity"]
        }

        return self.model_class(
            message=kwargs.get("message", "Validation warning"),
            severity=severity,
            **filtered_kwargs,
        )

    def _build_critical(self, **kwargs: Unpack[FactoryKwargs]) -> T:
        """Build a critical error with CRITICAL severity."""
        severity: EnumValidationSeverity = EnumValidationSeverity.CRITICAL

        # Remove processed fields to avoid duplication
        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k not in ["message", "severity"]
        }

        return self.model_class(
            message=kwargs.get("message", "Critical validation error"),
            severity=severity,
            **filtered_kwargs,
        )

    def _build_info(self, **kwargs: Unpack[FactoryKwargs]) -> T:
        """Build an info message with INFO severity."""
        severity: EnumValidationSeverity = EnumValidationSeverity.INFO

        # Remove processed fields to avoid duplication
        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k not in ["message", "severity"]
        }

        return self.model_class(
            message=kwargs.get("message", "Validation info"),
            severity=severity,
            **filtered_kwargs,
        )


# Export all factory classes
__all__ = [
    "ModelGenericFactory",
    "ResultFactory",
    "CapabilityFactory",
    "ValidationErrorFactory",
]
