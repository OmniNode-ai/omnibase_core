from pydantic import BaseModel, Field


class ModelEventAttributeInfo(BaseModel):
    """Structured event attributes."""

    category: str = Field(default="", description="Event category")
    importance: str = Field(default="medium", description="Event importance level")
    tags: list[str] = Field(default_factory=list, description="Event tags")
    custom_attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom attributes",
    )
    classification: str = Field(default="", description="Event classification")
