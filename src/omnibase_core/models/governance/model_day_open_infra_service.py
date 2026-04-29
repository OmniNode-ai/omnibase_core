# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayOpenInfraService — infrastructure service health entry from Phase 1."""

from pydantic import BaseModel, ConfigDict, Field

_MAX_STRING_LENGTH = 10000


class ModelDayOpenInfraService(BaseModel):
    """Infrastructure service health entry from Phase 1."""

    model_config = ConfigDict(frozen=True)

    service: str = Field(..., description="Service name", max_length=_MAX_STRING_LENGTH)
    running: bool = Field(..., description="Whether the Docker container is running")
    port_responding: bool = Field(
        ..., description="Whether the service port is accepting connections"
    )
    error: str | None = Field(
        default=None,
        description="Error message if health check failed",
        max_length=_MAX_STRING_LENGTH,
    )
