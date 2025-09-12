"""
Distance metric model for Qdrant vector similarity calculations.

This model defines distance metrics used for vector similarity,
following ONEX canonical patterns favoring models over enums.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ModelDistanceMetric(BaseModel):
    """Model representing a distance metric for vector similarity calculations."""

    metric_type: Literal["Cosine", "Euclidean", "Dot", "Manhattan"] = Field(
        default="Cosine",
        description="Type of distance metric to use for similarity calculation",
    )

    @property
    def is_cosine(self) -> bool:
        """Check if this is a cosine distance metric."""
        return self.metric_type == "Cosine"

    @property
    def is_euclidean(self) -> bool:
        """Check if this is a Euclidean distance metric."""
        return self.metric_type == "Euclidean"

    @property
    def is_dot_product(self) -> bool:
        """Check if this is a dot product distance metric."""
        return self.metric_type == "Dot"

    @property
    def is_manhattan(self) -> bool:
        """Check if this is a Manhattan distance metric."""
        return self.metric_type == "Manhattan"
