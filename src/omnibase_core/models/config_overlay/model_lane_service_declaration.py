# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A service declared by a lane's deployment."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_service_restart_policy import EnumServiceRestartPolicy


class ModelLaneServiceDeclaration(BaseModel):
    """A service name and its required restart policy."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    service_name: str = Field(
        ..., min_length=1, pattern=r"\S", description="Declared service name."
    )
    restart_policy: EnumServiceRestartPolicy = Field(
        ..., description="When the service should restart."
    )


__all__ = ["ModelLaneServiceDeclaration"]
