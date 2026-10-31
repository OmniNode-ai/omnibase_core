# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The network defaults contract binds every URL the touched modules fall back to (OMN-21783)."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from omnibase_core.backends.cache import backend_cache_redis
from omnibase_core.cli import cli_gate
from omnibase_core.doctor.checks import check_linear
from omnibase_core.mixins import mixin_canonical_serialization
from omnibase_core.models.configuration import model_database_secure_config
from omnibase_core.models.configuration.model_database_secure_config import (
    ModelDatabaseSecureConfig,
)
from omnibase_core.models.configuration.model_network_defaults import (
    ModelNetworkDefaults,
)
from omnibase_core.models.core import model_route_spec
from omnibase_core.models.core.model_route_spec import ModelRouteSpec
from omnibase_core.models.docker import model_docker_template_generator
from omnibase_core.models.handlers import model_handler_packaging
from omnibase_core.models.node_metadata import model_node_capability
from omnibase_core.models.node_metadata.model_node_capability import (
    ModelNodeCapability,
)
from omnibase_core.models.services import model_node_service_config
from omnibase_core.validation import validator_occ_merge_eligibility
from omnibase_core.validation.validator_contracts_and_di import ValidatorContractsAndDi

_TOUCHED_MODULES: tuple[ModuleType, ...] = (
    backend_cache_redis,
    cli_gate,
    check_linear,
    mixin_canonical_serialization,
    model_database_secure_config,
    model_route_spec,
    model_docker_template_generator,
    model_handler_packaging,
    model_node_capability,
    model_node_service_config,
    validator_occ_merge_eligibility,
)


@pytest.mark.unit
class TestUrlContractValues:
    def test_redis_sanitizer_fallback_reads_the_contract(self) -> None:
        class _Unparseable:
            """A value urlparse rejects with a TypeError."""

        redacted = backend_cache_redis.sanitize_redis_url(cast("str", _Unparseable()))
        assert redacted == ModelNetworkDefaults.load().redacted_redis_url

    def test_default_gate_config_project_url_comes_from_the_template(self) -> None:
        config = cli_gate._default_config(Path("/x/proj"), "proj", None)
        expected = ModelNetworkDefaults.load().default_project_url_template.format(
            project_name="proj"
        )
        assert config["project_url"] == expected

    def test_an_explicit_project_url_wins(self) -> None:
        config = cli_gate._default_config(Path("/x/proj"), "proj", "u")
        assert config["project_url"] == "u"

    def test_broadcast_route_destination_reads_the_contract(self) -> None:
        route = ModelRouteSpec.create_broadcast_route()
        assert (
            route.final_destination
            == ModelNetworkDefaults.load().broadcast_route_destination
        )

    def test_sqlite_connection_string_reads_the_template(self) -> None:
        config = ModelDatabaseSecureConfig.create_sqlite(database_path="/db/x.sqlite")
        expected = ModelNetworkDefaults.load().sqlite_connection_url_template.format(
            database="/db/x.sqlite"
        )
        assert config.get_connection_string() == expected

    def test_telemetry_capability_example_reads_the_contract(self) -> None:
        capability = ModelNodeCapability.telemetry_enabled()
        assert capability.example_config is not None
        endpoint = capability.example_config["telemetry_endpoint"]
        assert (
            ModelNetworkDefaults.load().example_telemetry_endpoint
            in endpoint.model_dump_json()
        )

    def test_file_scheme_prefix_reads_the_contract(self) -> None:
        prefix = ModelNetworkDefaults.load().file_url_prefix
        assert prefix in model_handler_packaging._ALLOWED_SCHEMES
        valid, message = model_handler_packaging._validate_artifact_reference(prefix)
        assert not valid
        assert message == f"{prefix} URLs must include a path"

    def test_kafka_listener_reads_the_contract(self) -> None:
        text = Path(model_docker_template_generator.__file__).read_text()
        assert "kafka_advertised_listener" in text

    def test_container_health_check_url_uses_the_declared_loopback(self) -> None:
        defaults = ModelNetworkDefaults.load()
        url = defaults.container_health_check_url(8080, "/health")
        assert url == f"http://{defaults.loopback_name}:8080/health"

    def test_every_new_url_field_is_declared(self) -> None:
        defaults = ModelNetworkDefaults.load()
        assert defaults.linear_graphql_url.startswith("https://")
        assert defaults.unknown_entrypoint_uri.startswith("python://")
        assert defaults.yamlfmt_repository_url.startswith("https://")
        assert "{port}" in defaults.container_health_check_url_template


@pytest.mark.unit
class TestCheckerReportsNoUrlLiteral:
    @pytest.mark.parametrize("module", _TOUCHED_MODULES, ids=lambda m: m.__name__)
    def test_module_holds_no_url_literal(self, module: ModuleType) -> None:
        assert module.__file__ is not None
        result = ValidatorContractsAndDi().validate_file(Path(module.__file__))
        assert [
            f"{i.line_number}: {i.message}"
            for i in result.issues
            if i.code == "literal_url"
        ] == []

    def test_checker_still_flags_a_planted_url(self, tmp_path: Path) -> None:
        planted = tmp_path / "src" / "omnibase_core" / "planted_url.py"
        planted.parent.mkdir(parents=True)
        planted.write_text('ENDPOINT = "https://svc.test/path"\n')
        (tmp_path / ".git").mkdir()
        result = ValidatorContractsAndDi().validate_file(planted)
        assert "literal_url" in {i.code for i in result.issues}
