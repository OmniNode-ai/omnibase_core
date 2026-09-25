# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ModelSecretsSyncIdentity(BaseModel):
    """
    Which secret-sync identity a lane applied.

    Carries references only; no field may hold a secret value.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    machine_identity_ref: Annotated[
        str,
        Field(
            ...,
            min_length=1,
            description="A reference such as 'infisical://identities/lab-sync', never a credential.",
        ),
    ]
    project_slug: Annotated[
        str,
        Field(..., min_length=1, description="The project slug."),
    ]
    environment_slug: Annotated[
        str,
        Field(..., min_length=1, description="The environment slug."),
    ]
    applied_cr_generation: Annotated[
        int,
        Field(
            ...,
            ge=0,
            description="The applied InfisicalSecret custom resource generation.",
        ),
    ]


__all__ = ["ModelSecretsSyncIdentity"]
