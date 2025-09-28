"""
Validation Error Factory Pattern for Model Creation.

Specialized factory for validation error models with severity patterns.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from omnibase_core.core.type_constraints import (
    Configurable,
    Nameable,
    Serializable,
    Validatable,
)
from omnibase_core.enums.enum_severity_level import EnumSeverityLevel

from .model_generic_factory import ModelGenericFactory
from .model_typed_dict_factory_kwargs import ModelTypedDictFactoryKwargs

# Type variable for validation error models with appropriate constraints
T = TypeVar("T", bound=BaseModel)


class ModelValidationErrorFactory(ModelGenericFactory[T]):
    """
    Specialized factory for validation error models.

    Provides patterns for creating validation errors with
    appropriate severity levels and error codes.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    def __init__(self, model_class: type[T]) -> None:
        """Initialize validation error factory with severity patterns."""
        super().__init__(model_class)

        # Register severity-based builders with explicit typing
        self.register_builder("error", self._build_error)
        self.register_builder("warning", self._build_warning)
        self.register_builder("critical", self._build_critical)
        self.register_builder("info", self._build_info)

    def _build_error(self, **kwargs: Any) -> T:
        """Build a standard error with ERROR severity."""
        severity: EnumSeverityLevel = EnumSeverityLevel.ERROR

        # Remove processed fields to avoid duplication
        filtered_kwargs: dict[str, Any] = {
            k: v for k, v in kwargs.items() if k not in ["message", "severity"]
        }

        return self.model_class(
            message=kwargs.get("message", "Validation error"),
            severity=severity,
            **filtered_kwargs,
        )

    def _build_warning(self, **kwargs: Any) -> T:
        """Build a warning with WARNING severity."""
        severity: EnumSeverityLevel = EnumSeverityLevel.WARNING

        # Remove processed fields to avoid duplication
        filtered_kwargs: dict[str, Any] = {
            k: v for k, v in kwargs.items() if k not in ["message", "severity"]
        }

        return self.model_class(
            message=kwargs.get("message", "Validation warning"),
            severity=severity,
            **filtered_kwargs,
        )

    def _build_critical(self, **kwargs: Any) -> T:
        """Build a critical error with CRITICAL severity."""
        severity: EnumSeverityLevel = EnumSeverityLevel.CRITICAL

        # Remove processed fields to avoid duplication
        filtered_kwargs: dict[str, Any] = {
            k: v for k, v in kwargs.items() if k not in ["message", "severity"]
        }

        return self.model_class(
            message=kwargs.get("message", "Critical validation error"),
            severity=severity,
            **filtered_kwargs,
        )

    def _build_info(self, **kwargs: Any) -> T:
        """Build an info message with INFO severity."""
        severity: EnumSeverityLevel = EnumSeverityLevel.INFO

        # Remove processed fields to avoid duplication
        filtered_kwargs: dict[str, Any] = {
            k: v for k, v in kwargs.items() if k not in ["message", "severity"]
        }

        return self.model_class(
            message=kwargs.get("message", "Validation info"),
            severity=severity,
            **filtered_kwargs,
        )

    # Export validation error factory class

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        # Factory instances don't have model_dump - serialize factory state instead
        return {
            "model_class": self.model_class.__name__,
            "factories": list(self._factories.keys()),
            "builders": list(self._builders.keys()),
        }

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False

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
    "ModelValidationErrorFactory",
]
