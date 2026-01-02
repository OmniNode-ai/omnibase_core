"""Configuration for schema validation invariant.

Validates output against a JSON Schema, ensuring structural
compliance and type correctness.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelSchemaInvariantConfig(BaseModel):
    """Configuration for schema validation invariant.

    Validates output against a JSON Schema, ensuring structural
    compliance and type correctness. The schema follows the JSON Schema
    specification (https://json-schema.org/).

    Attributes:
        json_schema: JSON Schema definition to validate against. Must be
            a valid JSON Schema object (e.g., with "type", "properties", etc.).
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    json_schema: dict[str, object] = Field(
        ...,
        description="JSON schema to validate against",
    )


__all__ = ["ModelSchemaInvariantConfig"]
