"""
Result Factory Pattern for Model Creation.

Specialized factory for result-type models with success/error patterns.
"""

from __future__ import annotations

from typing import TypeVar, Unpack

from pydantic import BaseModel

from omnibase_core.types.typed_dict_result_factory_kwargs import (
    TypedDictResultFactoryKwargs,
)

from .model_generic_factory import ModelGenericFactory

T = TypeVar("T", bound=BaseModel)


class ModelResultFactory(ModelGenericFactory[T]):
    """
    Specialized factory for result-type models.

    Provides common patterns for success/error result creation with
    standardized field names and behavior.
    """

    def __init__(self, model_class: type[T]) -> None:
        """Initialize result factory with common patterns."""
        super().__init__(model_class)

        # Register common result builders
        self.register_builder("success", self._build_success_result)
        self.register_builder("error", self._build_error_result)
        self.register_builder("validation_error", self._build_validation_error_result)

    def _build_success_result(
        self,
        **kwargs: Unpack[TypedDictResultFactoryKwargs],
    ) -> T:
        """Build a success result with standard fields."""
        # Remove conflicting fields and set standard success values
        filtered_kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in ["success", "error_message", "exit_code"]
        }
        return self.model_class(
            success=True,
            exit_code=kwargs.get("exit_code", 0),
            error_message=None,
            **filtered_kwargs,
        )

    def _build_error_result(self, **kwargs: Unpack[TypedDictResultFactoryKwargs]) -> T:
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
        self,
        **kwargs: Unpack[TypedDictResultFactoryKwargs],
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


# Export result factory class and types
__all__ = [
    "ModelResultFactory",
]
