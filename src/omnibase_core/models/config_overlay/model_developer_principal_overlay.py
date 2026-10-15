# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The body of a ``developer.principal`` overlay document."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from omnibase_core.models.config_overlay.model_developer_principal_declaration import (
    ModelDeveloperPrincipalDeclaration,
)


class ModelDeveloperPrincipalOverlay(BaseModel):
    """The developer machines a deployment gives a broker principal.

    The document has no field for a grant. The grants of every principal in it
    are derived from the declaration ``grants_source`` names, so a grant cannot
    be typed into a row and left to drift from that declaration.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal["developer_principal.v1"] = Field(
        ..., description="Schema version tag."
    )
    grants_source: str = Field(
        ...,
        min_length=1,
        pattern=r"\S",
        description="The declaration every principal's grants are derived from.",
    )
    principals: tuple[ModelDeveloperPrincipalDeclaration, ...] = Field(
        ..., min_length=1, description="The developer machines holding a principal."
    )

    @model_validator(mode="after")
    def _identities_are_unique(self) -> Self:
        """Declare each principal name and each login-device pair once."""
        names = [row.principal for row in self.principals]
        if len(set(names)) != len(names):
            raise PydanticCustomError(
                "duplicate_principal", "principal names must be unique"
            )
        holders = [(row.login, row.device) for row in self.principals]
        if len(set(holders)) != len(holders):
            raise PydanticCustomError(
                "duplicate_holder", "each login and device pair may hold one principal"
            )
        return self


__all__ = ["ModelDeveloperPrincipalOverlay"]
