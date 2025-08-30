"""Centralized ModelValidationConfig implementation."""

from pydantic import BaseModel


class ModelValidationConfig(BaseModel):
    """Generic validationconfig model for common use."""
