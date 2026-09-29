# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The body of a ``broker.principal_grants`` overlay document."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.config_overlay.model_broker_principal_declaration import (
    ModelBrokerPrincipalDeclaration,
)


class ModelBrokerPrincipalGrantsOverlay(BaseModel):
    """Broker access declared by a deployment."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal["broker_principal_grants.v1"] = (
        Field(  # string-version-ok: schema discriminator, not SemVer
            ..., description="Schema version tag."
        )
    )
    principals: tuple[ModelBrokerPrincipalDeclaration, ...] = Field(
        ..., min_length=1, description="Principals whose access is declared."
    )


__all__ = ["ModelBrokerPrincipalGrantsOverlay"]
