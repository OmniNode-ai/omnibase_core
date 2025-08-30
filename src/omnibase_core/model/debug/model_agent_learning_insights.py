"""
Model for agent learning insights in debug intelligence system.

This model represents learning insights extracted from agent debug history
for continuous improvement and pattern recognition.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class ModelAgentLearningInsights(BaseModel):
    """Model for agent learning insights."""

    agent_id: str = Field(description="ID of the agent")
    success_rate: float = Field(description="Success rate as a percentage")
    total_attempts: int = Field(description="Total number of attempts logged")
    successful_attempts: int = Field(description="Number of successful attempts")
    failed_attempts: int = Field(description="Number of failed attempts")
    most_common_failures: Dict[str, int] = Field(
        default_factory=dict,
        description="Most common failure categories and their counts",
    )
    successful_techniques: List[str] = Field(
        default_factory=list, description="List of techniques that led to success"
    )
    improvement_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for improvement based on patterns",
    )
    confidence_score: float = Field(
        description="Confidence score for the insights (0.0 to 1.0)"
    )
    insights_summary: str = Field(description="Human-readable summary of insights")
