"""
Model for cost breakdown.

Cost breakdown by category or window.
"""

from pydantic import BaseModel, Field


class ModelCostBreakdown(BaseModel):
    """Cost breakdown by category or window."""

    model_generation: float = Field(0.0, description="Cost for model generation")
    code_analysis: float = Field(0.0, description="Cost for code analysis")
    testing: float = Field(0.0, description="Cost for testing")
    documentation: float = Field(0.0, description="Cost for documentation")
    architecture: float = Field(0.0, description="Cost for architecture")
    debugging: float = Field(0.0, description="Cost for debugging")
    refactoring: float = Field(0.0, description="Cost for refactoring")
    review: float = Field(0.0, description="Cost for review")
    other: float = Field(0.0, description="Cost for other activities")

    def get_total(self) -> float:
        """Get total cost across all categories."""
        return sum(
            [
                self.model_generation,
                self.code_analysis,
                self.testing,
                self.documentation,
                self.architecture,
                self.debugging,
                self.refactoring,
                self.review,
                self.other,
            ]
        )
