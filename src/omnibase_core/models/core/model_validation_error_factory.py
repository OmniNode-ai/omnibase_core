"""
Validation Error Factory Pattern for Model Creation.

Specialized factory for validation error models with severity patterns.
"""

from __future__ import annotations

from typing import TypeVar, Unpack

from pydantic import BaseModel

from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity

from .model_generic_factory import ModelGenericFactory, TypedDictFactoryKwargs

T = TypeVar("T", bound=BaseModel)


class ValidationErrorFactory(ModelGenericFactory[T]):
    """
    Specialized factory for validation error models.

    Provides patterns for creating validation errors with
    appropriate severity levels and error codes.
    """

    def __init__(self, model_class: type[T]) -> None:
        """Initialize validation error factory with severity patterns."""
        super().__init__(model_class)

        # Register severity-based builders
        self.register_builder("error", self._build_error)
        self.register_builder("warning", self._build_warning)
        self.register_builder("critical", self._build_critical)
        self.register_builder("info", self._build_info)

    def _build_error(self, **kwargs: Unpack[TypedDictFactoryKwargs]) -> T:
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

    def _build_warning(self, **kwargs: Unpack[TypedDictFactoryKwargs]) -> T:
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

    def _build_critical(self, **kwargs: Unpack[TypedDictFactoryKwargs]) -> T:
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

    def _build_info(self, **kwargs: Unpack[TypedDictFactoryKwargs]) -> T:
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


# Export validation error factory class
__all__ = [
    "ValidationErrorFactory",
]
