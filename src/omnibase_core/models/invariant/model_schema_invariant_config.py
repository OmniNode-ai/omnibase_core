"""Configuration for schema validation invariant.

Validates output against a JSON Schema, ensuring structural
compliance and type correctness.
"""

from pydantic import BaseModel, Field


class ModelSchemaInvariantConfig(BaseModel):
    """Configuration for schema validation invariant.

    Validates output against a JSON Schema, ensuring structural
    compliance and type correctness.
    """

    json_schema: dict[str, object] = Field(
        ...,
        description="JSON schema to validate against",
    )


__all__ = ["ModelSchemaInvariantConfig"]
