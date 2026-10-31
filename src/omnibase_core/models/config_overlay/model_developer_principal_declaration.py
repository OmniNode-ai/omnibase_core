# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One developer machine's broker principal, as a deployment declares it."""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from omnibase_core.enums.enum_developer_principal_role import (
    EnumDeveloperPrincipalRole,
)


class ModelDeveloperPrincipalDeclaration(BaseModel):
    """The identity of one developer machine's principal.

    The row names who holds the principal and holds no grant: the grants come
    from the document's ``grants_source``. A machine row may bind grant roles by
    name; each role's grant set is declared by ``grants_source`` too, so a
    binding selects a declared set and never types a grant.
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
    role: EnumDeveloperPrincipalRole = Field(
        default=EnumDeveloperPrincipalRole.DEVELOPER,
        description=(
            "Whether the principal is a person's development machine or a machine the "
            "deployment runs itself. Never a grant."
        ),
    )
    grant_roles: tuple[
        Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]*$")], ...
    ] = Field(
        default=(),
        description=(
            "Names of the grant roles this machine holds beyond the profile every "
            "machine receives (OMN-21622), each one a grant set ``grants_source`` "
            "declares. Only a machine row binds a role, and each role once."
        ),
    )

    @model_validator(mode="after")
    def _grant_roles_bind_a_machine_once(self) -> Self:
        if self.grant_roles and self.role is not EnumDeveloperPrincipalRole.MACHINE:
            raise ValueError("grant_roles binds a machine row only")
        if len(set(self.grant_roles)) != len(self.grant_roles):
            raise ValueError("grant_roles names each role once")
        return self


__all__ = ["ModelDeveloperPrincipalDeclaration"]
