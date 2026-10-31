# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The network defaults contract binds every host, address and port the model layer falls back to (OMN-21681)."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from omnibase_core.handlers import handler_ledger_write_guard
from omnibase_core.models.cli.model_cli_user_config_kafka import ModelCliUserConfigKafka
from omnibase_core.models.configuration import (
    model_database_connection_config,
    model_database_secure_config,
    model_network_defaults,
    model_rest_api_connection_config,
)
from omnibase_core.models.configuration.model_database_secure_config import (
    ModelDatabaseSecureConfig,
)
from omnibase_core.models.configuration.model_network_defaults import (
    ModelNetworkDefaults,
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
from omnibase_core.models.operations import model_change_proposal
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.services import (
    model_network_config,
    model_node_service_config,
)
from omnibase_core.models.services.model_network_config import ModelNetworkConfig
from omnibase_core.models.services.model_node_service_config import (
    ModelNodeServiceConfig,
)
from omnibase_core.nodes.node_contract_evidence_check_effect import (
    handler_contract_compliance_check,
)
from omnibase_core.nodes.node_dependency_pin_bump_effect import (
    handler_dependency_pin_bump,
)
from omnibase_core.validation.validator_contracts_and_di import ValidatorContractsAndDi

_CONTRACT = Path(model_network_defaults.__file__).parent / "network_defaults.yaml"

_TOUCHED_MODULES: tuple[ModuleType, ...] = (
    handler_ledger_write_guard,
    model_database_connection_config,
    model_database_secure_config,
    model_rest_api_connection_config,
    model_connection_endpoint,
    model_connection_info,
    model_node_connection_settings,
    model_change_proposal,
    model_network_config,
    model_node_service_config,
    handler_contract_compliance_check,
    handler_dependency_pin_bump,
)

_NETWORK_RULES = {"literal_host", "literal_ip", "literal_port"}


@pytest.mark.unit
class TestNetworkDefaultsContract:
    def test_loaded_values_equal_the_packaged_contract(self) -> None:
        declared = YAML(typ="safe").load(_CONTRACT.read_text(encoding="utf-8"))
        assert ModelNetworkDefaults.load().model_dump() == declared

    def test_a_contract_with_a_missing_key_fails_to_load(self) -> None:
        declared = YAML(typ="safe").load(_CONTRACT.read_text(encoding="utf-8"))
        del declared["http_port"]
        with pytest.raises(ValidationError):
            ModelNetworkDefaults.model_validate(declared)

    def test_host_sets_are_built_from_the_declared_names(self) -> None:
        defaults = ModelNetworkDefaults.load()
        assert defaults.local_hosts == {defaults.loopback_name, defaults.loopback_ipv4}
        assert defaults.loopback_hosts == defaults.local_hosts | {
            defaults.loopback_ipv6
        }
        assert defaults.loopback_hosts_with_alias == defaults.loopback_hosts | {
            defaults.loopback_ipv6_alias
        }


@pytest.mark.unit
class TestConsumersReadTheContract:
    def test_database_factories_default_their_port_from_the_contract(self) -> None:
        defaults = ModelNetworkDefaults.load()
        login_value = "x" * 16
        assert (
            ModelDatabaseSecureConfig.create_postgresql(
                "db.example.com", password=login_value
            ).port
            == defaults.postgresql_port
        )
        assert (
            ModelDatabaseSecureConfig.create_mysql(
                "db.example.com", password=login_value
            ).port
            == defaults.mysql_port
        )
        assert (
            ModelDatabaseSecureConfig.create_sqlite().port
            == defaults.sqlite_placeholder_port
        )

    def test_an_explicit_port_still_wins(self) -> None:
        endpoint = ModelConnectionEndpoint.create_http("svc.example.com", port=9000)
        assert endpoint.port == 9000

    def test_endpoint_and_info_default_their_port_from_the_contract(self) -> None:
        defaults = ModelNetworkDefaults.load()
        assert (
            ModelConnectionEndpoint.create_http("svc.example.com").port
            == defaults.http_port
        )
        assert (
            ModelConnectionEndpoint.create_websocket("svc.example.com").port
            == defaults.http_port
        )
        assert (
            ModelConnectionInfo.create_http("svc.example.com").endpoint.port
            == defaults.http_port
        )
        assert (
            ModelConnectionInfo.create_websocket("svc.example.com").endpoint.port
            == defaults.http_port
        )

    def test_node_connection_settings_default_their_port_from_the_contract(
        self,
    ) -> None:
        defaults = ModelNetworkDefaults.load()
        assert (
            ModelNodeConnectionSettings.create_http("svc.example.com").port
            == defaults.http_port
        )
        assert (
            ModelNodeConnectionSettings.create_grpc("svc.example.com").port
            == defaults.grpc_port
        )

    def test_loopback_endpoint_is_local(self) -> None:
        defaults = ModelNetworkDefaults.load()
        for host in defaults.local_hosts:
            assert ModelConnectionEndpoint.create_http(host).is_local_connection()
        assert ModelConnectionEndpoint.model_construct(
            host=defaults.loopback_ipv6
        ).is_local_connection()
        assert not ModelConnectionEndpoint.create_http(
            "svc.example.com"
        ).is_local_connection()

    def test_service_config_binds_the_declared_address_and_ports(self) -> None:
        defaults = ModelNetworkDefaults.load()
        assert ModelNetworkConfig().host == defaults.service_bind_address
        registry = ModelNodeServiceConfig.for_node_registry(
            node_version=ModelSemVer(major=1, minor=0, patch=0)
        )
        assert registry.network.port == defaults.node_registry_service_port
        assert (
            registry.monitoring.prometheus_port
            == defaults.node_registry_prometheus_port
        )

    def test_user_kafka_config_defaults_from_the_contract(self) -> None:
        assert (
            ModelCliUserConfigKafka().bootstrap_servers
            == ModelNetworkDefaults.load().kafka_bootstrap_servers
        )

    def test_ledger_guard_treats_the_declared_loopback_as_local(self) -> None:
        defaults = ModelNetworkDefaults.load()
        for host in defaults.loopback_hosts:
            assert not handler_ledger_write_guard.dsn_is_canonical(
                f"postgresql://u@{host}/ledger"
            )
        assert handler_ledger_write_guard.dsn_is_canonical(
            "postgresql://u@db.example.com/ledger"
        )

    def test_compliance_check_treats_the_declared_alias_as_loopback(self) -> None:
        defaults = ModelNetworkDefaults.load()
        for host in defaults.loopback_hosts_with_alias:
            assert handler_contract_compliance_check._is_loopback_host(host)
        assert not handler_contract_compliance_check._is_loopback_host(
            "svc.example.com"
        )

    def test_pin_bump_source_url_uses_the_declared_source_control_host(self) -> None:
        host = ModelNetworkDefaults.load().source_control_host
        assert handler_dependency_pin_bump._source_url().startswith(f"https://{host}/")


@pytest.mark.unit
class TestCheckerReportsNoNetworkLiteral:
    @pytest.mark.parametrize("module", _TOUCHED_MODULES, ids=lambda m: m.__name__)
    def test_module_holds_no_host_address_or_port_literal(
        self, module: ModuleType
    ) -> None:
        assert module.__file__ is not None
        result = ValidatorContractsAndDi().validate_file(Path(module.__file__))
        assert [
            f"{i.line_number}: {i.message}"
            for i in result.issues
            if i.code in _NETWORK_RULES
        ] == []

    def test_checker_still_flags_a_planted_literal(self, tmp_path: Path) -> None:
        planted = tmp_path / "src" / "omnibase_core" / "planted_network.py"
        planted.parent.mkdir(parents=True)
        address = ".".join(["10", "1", "2", "3"])
        planted.write_text(f'ADDRESS = "{address}"\n')
        (tmp_path / ".git").mkdir()
        result = ValidatorContractsAndDi().validate_file(planted)
        assert {i.code for i in result.issues} & _NETWORK_RULES
