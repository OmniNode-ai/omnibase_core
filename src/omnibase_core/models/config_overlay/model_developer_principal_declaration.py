# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One developer machine's broker principal, as a deployment declares it."""

from pydantic import BaseModel, ConfigDict, Field


class ModelDeveloperPrincipalDeclaration(BaseModel):
    """The identity of one developer machine's principal.

    The row names who holds the principal and holds no grant: the grants come
    from the document's ``grants_source``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    principal: str = Field(
        ...,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
        description="Broker principal name: lower-case letters, digits and hyphens.",
    )
    login: str = Field(
        ...,
        min_length=1,
        pattern=r"\S",
        description="Identity-provider login of the developer who holds the principal.",
    )
    device: str = Field(
        ...,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
        description="Device the principal is issued to: lower-case letters, digits and hyphens.",
    )


__all__ = ["ModelDeveloperPrincipalDeclaration"]
