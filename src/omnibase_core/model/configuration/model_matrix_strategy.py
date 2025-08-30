"""
Matrix strategy model.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelMatrixStrategy(BaseModel):
    """Matrix strategy configuration."""

    matrix: Dict[str, List[Any]] = Field(..., description="Matrix dimensions")
    include: Optional[List[Dict[str, Any]]] = Field(
        None, description="Matrix inclusions"
    )
    exclude: Optional[List[Dict[str, Any]]] = Field(
        None, description="Matrix exclusions"
    )
