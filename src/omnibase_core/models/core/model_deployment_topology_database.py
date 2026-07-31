# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed application-database resource for deployment topology."""

import re
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.core.model_deployment_topology_database_binding import (
    ModelDeploymentTopologyDatabaseBinding,
)
from omnibase_core.models.core.model_deployment_topology_database_migration_ledger import (
    ModelDeploymentTopologyDatabaseMigrationLedger,
)
from omnibase_core.models.core.model_deployment_topology_database_owner import (
    ModelDeploymentTopologyDatabaseOwner,
)
from omnibase_core.models.core.model_deployment_topology_database_principal import (
    ModelDeploymentTopologyDatabasePrincipal,
)
from omnibase_core.models.core.model_deployment_topology_database_schema import (
    ModelDeploymentTopologyDatabaseSchema,
)

__all__ = ["ModelDeploymentTopologyDatabase"]

_SQL_IDENTIFIER_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
_MIGRATION_STREAM_PATTERN = r"^[A-Za-z][A-Za-z0-9_.:/-]*$"


def _validate_mapping_keys(label: str, values: Mapping[str, object]) -> None:
    invalid = [
        key
        for key in values
        if len(key) > 63 or _SQL_IDENTIFIER_PATTERN.fullmatch(key) is None
    ]
    if invalid:
        # error-ok: Called only from a Pydantic validator to produce ValidationError.
        raise ValueError(f"{label} keys must be SQL identifiers, got {invalid!r}")


class ModelDeploymentTopologyDatabase(BaseModel):
    """Logical database, identities, grants, bindings, and selected ledger."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    physical_name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z_][a-z0-9_]*$",
    )
    schemas: dict[str, ModelDeploymentTopologyDatabaseSchema] = Field(
        ...,
        min_length=1,
    )
    owners: dict[str, ModelDeploymentTopologyDatabaseOwner] = Field(
        ...,
        min_length=1,
    )
    principals: dict[str, ModelDeploymentTopologyDatabasePrincipal] = Field(
        ...,
        min_length=1,
    )
    bindings: dict[str, ModelDeploymentTopologyDatabaseBinding] = Field(
        ...,
        min_length=1,
    )
    migration_stream: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=_MIGRATION_STREAM_PATTERN,
    )
    checksum_ledgers: dict[str, ModelDeploymentTopologyDatabaseMigrationLedger] = Field(
        ..., min_length=1
    )
    checksum_ledger: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z_][a-z0-9_]*$",
        description="Selected checksum-capable ledger reference.",
    )

    @model_validator(mode="after")
    def validate_references(self) -> "ModelDeploymentTopologyDatabase":
        """Resolve every nested owner, principal, schema, and ledger reference."""
        for label, values in (
            ("schemas", self.schemas),
            ("owners", self.owners),
            ("principals", self.principals),
            ("bindings", self.bindings),
            ("checksum_ledgers", self.checksum_ledgers),
        ):
            _validate_mapping_keys(label, values)

        for schema_ref, schema in self.schemas.items():
            if schema.owner not in self.owners:
                # error-ok: Pydantic validators require ValueError to produce ValidationError.
                raise ValueError(
                    f"Schema '{schema_ref}' references unknown owner '{schema.owner}'"
                )

        conflicting_roles = sorted(self.owners.keys() & self.principals.keys())
        if conflicting_roles:
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError(
                "Database roles cannot be both NOLOGIN owners and LOGIN principals: "
                f"{conflicting_roles!r}"
            )

        for principal_ref, principal in self.principals.items():
            for grant in principal.grants:
                if grant.schema is not None and grant.schema not in self.schemas:
                    # error-ok: Pydantic validators require ValueError to produce ValidationError.
                    raise ValueError(
                        f"Principal '{principal_ref}' grant references unknown schema "
                        f"'{grant.schema}'"
                    )

        for consumer, binding in self.bindings.items():
            if binding.principal not in self.principals:
                # error-ok: Pydantic validators require ValueError to produce ValidationError.
                raise ValueError(
                    f"Binding '{consumer}' references unknown principal "
                    f"'{binding.principal}'"
                )

        if self.checksum_ledger not in self.checksum_ledgers:
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError(
                f"checksum_ledger references unknown ledger '{self.checksum_ledger}'"
            )
        for ledger_ref, ledger in self.checksum_ledgers.items():
            if ledger.schema not in self.schemas:
                # error-ok: Pydantic validators require ValueError to produce ValidationError.
                raise ValueError(
                    f"Checksum ledger '{ledger_ref}' references unknown schema "
                    f"'{ledger.schema}'"
                )
        return self
