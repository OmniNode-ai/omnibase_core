"""
Capability Factory Pattern for Model Creation.

Specialized factory for capability-type models with standardized naming and metadata.
"""

from __future__ import annotations

from typing import TypeVar, Unpack

from pydantic import BaseModel

from omnibase_core.types import TypedDictCapabilityFactoryKwargs

from .model_generic_factory import ModelGenericFactory

T = TypeVar("T", bound=BaseModel)


class ModelCapabilityFactory(ModelGenericFactory[T]):
    """
    Specialized factory for capability-type models.

    Provides patterns for creating capability instances with
    standardized naming and metadata.
    """

    def __init__(self, model_class: type[T]) -> None:
        """Initialize capability factory with common patterns."""
        super().__init__(model_class)

        # Register common capability builders
        self.register_builder("standard", self._build_standard_capability)
        self.register_builder("deprecated", self._build_deprecated_capability)
        self.register_builder("experimental", self._build_experimental_capability)

    def _build_standard_capability(
        self,
        **kwargs: Unpack[TypedDictCapabilityFactoryKwargs],
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
        self,
        **kwargs: Unpack[TypedDictCapabilityFactoryKwargs],
    ) -> T:
        """Build a deprecated capability with warning metadata."""
        # Ensure deprecated flag is set
        kwargs["deprecated"] = True
        return self._build_standard_capability(**kwargs)

    def _build_experimental_capability(
        self,
        **kwargs: Unpack[TypedDictCapabilityFactoryKwargs],
    ) -> T:
        """Build an experimental capability with appropriate metadata."""
        # Set experimental flag if the model supports it
        if "experimental" not in kwargs:
            kwargs["experimental"] = True
        return self._build_standard_capability(**kwargs)


# Export model capability factory class
__all__ = [
    "ModelCapabilityFactory",
]
