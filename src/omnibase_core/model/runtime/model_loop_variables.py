"""Loop variables model."""

from pydantic import BaseModel, Field


class ModelLoopVariables(BaseModel):
    """Variables used in loop execution."""

    current_item: str | int | float | bool | None = Field(
        default=None,
        description="Current loop item",
    )
    current_index: int | None = Field(default=None, description="Current loop index")
    iteration_count: int = Field(
        default=0,
        description="Number of iterations completed",
    )
    collection_size: int | None = Field(
        default=None,
        description="Size of collection being iterated",
    )
    loop_id: str | None = Field(default=None, description="Loop identifier")
    custom_variables: list[str] | None = Field(
        default=None,
        description="Additional custom loop variables",
    )
