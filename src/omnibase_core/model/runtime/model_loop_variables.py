"""Loop variables model."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ModelLoopVariables(BaseModel):
    """Variables used in loop execution."""

    current_item: Optional[Union[str, int, float, bool]] = Field(
        default=None, description="Current loop item"
    )
    current_index: Optional[int] = Field(default=None, description="Current loop index")
    iteration_count: int = Field(
        default=0, description="Number of iterations completed"
    )
    collection_size: Optional[int] = Field(
        default=None, description="Size of collection being iterated"
    )
    loop_id: Optional[str] = Field(default=None, description="Loop identifier")
    custom_variables: Optional[List[str]] = Field(
        default=None, description="Additional custom loop variables"
    )
