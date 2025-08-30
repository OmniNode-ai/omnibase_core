"""
Model for similar solutions in debug intelligence system.

This model represents similar solutions found in the knowledge base
for helping agents learn from past successful attempts.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelSimilarSolution(BaseModel):
    """Model for similar solution entries."""

    solution_id: str = Field(description="Unique identifier for the solution")
    task_description: str = Field(description="Description of the original task")
    approach_taken: str = Field(description="Approach that was successful")
    code_snippet: Optional[str] = Field(
        default=None, description="Code snippet from the successful solution"
    )
    tools_used: List[str] = Field(
        default_factory=list, description="Tools used in the successful solution"
    )
    confidence_score: float = Field(
        description="Confidence score for similarity (0.0 to 1.0)"
    )
    keywords_matched: List[str] = Field(
        default_factory=list,
        description="Keywords that matched between problem and solution",
    )
    execution_time_seconds: Optional[float] = Field(
        default=None, description="Execution time of the original solution"
    )
    success_pattern_id: Optional[str] = Field(
        default=None, description="ID of the success pattern this solution belongs to"
    )
