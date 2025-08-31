"""Strongly typed model for tool execution statistics."""

from pydantic import BaseModel, Field


class ModelToolStats(BaseModel):
    """Model for tool execution statistics."""

    count: int = Field(0, description="Total number of executions", ge=0)
    total_duration: int = Field(0, description="Total duration in milliseconds", ge=0)
    errors: int = Field(0, description="Number of errors", ge=0)

    @property
    def average_duration(self) -> float:
        """Calculate average duration per execution."""
        return self.total_duration / self.count if self.count > 0 else 0.0

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        return (self.errors / self.count * 100) if self.count > 0 else 0.0
