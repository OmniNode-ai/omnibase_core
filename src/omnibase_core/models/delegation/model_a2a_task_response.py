# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelA2ATaskResponse: A2A task response wire DTO."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelA2ATaskResponse(BaseModel):
    """Remote peer task response with raw status retained for handler mapping."""

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    remote_task_handle: str = Field(min_length=1)
    status: str = Field(min_length=1)
    artifacts: list[dict[str, ModelSchemaValue]] = Field(default_factory=list)
    error: str | None = None

    @field_validator("artifacts", mode="before")
    @classmethod
    def coerce_artifacts(
        cls,
        value: object,
    ) -> list[dict[str, ModelSchemaValue]]:
        """Convert raw A2A artifacts into typed schema-value maps."""
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("artifacts must be a list")

        artifacts: list[dict[str, ModelSchemaValue]] = []
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("each artifact must be an object")
            artifacts.append(
                {
                    str(key): artifact_value
                    if isinstance(artifact_value, ModelSchemaValue)
                    else ModelSchemaValue.from_value(artifact_value)
                    for key, artifact_value in item.items()
                },
            )
        return artifacts


__all__ = ["ModelA2ATaskResponse"]
