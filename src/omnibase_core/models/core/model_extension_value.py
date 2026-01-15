"""
Extension value model.
"""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.types import JsonSerializable


class ModelExtensionValue(BaseModel):
    """
    Strongly typed model for extension values in x_extensions.
    Accepts any type for value (str, int, float, bool, dict[str, Any], list[Any], etc.) for protocol and legacy compatibility.
    """

    value: JsonSerializable = None
    description: str | None = None
    # Add more fields as needed for extension use cases

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
