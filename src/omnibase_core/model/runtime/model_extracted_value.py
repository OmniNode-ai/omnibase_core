# Model for extracted values from paths
# DO NOT EDIT MANUALLY - regenerate using model generation tools


from pydantic import BaseModel, Field


class ModelExtractedValue(BaseModel):
    """Model for values extracted from execution paths."""

    value: str | int | float | bool | None = Field(
        ...,
        description="The extracted value",
    )
    source_path: str = Field(
        ...,
        description="Source path where value was extracted from",
    )
    value_type: str = Field(..., description="Type of the extracted value")
    is_valid: bool = Field(
        default=True,
        description="Whether the extraction was successful",
    )
