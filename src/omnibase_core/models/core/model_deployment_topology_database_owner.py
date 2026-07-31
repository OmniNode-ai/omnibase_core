# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NOLOGIN schema-owner declaration for a deployment database."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDeploymentTopologyDatabaseOwner"]


class ModelDeploymentTopologyDatabaseOwner(BaseModel):
    """Schema-owner role which is structurally prohibited from logging in."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    login: Literal[False] = Field(
        ...,
        description="Must be false: schema owners are NOLOGIN roles.",
    )
