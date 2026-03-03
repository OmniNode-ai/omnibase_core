# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelDeploymentTopology, ModelDeploymentTopologyService,
ModelDeploymentTopologyLocalConfig, and EnumDeploymentMode.

13 tests covering: factory methods, query helpers, YAML roundtrip,
validation errors, frozen/extra-forbid invariants.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_deployment_mode import EnumDeploymentMode
from omnibase_core.models.core.model_deployment_topology import ModelDeploymentTopology
from omnibase_core.models.core.model_deployment_topology_local_config import (
    ModelDeploymentTopologyLocalConfig,
)
from omnibase_core.models.core.model_deployment_topology_service import (
    ModelDeploymentTopologyService,
)


@pytest.mark.unit
class TestModelDeploymentTopology:
    def test_default_minimal_creates_exactly_three_services(self) -> None:
        topology = ModelDeploymentTopology.default_minimal()
        assert len(topology.services) == 3

    def test_default_minimal_all_services_are_local_mode(self) -> None:
        topology = ModelDeploymentTopology.default_minimal()
        for name, svc in topology.services.items():
            assert svc.mode == EnumDeploymentMode.LOCAL, (
                f"Service '{name}' expected LOCAL mode"
            )

    def test_local_services_returns_only_local_mode_services(self) -> None:
        topology = ModelDeploymentTopology.default_full()
        local = topology.local_services()
        for name, svc in local.items():
            assert svc.mode == EnumDeploymentMode.LOCAL, (
                f"local_services() returned non-LOCAL service: '{name}'"
            )
        # omninode_runtime is DISABLED — must not appear in local_services
        assert "omninode_runtime" not in local

    def test_is_service_enabled_returns_false_for_absent_service(self) -> None:
        topology = ModelDeploymentTopology.default_minimal()
        assert topology.is_service_enabled("nonexistent_service") is False

    def test_services_for_preset_uses_global_preset_map(self) -> None:
        topology = ModelDeploymentTopology.default_minimal()
        names = topology.services_for_preset("minimal")
        assert set(names) == {"postgres", "redpanda", "valkey"}

    def test_to_yaml_and_from_yaml_roundtrip_produces_equal_model(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        original = ModelDeploymentTopology.default_standard()
        yaml_file = tmp_path / "topology.yaml"  # type: ignore[operator]
        original.to_yaml(yaml_file)
        loaded = ModelDeploymentTopology.from_yaml(yaml_file)
        assert original == loaded

    def test_from_yaml_raises_on_unknown_mode_value(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        bad_yaml = tmp_path / "bad.yaml"  # type: ignore[operator]
        bad_yaml.write_text(  # type: ignore[union-attr]
            "schema_version: '1.0'\n"
            "services:\n"
            "  postgres:\n"
            "    mode: INVALID_MODE\n"
            "    local: null\n"
            "presets: {}\n"
            "active_preset: null\n"
        )
        with pytest.raises((ValidationError, ValueError)):
            ModelDeploymentTopology.from_yaml(bad_yaml)  # type: ignore[arg-type]

    def test_from_yaml_raises_when_schema_version_missing(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        no_version_yaml = tmp_path / "no_version.yaml"  # type: ignore[operator]
        no_version_yaml.write_text(  # type: ignore[union-attr]
            "services: {}\npresets: {}\nactive_preset: null\n"
        )
        with pytest.raises(ValueError, match="schema_version"):
            ModelDeploymentTopology.from_yaml(no_version_yaml)  # type: ignore[arg-type]

    def test_extra_fields_forbidden_on_topology(self) -> None:
        with pytest.raises(ValidationError):
            ModelDeploymentTopology(
                schema_version="1.0",
                services={},
                presets={},
                active_preset=None,
                unknown_extra_field="should_fail",  # type: ignore[call-arg]
            )

    def test_frozen_topology_raises_on_mutation_attempt(self) -> None:
        topology = ModelDeploymentTopology.default_minimal()
        with pytest.raises((ValidationError, TypeError)):
            topology.active_preset = "full"  # type: ignore[misc]

    def test_local_mode_without_local_config_raises(self) -> None:
        with pytest.raises(ValidationError, match="local"):
            ModelDeploymentTopologyService(
                mode=EnumDeploymentMode.LOCAL,
                local=None,
            )

    def test_cloud_mode_with_local_config_raises(self) -> None:
        local_cfg = ModelDeploymentTopologyLocalConfig(
            compose_service="some-svc",
            host_port=8080,
        )
        with pytest.raises(ValidationError, match="local"):
            ModelDeploymentTopologyService(
                mode=EnumDeploymentMode.CLOUD,
                local=local_cfg,
            )

    def test_disabled_mode_with_local_config_raises(self) -> None:
        local_cfg = ModelDeploymentTopologyLocalConfig(
            compose_service="some-svc",
            host_port=8080,
        )
        with pytest.raises(ValidationError, match="local"):
            ModelDeploymentTopologyService(
                mode=EnumDeploymentMode.DISABLED,
                local=local_cfg,
            )

    def test_cloud_service_stored_correctly_without_local(self) -> None:
        svc = ModelDeploymentTopologyService(
            mode=EnumDeploymentMode.CLOUD,
            local=None,
        )
        assert svc.mode == EnumDeploymentMode.CLOUD
        assert svc.local is None
