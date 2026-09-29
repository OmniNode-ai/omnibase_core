# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The body of a ``host.settings`` overlay document."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.config_overlay.model_host_declaration import (
    ModelHostDeclaration,
)


class ModelHostSettingsOverlay(BaseModel):
    """Host configuration declared by a deployment."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal["host_settings.v1"] = (
        Field(  # string-version-ok: schema discriminator, not SemVer
            ..., description="Schema version tag."
        )
    )
    hosts: tuple[ModelHostDeclaration, ...] = Field(
        ..., min_length=1, description="Hosts whose configuration is declared."
    )


__all__ = ["ModelHostSettingsOverlay"]
