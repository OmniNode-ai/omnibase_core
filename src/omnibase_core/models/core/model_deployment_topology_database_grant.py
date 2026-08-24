# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Explicit workload-principal grant in a deployment database topology."""

import re
import warnings

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_database_grant_object_type import (
    EnumDatabaseGrantObjectType,
)
from omnibase_core.enums.enum_database_privilege import EnumDatabasePrivilege

__all__ = ["ModelDeploymentTopologyDatabaseGrant"]

_SQL_IDENTIFIER_PATTERN = r"^[a-z_][a-z0-9_]*$"

# OMN-16415: see model_deployment_topology_database_migration_ledger.py for the
# full rationale -- `schema` is the correct SQL-domain field name; the warning
# is suppressed narrowly by message pattern, not renamed.
warnings.filterwarnings(
    "ignore",
    message=r'Field name "schema" in ".*" shadows an attribute in parent "BaseModel"',
    category=UserWarning,
)
_SQL_IDENTIFIER = re.compile(_SQL_IDENTIFIER_PATTERN)

_ALLOWED_PRIVILEGES: dict[
    EnumDatabaseGrantObjectType, frozenset[EnumDatabasePrivilege]
] = {
    EnumDatabaseGrantObjectType.DATABASE: frozenset(
        {
            EnumDatabasePrivilege.CONNECT,
            EnumDatabasePrivilege.CREATE,
            EnumDatabasePrivilege.TEMPORARY,
        }
    ),
    EnumDatabaseGrantObjectType.SCHEMA: frozenset(
        {EnumDatabasePrivilege.USAGE, EnumDatabasePrivilege.CREATE}
    ),
    EnumDatabaseGrantObjectType.TABLE: frozenset(
        {
            EnumDatabasePrivilege.SELECT,
            EnumDatabasePrivilege.INSERT,
            EnumDatabasePrivilege.UPDATE,
            EnumDatabasePrivilege.DELETE,
            EnumDatabasePrivilege.TRUNCATE,
            EnumDatabasePrivilege.REFERENCES,
            EnumDatabasePrivilege.TRIGGER,
        }
    ),
    EnumDatabaseGrantObjectType.SEQUENCE: frozenset(
        {
            EnumDatabasePrivilege.USAGE,
            EnumDatabasePrivilege.SELECT,
            EnumDatabasePrivilege.UPDATE,
        }
    ),
    EnumDatabaseGrantObjectType.FUNCTION: frozenset({EnumDatabasePrivilege.EXECUTE}),
    EnumDatabaseGrantObjectType.TYPE: frozenset({EnumDatabasePrivilege.USAGE}),
}


class ModelDeploymentTopologyDatabaseGrant(BaseModel):
    """One explicit grant without wildcard or implicit ``ALL`` semantics."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    object_type: EnumDatabaseGrantObjectType
    # Pydantic v2 keeps BaseModel.schema as a deprecated compatibility callable.
    schema: str | None = Field(  # type: ignore[assignment]
        default=None,
        min_length=1,
        max_length=63,
        pattern=_SQL_IDENTIFIER_PATTERN,
        description="Schema reference for every scope except DATABASE.",
    )
    objects: tuple[str, ...] = Field(
        default=(),
        description="Explicit object identifiers for relation-level scopes.",
    )
    privileges: tuple[EnumDatabasePrivilege, ...] = Field(
        ...,
        min_length=1,
        description="Non-empty, object-compatible privilege set.",
    )

    @model_validator(mode="after")
    def validate_scope(self) -> "ModelDeploymentTopologyDatabaseGrant":
        """Reject ambiguous targets, wildcards, and incompatible privileges."""
        invalid_privileges = (
            set(self.privileges) - _ALLOWED_PRIVILEGES[self.object_type]
        )
        if invalid_privileges:
            names = ", ".join(
                sorted(privilege.value for privilege in invalid_privileges)
            )
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError(
                f"Privileges {names} are invalid for {self.object_type.value} objects"
            )
        if len(set(self.privileges)) != len(self.privileges):
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError("Grant privileges must be unique")

        relation_scopes = {
            EnumDatabaseGrantObjectType.TABLE,
            EnumDatabaseGrantObjectType.SEQUENCE,
            EnumDatabaseGrantObjectType.FUNCTION,
            EnumDatabaseGrantObjectType.TYPE,
        }
        if self.object_type is EnumDatabaseGrantObjectType.DATABASE:
            if self.schema is not None or self.objects:
                # error-ok: Pydantic validators require ValueError to produce ValidationError.
                raise ValueError("DATABASE grants cannot declare schema or objects")
            return self

        if self.schema is None:
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError(f"{self.object_type.value} grants require a schema")

        if self.object_type is EnumDatabaseGrantObjectType.SCHEMA:
            if self.objects:
                # error-ok: Pydantic validators require ValueError to produce ValidationError.
                raise ValueError("SCHEMA grants cannot declare objects")
            return self

        if self.object_type in relation_scopes and not self.objects:
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError(
                f"{self.object_type.value} grants require explicit object names"
            )
        invalid_objects = [
            name
            for name in self.objects
            if len(name) > 63 or _SQL_IDENTIFIER.fullmatch(name) is None
        ]
        if invalid_objects:
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError(
                f"Grant objects must be SQL identifiers, got {invalid_objects!r}"
            )
        if len(set(self.objects)) != len(self.objects):
            # error-ok: Pydantic validators require ValueError to produce ValidationError.
            raise ValueError("Grant objects must be unique")
        return self
