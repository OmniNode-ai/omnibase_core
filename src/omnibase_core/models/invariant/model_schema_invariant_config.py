"""Configuration for schema validation invariant.

Validates output against a JSON Schema, ensuring structural
compliance and type correctness.

Thread Safety:
    ModelSchemaInvariantConfig is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelSchemaInvariantConfig(BaseModel):
    """Configuration for schema validation invariant.

    Validates output against a JSON Schema, ensuring structural
    compliance and type correctness. The schema follows the JSON Schema
    specification (https://json-schema.org/).

    Attributes:
        json_schema: JSON Schema definition to validate against. Must be
            a valid JSON Schema object (e.g., with "type", "properties", etc.).

    Raises:
        ValueError: If json_schema is empty (no validation rules defined).

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access. No synchronization is needed
        when sharing instances across threads.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    json_schema: dict[str, object] = Field(
        ...,
        description="JSON schema to validate against",
    )

    @model_validator(mode="after")
    def validate_schema_not_empty(self) -> Self:
        """Validate that json_schema contains at least one validation rule.

        An empty schema provides no validation value and likely indicates
        a configuration error.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If json_schema is empty.
        """
        if not self.json_schema:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                "json_schema cannot be empty. "
                "A valid JSON Schema must contain at least one validation rule "
                "(e.g., 'type', 'properties', 'required', etc.). "
                "See https://json-schema.org/ for schema specification."
            )
        return self


__all__ = ["ModelSchemaInvariantConfig"]
