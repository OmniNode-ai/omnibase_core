"""
JSON Data Model for ONEX Configuration System.

Strongly typed model for JSON request body data.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.configuration.model_dict_config import ModelDictConfig


class ModelJsonField(BaseModel):
    """Strongly typed JSON field."""

    string_value: Optional[str] = Field(default=None, description="String value")
    number_value: Optional[float] = Field(default=None, description="Number value")
    boolean_value: Optional[bool] = Field(default=None, description="Boolean value")
    array_values: Optional[List[str]] = Field(
        default=None, description="Array of string values"
    )

    def get_value(self):
        """Get the actual value based on what's set."""
        if self.string_value is not None:
            return self.string_value
        elif self.number_value is not None:
            return self.number_value
        elif self.boolean_value is not None:
            return self.boolean_value
        elif self.array_values is not None:
            return self.array_values
        return None


class ModelJsonData(BaseModel):
    """
    Strongly typed model for JSON request body data.

    Represents JSON data that can be sent in HTTP request bodies
    with proper type safety.
    """

    fields: Dict[str, ModelJsonField] = Field(
        default_factory=dict, description="JSON fields with strongly typed values"
    )

    def to_dict(self) -> ModelDictConfig:
        """Convert to strongly typed dict config for serialization."""
        result = {}
        for key, field in self.fields.items():
            result[key] = str(field.get_value())
        return ModelDictConfig(data=result)

    @classmethod
    def from_dict(cls, data: ModelDictConfig) -> "ModelJsonData":
        """Create from strongly typed dict config."""
        fields = {}
        for key, value in data.data.items():
            field = ModelJsonField()
            # Since ModelDictConfig stores string values, parse them appropriately
            if value.lower() in ["true", "false"]:
                field.boolean_value = value.lower() == "true"
            elif value.replace(".", "").replace("-", "").isdigit():
                field.number_value = float(value)
            elif value.startswith("[") and value.endswith("]"):
                # Simple array parsing - could be enhanced
                array_content = value[1:-1]
                field.array_values = [
                    item.strip().strip("\"'")
                    for item in array_content.split(",")
                    if item.strip()
                ]
            else:
                field.string_value = value
            fields[key] = field
        return cls(fields=fields)
