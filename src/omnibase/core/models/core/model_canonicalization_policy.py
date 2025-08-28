"""
Canonicalization Policy Model for ONEX Configuration System.

Strongly typed model for canonicalization policies.
"""

from typing import Callable

from pydantic import BaseModel, Field


class ModelCanonicalizationPolicy(BaseModel):
    """
    Strongly typed model for canonicalization policies.

    Represents canonicalization configuration with proper type safety.
    """

    canonicalize_body: Callable = Field(
        ..., description="Function to canonicalize body content"
    )

    class Config:
        arbitrary_types_allowed = True

    def get_canonicalizer(self) -> Callable:
        """Get the canonicalization function."""
        return self.canonicalize_body

    def canonicalize(self, body: str) -> str:
        """Apply canonicalization to body content."""
        return self.canonicalize_body(body)
