# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The addresses and ports of the connection models are a packaged contract, not literals in code (OMN-21778)."""

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.handlers import handler_ledger_write_guard
from omnibase_core.models.configuration import (
    model_database_connection_config,
    model_database_secure_config,
    model_rest_api_connection_config,
)
from omnibase_core.models.configuration.model_database_secure_config import (
    ModelDatabaseSecureConfig,
)
from omnibase_core.models.connections import (
    model_connection_endpoint,
    model_connection_info,
)
from omnibase_core.models.connections.model_connection_endpoint import (
    ModelConnectionEndpoint,
)
from omnibase_core.models.connections.model_connection_info import ModelConnectionInfo
from omnibase_core.models.node_metadata import model_node_connection_settings
from omnibase_core.models.node_metadata.model_node_connection_settings import (
    ModelNodeConnectionSettings,
)
from omnibase_core.models.runtime import model_network_defaults
from omnibase_core.models.runtime.model_network_defaults import (
    ModelNetworkDefaults,
    packaged_network_defaults,
)
from omnibase_core.models.services import (
    model_network_config,
    model_node_service_config,
)
from omnibase_core.models.services.model_network_config import ModelNetworkConfig
from omnibase_core.nodes.node_contract_evidence_check_effect import (
    handler_contract_compliance_check,
)
from omnibase_core.validation.validator_contracts_and_di import (
    ValidatorContractsAndDi,
)

_CONTRACT = Path(model_network_defaults.__file__).with_name("network_defaults.yaml")

_SLICE_MODULES = (
    handler_ledger_write_guard,
    model_database_connection_config,
    model_database_secure_config,
    model_rest_api_connection_config,
    model_connection_endpoint,
    model_connection_info,
    model_node_connection_settings,
    model_network_config,
    model_node_service_config,
    handler_contract_compliance_check,
)


def _mapping() -> dict[str, Any]:
    loaded = yaml.safe_load(_CONTRACT.read_text())
    assert isinstance(loaded, dict)
    return loaded


@pytest.mark.unit
class TestPackagedNetworkDefaults:
    def test_values_equal_the_literals_the_modules_carried(self) -> None:
        defaults = packaged_network_defaults()
        assert defaults.local_hosts == {"localhost", "127.0.0.1"}
        assert defaults.loopback_hosts == {"localhost", "127.0.0.1", "::1"}
        assert defaults.service_bind_host == "0.0.0.0"
        assert defaults.http_port == 80
        assert defaults.grpc_port == 50051
        assert defaults.postgres_port == 5432
        assert defaults.mysql_port == 3306
        assert defaults.sqlite_placeholder_port == 0
        assert defaults.node_registry_port == 8081
        assert defaults.node_registry_prometheus_port == 9091

    def test_a_missing_key_fails_the_load(self) -> None:
        mapping = _mapping()
        del mapping["http_port"]
        with pytest.raises(ValidationError):
            ModelNetworkDefaults(**mapping)

    def test_an_unknown_key_fails_the_load(self) -> None:
        with pytest.raises(ValidationError):
            ModelNetworkDefaults(**_mapping(), surprise=1)


@pytest.mark.unit
class TestCallSitesReadTheContract:
    def test_overlaid_defaults_reach_the_factories(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        overlay = ModelNetworkDefaults(
            **{
                **_mapping(),
                "http_port": 8000,
                "grpc_port": 50052,
                "postgres_port": 15432,
                "mysql_port": 13306,
            }
        )
        for module in _SLICE_MODULES:
            if hasattr(module, "packaged_network_defaults"):
                monkeypatch.setattr(
                    module, "packaged_network_defaults", lambda: overlay
                )
        assert ModelConnectionEndpoint.create_http("h").port == 8000
        assert ModelConnectionEndpoint.create_websocket("h").port == 8000
        assert ModelConnectionInfo.create_http("h").endpoint.port == 8000
        assert ModelNodeConnectionSettings.create_http("h").port == 8000
        assert ModelNodeConnectionSettings.create_grpc("h").port == 50052
        assert (
            ModelDatabaseSecureConfig.create_postgresql(
                "h",
                password="x" * 16,
            ).port
            == 15432
        )
        assert (
            ModelDatabaseSecureConfig.create_mysql(
                "h",
                password="x" * 16,
            ).port
            == 13306
        )

    def test_explicit_ports_win_over_the_contract(self) -> None:
        assert ModelConnectionEndpoint.create_http("h", 9000).port == 9000
        assert ModelNodeConnectionSettings.create_grpc("h", 1234).port == 1234

    def test_default_ports_are_unchanged(self) -> None:
        assert ModelConnectionEndpoint.create_http("h").port == 80
        assert ModelConnectionInfo.create_websocket("h").endpoint.port == 80
        assert ModelNodeConnectionSettings.create_grpc("h").port == 50051
        assert ModelNetworkConfig().host == "0.0.0.0"

    def test_loopback_endpoint_is_local(self) -> None:
        endpoint = ModelConnectionEndpoint.create_http("localhost")
        assert endpoint.is_local_connection()
        assert not ModelConnectionEndpoint.create_http(
            "example.org"
        ).is_local_connection()

    @pytest.mark.parametrize(
        "module", _SLICE_MODULES, ids=lambda m: m.__name__.rsplit(".", 1)[-1]
    )
    def test_module_draws_no_literal_ip_or_port_finding(self, module: Any) -> None:
        result = ValidatorContractsAndDi().validate_file(Path(module.__file__))
        assert [
            i.message for i in result.issues if i.code in {"literal_ip", "literal_port"}
        ] == []
