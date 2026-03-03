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
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_deployment_mode import EnumDeploymentMode
from omnibase_core.models.core.model_deployment_topology_local_config import (
    ModelDeploymentTopologyLocalConfig,
)
from omnibase_core.models.core.model_deployment_topology_service import (
    ModelDeploymentTopologyService,
)

__all__ = ["ModelDeploymentTopology"]


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

    model_config = {"frozen": True, "extra": "forbid"}

    schema_version: str = Field(
        description="Schema version for this topology file. Required; YAML missing it is rejected.",
    )
    services: dict[str, ModelDeploymentTopologyService] = Field(
        default_factory=dict,
        description="Map of service name to its deployment service config.",
    )
    presets: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Named presets mapping preset name to list of service names.",
    )
    active_preset: str | None = Field(
        default=None,
        description="Currently active preset name (or None for no active preset).",
    )

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
            ValueError: if schema_version is missing.
            ValidationError: if any field values are invalid.
        """
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        with open(path, encoding="utf-8") as fh:
            data: dict[str, Any] = yaml.load(fh)

        if not isinstance(data, dict) or "schema_version" not in data:
            raise ValueError(
                f"Deployment topology YAML at '{path}' is missing required field 'schema_version'."
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
        data: dict[str, Any] = yaml.load(content)

        if not isinstance(data, dict) or "schema_version" not in data:
            raise ValueError(
                "Deployment topology YAML string is missing required field 'schema_version'."
            )

        return cls.model_validate(data)
