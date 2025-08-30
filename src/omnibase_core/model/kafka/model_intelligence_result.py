"""ModelIntelligenceResult: Strongly typed intelligence analysis result"""

from pydantic import BaseModel, Field


class ModelIntelligenceResult(BaseModel):
    """Strongly typed intelligence analysis result"""

    uid: str = Field(..., description="Unique analysis identifier")
    analysis_type: str = Field(..., description="Type of analysis performed")
    summary: str = Field(..., description="Analysis summary")
    confidence_score: float = Field(..., description="Confidence level 0.0-1.0")
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Analysis metadata",
    )
    timestamp: str = Field(..., description="ISO timestamp of analysis")
