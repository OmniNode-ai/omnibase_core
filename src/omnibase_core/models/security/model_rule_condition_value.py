"""Rule Condition Value Model.

Value structure for rule conditions supporting various comparison types.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelRuleConditionValue(BaseModel):
    """Value structure for rule conditions supporting various comparison types."""

    model_config = ConfigDict(populate_by_name=True)

    # Comparison operators
    in_values: list[str] | None = Field(
        default=None,
        alias="$in",
        description="Values to match against",
    )
    regex: str | None = Field(
        default=None,
        alias="$regex",
        description="Regular expression pattern",
    )
    gte: int | None = Field(
        default=None,
        alias="$gte",
        description="Greater than or equal to value",
    )
    lte: int | None = Field(
        default=None,
        alias="$lte",
        description="Less than or equal to value",
    )
