#!/usr/bin/env python3
"""
Canonicalization Policy Model - ONEX Standards Compliant.

Strongly-typed model for canonicalization policies.
"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_canonicalization_policy_config import ModelConfig


class ModelCanonicalizationPolicy(BaseModel):
    """
    Strongly typed model for canonicalization policies.

    Represents canonicalization configuration with proper type safety.
    """

    canonicalize_body: Callable[..., Any] = Field(
        default=...,
        description="Function to canonicalize body content",
    )

    def get_canonicalizer(self) -> Callable[..., Any]:
        """Get the canonicalization function."""
        return self.canonicalize_body

    def canonicalize(self, body: str) -> str:
        """Apply canonicalization to body content."""
        return self.canonicalize_body(body)
