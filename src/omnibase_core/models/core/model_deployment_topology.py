# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Deployment Topology Model

YAML-backed, frozen model describing which services are provisioned locally,
in the cloud, or disabled. Supports presets (minimal / standard / full).

Invariants:
  I1 — YAML stability: ruamel.yaml used; from_yaml/to_yaml roundtrip produces == equality.
  I2 — Mode/local consistency: enforced by ModelDeploymentTopologyService validator.
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_database_schema_domain import EnumDatabaseSchemaDomain
from omnibase_core.enums.enum_deployment_mode import EnumDeploymentMode
from omnibase_core.models.core.model_deployment_topology_database import (
    ModelDeploymentTopologyDatabase,
)
from omnibase_core.models.core.model_deployment_topology_local_config import (
    ModelDeploymentTopologyLocalConfig,
)
from omnibase_core.models.core.model_deployment_topology_service import (
    ModelDeploymentTopologyService,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.contracts.subcontracts.model_db_table_declaration import (
        ModelDbTableDeclaration,
    )

__all__ = ["ModelDeploymentTopology"]

_LOGICAL_DATABASE_REFERENCE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


def _sort_dict_recursively(obj: Any) -> Any:
    """Recursively sort dict keys for stable YAML serialization."""
    if isinstance(obj, dict):
        return {k: _sort_dict_recursively(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_sort_dict_recursively(item) for item in obj]
    return obj


class ModelDeploymentTopology(BaseModel):
    """
    YAML-backed deployment topology configuration.

    Describes which services are provisioned locally (Docker compose),
    in the cloud, or disabled. Global presets select subsets of services
    to activate together.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-version-ok: YAML-deserialization boundary; topology files on disk carry plain strings
    schema_version: str = Field(
        description="Schema version for this topology file. Required; YAML missing it is rejected.",
    )
    services: dict[str, ModelDeploymentTopologyService] = Field(
        default_factory=dict,
        description="Map of service name to its deployment service config.",
    )
    databases: dict[str, ModelDeploymentTopologyDatabase] = Field(
        default_factory=dict,
        description=(
            "Logical application-database resources. Checked-in environment topology "
            "instances populate this map; host-local topology files are projections."
        ),
    )
    presets: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Named presets mapping preset name to list of service names.",
    )
    active_preset: str | None = Field(
        default=None,
        description="Currently active preset name (or None for no active preset).",
    )

    @model_validator(mode="after")
    def validate_database_references(self) -> ModelDeploymentTopology:
        """Ensure nested consumer bindings resolve to their containing database."""
        for database_ref, database in self.databases.items():
            if (
                len(database_ref) > 63
                or _LOGICAL_DATABASE_REFERENCE_PATTERN.fullmatch(database_ref) is None
            ):
                # error-ok: Pydantic validators require ValueError to produce ValidationError.
                raise ValueError(
                    "databases keys must be lowercase logical SQL identifiers, "
                    f"got '{database_ref}'"
                )
            for consumer, binding in database.bindings.items():
                if binding.database_ref not in self.databases:
                    # error-ok: Pydantic validators require ValueError to produce ValidationError.
                    raise ValueError(
                        f"Binding '{consumer}' references unknown database_ref "
                        f"'{binding.database_ref}'"
                    )
                if binding.database_ref != database_ref:
                    # error-ok: Pydantic validators require ValueError to produce ValidationError.
                    raise ValueError(
                        f"Binding '{consumer}' database_ref '{binding.database_ref}' "
                        f"does not match containing database '{database_ref}'"
                    )
        return self

    # -----------------------------------------------------------------
    # Query helpers
    # -----------------------------------------------------------------

    def local_services(self) -> dict[str, ModelDeploymentTopologyService]:
        """Return only services with mode=LOCAL."""
        return {
            name: svc
            for name, svc in self.services.items()
            if svc.mode == EnumDeploymentMode.LOCAL
        }

    def is_service_enabled(self, service_name: str) -> bool:
        """Return True if the named service exists and mode != DISABLED."""
        svc = self.services.get(service_name)
        if svc is None:
            return False
        return svc.mode != EnumDeploymentMode.DISABLED

    def services_for_preset(self, preset_name: str) -> list[str]:
        """Return the list of service names for a named preset."""
        return self.presets.get(preset_name, [])

    def schema_domain(
        self,
        database_ref: str,
        schema: str,
    ) -> EnumDatabaseSchemaDomain:
        """Resolve the authoritative domain for a logical database/schema pair."""
        database = self.databases.get(database_ref)
        if database is None:
            # error-ok: Public lookup helper reports unresolved contract references.
            raise ValueError(f"Unknown database_ref '{database_ref}'")
        schema_config = database.schemas.get(schema)
        if schema_config is None:
            # error-ok: Public lookup helper reports unresolved contract references.
            raise ValueError(
                f"Unknown schema '{schema}' for database_ref '{database_ref}'"
            )
        return schema_config.domain

    def table_domain(
        self,
        declaration: ModelDbTableDeclaration,
    ) -> EnumDatabaseSchemaDomain:
        """Derive a table domain solely from its topology-owned schema location."""
        return self.schema_domain(declaration.database_ref, declaration.schema)

    # -----------------------------------------------------------------
    # Factory methods
    # -----------------------------------------------------------------

    @classmethod
    def default_minimal(cls) -> ModelDeploymentTopology:
        """
        Minimal topology: postgres, redpanda, valkey — all LOCAL.
        """
        services: dict[str, ModelDeploymentTopologyService] = {
            "postgres": ModelDeploymentTopologyService(
                mode=EnumDeploymentMode.LOCAL,
                local=ModelDeploymentTopologyLocalConfig(
                    compose_service="omnibase-infra-postgres",
                    host_port=5436,
                    health_check_path=None,
                ),
            ),
            "redpanda": ModelDeploymentTopologyService(
                mode=EnumDeploymentMode.LOCAL,
                local=ModelDeploymentTopologyLocalConfig(
                    compose_service="omnibase-infra-redpanda",
                    host_port=19092,
                    health_check_path=None,
                ),
            ),
            "valkey": ModelDeploymentTopologyService(
                mode=EnumDeploymentMode.LOCAL,
                local=ModelDeploymentTopologyLocalConfig(
                    compose_service="omnibase-infra-valkey",
                    host_port=16379,
                    health_check_path=None,
                ),
            ),
        }
        presets: dict[str, list[str]] = {
            "minimal": ["postgres", "redpanda", "valkey"],
            "standard": ["postgres", "redpanda", "valkey"],
            "full": ["postgres", "redpanda", "valkey"],
        }
        return cls(
            schema_version="1.0",
            services=services,
            presets=presets,
            active_preset="minimal",
        )

    @classmethod
    def default_standard(cls) -> ModelDeploymentTopology:
        """
        Standard topology: minimal + infisical (secrets profile, health_check_path).
        """
        base = cls.default_minimal()
        new_services = dict(base.services)
        new_services["infisical"] = ModelDeploymentTopologyService(
            mode=EnumDeploymentMode.LOCAL,
            local=ModelDeploymentTopologyLocalConfig(
                compose_service="omnibase-infra-infisical",
                host_port=8880,
                compose_profile="secrets",
                health_check_path="/api/status",
            ),
        )
        new_presets = dict(base.presets)
        new_presets["standard"] = ["postgres", "redpanda", "valkey", "infisical"]
        new_presets["full"] = ["postgres", "redpanda", "valkey", "infisical"]
        return cls(
            schema_version=base.schema_version,
            services=new_services,
            databases=base.databases,
            presets=new_presets,
            active_preset="standard",
        )

    @classmethod
    def default_full(cls) -> ModelDeploymentTopology:
        """
        Full topology: standard + keycloak (LOCAL) + omninode_runtime (DISABLED).
        """
        base = cls.default_standard()
        new_services = dict(base.services)
        new_services["keycloak"] = ModelDeploymentTopologyService(
            mode=EnumDeploymentMode.LOCAL,
            local=ModelDeploymentTopologyLocalConfig(
                compose_service="omnibase-infra-keycloak",
                host_port=8443,
                health_check_path="/health/ready",
            ),
        )
        new_services["omninode_runtime"] = ModelDeploymentTopologyService(
            mode=EnumDeploymentMode.DISABLED,
            local=None,
        )
        new_presets = dict(base.presets)
        new_presets["full"] = [
            "postgres",
            "redpanda",
            "valkey",
            "infisical",
            "keycloak",
        ]
        return cls(
            schema_version=base.schema_version,
            services=new_services,
            databases=base.databases,
            presets=new_presets,
            active_preset="full",
        )

    # -----------------------------------------------------------------
    # YAML serialization (ruamel.yaml — Invariant I1)
    # -----------------------------------------------------------------

    def to_yaml(self, path: Path) -> None:
        """Serialize to YAML using ruamel.yaml. Produces stable sorted output."""
        from ruamel.yaml import YAML

        raw = self.model_dump(mode="json")
        stable = _sort_dict_recursively(raw)

        yaml = YAML(typ="safe")
        yaml.default_flow_style = False
        with open(path, "w", encoding="utf-8") as fh:
            yaml.dump(stable, fh)

    @classmethod
    def from_yaml(cls, path: Path) -> ModelDeploymentTopology:
        """
        Load topology from a YAML file.

        Raises:
            ModelOnexError: if schema_version is missing.
            ValidationError: if any field values are invalid.
        """
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        with open(path, encoding="utf-8") as fh:
            data = yaml.load(fh)

        if not isinstance(data, dict) or "schema_version" not in data:
            raise ModelOnexError(
                f"Deployment topology YAML at '{path}' is missing required field 'schema_version'.",
                error_code=EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER,
            )

        return cls.model_validate(data)

    def _to_yaml_string(self) -> str:
        """Serialize to a YAML string (used for roundtrip equality checks)."""
        from ruamel.yaml import YAML

        raw = self.model_dump(mode="json")
        stable = _sort_dict_recursively(raw)

        yaml = YAML(typ="safe")
        yaml.default_flow_style = False
        buf = io.StringIO()
        yaml.dump(stable, buf)
        return buf.getvalue()

    @classmethod
    def _from_yaml_string(cls, content: str) -> ModelDeploymentTopology:
        """Load topology from a YAML string (used for roundtrip equality checks)."""
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        data = yaml.load(content)

        if not isinstance(data, dict) or "schema_version" not in data:
            raise ModelOnexError(
                "Deployment topology YAML string is missing required field 'schema_version'.",
                error_code=EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER,
            )

        return cls.model_validate(data)
