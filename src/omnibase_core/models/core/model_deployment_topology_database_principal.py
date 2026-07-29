# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""LOGIN workload-principal declaration for a deployment database."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_database_privilege import EnumDatabasePrivilege
from omnibase_core.models.core.model_deployment_topology_database_grant import (
    ModelDeploymentTopologyDatabaseGrant,
)

__all__ = ["ModelDeploymentTopologyDatabasePrincipal"]


class ModelDeploymentTopologyDatabasePrincipal(BaseModel):
    """Non-owner application principal with explicit, least-privilege grants."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    login: Literal[True] = Field(
        ...,
        description="Must be true: workload principals are LOGIN roles.",
    )
    bypass_rls: Literal[False] = Field(
        ...,
        description="Must be false: application principals cannot bypass RLS.",
    )
    grants: tuple[ModelDeploymentTopologyDatabaseGrant, ...] = Field(
        ...,
        min_length=1,
        description="Explicit database, schema, and object grants.",
    )

    @model_validator(mode="after")
    def workload_principal_has_no_ddl(
        self,
    ) -> "ModelDeploymentTopologyDatabasePrincipal":
        """Keep runtime workload identities out of database/schema creation paths."""
        prohibited = {
            EnumDatabasePrivilege.CREATE,
            EnumDatabasePrivilege.TEMPORARY,
        }
        granted = {
            privilege
            for grant in self.grants
            for privilege in grant.privileges
            if privilege in prohibited
        }
        if granted:
            names = ", ".join(sorted(privilege.value for privilege in granted))
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError(
                f"Workload principals cannot receive DDL privileges: {names}"
            )
        return self
