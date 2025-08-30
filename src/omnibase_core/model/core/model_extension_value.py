"""
Extension value model.
"""

from typing import Any, Optional

from pydantic import BaseModel


class ModelExtensionValue(BaseModel):
    """
    Strongly typed model for extension values in x_extensions.
    Accepts any type for value (str, int, float, bool, dict, list, etc.) for protocol and legacy compatibility.
    """

    value: Optional[Any] = None
    description: Optional[str] = None
    # Add more fields as needed for extension use cases

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
