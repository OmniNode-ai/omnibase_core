#!/usr/bin/env python3
"""
Canonicalization Policy Model.

Strongly-typed model for canonicalization policies.
"""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field


class ModelCanonicalizationPolicy(BaseModel):
    """
    Strongly typed model for canonicalization policies.

    Represents canonicalization configuration with proper type safety.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    canonicalize_body: Callable[..., object] = Field(
        default=...,
        description="Function to canonicalize body content",
    )

    def get_canonicalizer(self) -> Callable[..., object]:
        """Get the canonicalization function."""
        return self.canonicalize_body

    def canonicalize(self, body: str) -> str:
        """Apply canonicalization to body content."""
        from typing import cast

        return cast("str", self.canonicalize_body(body))
