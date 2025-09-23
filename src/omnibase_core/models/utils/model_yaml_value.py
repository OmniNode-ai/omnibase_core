"""
YAML-serializable data structures model with discriminated union.

Author: ONEX Framework Team
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from ..common.model_schema_value import ModelSchemaValue


class ModelYamlValue(BaseModel):
    """Discriminated union for YAML-serializable data structures."""

    value_type: Literal["schema_value", "dict", "list"] = Field(
        description="Type discriminator for the YAML value"
    )
    schema_value: ModelSchemaValue | None = Field(None, description="Schema value data")
    dict_value: dict[str, "ModelYamlValue"] | None = Field(
        None, description="Dictionary data"
    )
    list_value: list["ModelYamlValue"] | None = Field(None, description="List data")

    @classmethod
    def from_schema_value(cls, value: ModelSchemaValue) -> "ModelYamlValue":
        """Create from ModelSchemaValue."""
        return cls(
            value_type="schema_value",
            schema_value=value,
            dict_value=None,
            list_value=None,
        )

    @classmethod
    def from_dict_data(cls, value: dict[str, ModelSchemaValue]) -> "ModelYamlValue":
        """Create from dictionary of ModelSchemaValue."""
        dict_value = {k: cls.from_schema_value(v) for k, v in value.items()}
        return cls(
            value_type="dict", schema_value=None, dict_value=dict_value, list_value=None
        )

    @classmethod
    def from_list(cls, value: list[ModelSchemaValue]) -> "ModelYamlValue":
        """Create from list of ModelSchemaValue."""
        list_value = [cls.from_schema_value(v) for v in value]
        return cls(
            value_type="list", schema_value=None, dict_value=None, list_value=list_value
        )

    def to_serializable(self) -> Any:
        """Convert back to serializable data structure."""
        if self.value_type == "schema_value":
            return self.schema_value
        elif self.value_type == "dict":
            return {k: v.to_serializable() for k, v in (self.dict_value or {}).items()}
        elif self.value_type == "list":
            return [v.to_serializable() for v in (self.list_value or [])]
        raise ValueError(f"Invalid value_type: {self.value_type}")


# Export the model
__all__ = ["ModelYamlValue"]
