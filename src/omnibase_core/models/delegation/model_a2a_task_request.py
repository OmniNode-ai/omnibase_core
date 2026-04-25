# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelA2ATaskRequest: A2A task-send wire DTO."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelA2ATaskRequest(BaseModel):
    """External A2A task request with a typed payload map."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
    )

    skill_ref: str = Field(
        min_length=1,
        validation_alias="skill_id",
        serialization_alias="skill_id",
    )
    input: dict[str, ModelSchemaValue] = Field(default_factory=dict)
    correlation_id: UUID

    @field_validator("input", mode="before")
    @classmethod
    def coerce_input_values(cls, value: object) -> dict[str, ModelSchemaValue]:
        """Convert raw A2A input payload values into typed schema values."""
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("input must be an object")
        return {
            str(key): item
            if isinstance(item, ModelSchemaValue)
            else ModelSchemaValue.from_value(item)
            for key, item in value.items()
        }


__all__ = ["ModelA2ATaskRequest"]
