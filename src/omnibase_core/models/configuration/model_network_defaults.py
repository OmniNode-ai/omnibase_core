# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Network defaults read from the packaged ``network_defaults.yaml`` (OMN-21681)."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

__all__ = ["ModelNetworkDefaults"]

_CONTRACT_PATH = Path(__file__).parent / "network_defaults.yaml"


class ModelNetworkDefaults(BaseModel):
    """Hosts, addresses and ports the model layer falls back to, declared in YAML.

    Attributes:
        loopback_name: The loopback host name.
        loopback_ipv4: The IPv4 loopback address.
        loopback_ipv6: The IPv6 loopback address.
        loopback_ipv6_alias: The host-file alias some resolvers give the IPv6 loopback.
        service_bind_address: The address a service binds when none is configured.
        http_port: The port of an HTTP or WebSocket endpoint with none given.
        grpc_port: The port of a gRPC endpoint with none given.
        postgresql_port: The port of a PostgreSQL connection with none given.
        mysql_port: The port of a MySQL connection with none given.
        sqlite_placeholder_port: The port a SQLite connection carries, as the
            connection model requires one but SQLite has none.
        node_registry_service_port: The service port of the NodeRegistry service.
        node_registry_prometheus_port: The metrics port of the NodeRegistry service.
        kafka_bootstrap_servers: The bootstrap servers a scaffolded user config names.
        source_control_host: The host of the git remote that holds the first-party repositories.
        redacted_redis_url: The URL returned when a Redis URL cannot be parsed for redaction.
        default_project_url_template: Project URL of a scaffolded gate config (``project_name`` field).
        linear_graphql_url: The Linear GraphQL endpoint the doctor check probes.
        unknown_entrypoint_uri: The entrypoint URI stamped when none is given.
        unknown_namespace_uri: The namespace URI stamped when none is given.
        sqlite_connection_url_template: SQLite connection string (``database`` field).
        mssql_connection_url_template: SQL Server connection string (``params`` field).
        broadcast_route_destination: The final destination of a broadcast route.
        kafka_advertised_listener: The advertised listener of a generated Kafka service.
        file_url_prefix: The prefix of a ``file`` artifact reference.
        example_telemetry_endpoint: The example telemetry endpoint of a capability.
        container_health_check_url_template: A container's own health-check URL
            (``host``, ``port`` and ``path`` fields).
        yamlfmt_repository_url: The repository of the yamlfmt pre-commit hook.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    loopback_name: str = Field(min_length=1)
    loopback_ipv4: str = Field(min_length=1)
    loopback_ipv6: str = Field(min_length=1)
    loopback_ipv6_alias: str = Field(min_length=1)
    service_bind_address: str = Field(min_length=1)
    http_port: int = Field(ge=0, le=65535)
    grpc_port: int = Field(ge=0, le=65535)
    postgresql_port: int = Field(ge=0, le=65535)
    mysql_port: int = Field(ge=0, le=65535)
    sqlite_placeholder_port: int = Field(ge=0, le=65535)
    node_registry_service_port: int = Field(ge=0, le=65535)
    node_registry_prometheus_port: int = Field(ge=0, le=65535)
    kafka_bootstrap_servers: str = Field(min_length=1)
    source_control_host: str = Field(min_length=1)
    redacted_redis_url: str = Field(min_length=1)
    default_project_url_template: str = Field(min_length=1)
    linear_graphql_url: str = Field(min_length=1)
    unknown_entrypoint_uri: str = Field(min_length=1)
    unknown_namespace_uri: str = Field(min_length=1)
    sqlite_connection_url_template: str = Field(min_length=1)
    mssql_connection_url_template: str = Field(min_length=1)
    broadcast_route_destination: str = Field(min_length=1)
    kafka_advertised_listener: str = Field(min_length=1)
    file_url_prefix: str = Field(min_length=1)
    example_telemetry_endpoint: str = Field(min_length=1)
    container_health_check_url_template: str = Field(min_length=1)
    yamlfmt_repository_url: str = Field(min_length=1)

    @classmethod
    def load(cls) -> ModelNetworkDefaults:
        """The defaults of the packaged contract, read once."""
        return _load_packaged()

    def default_project_url(self, project_name: str) -> str:
        """The project URL of a scaffolded gate config for ``project_name``."""
        return self.default_project_url_template.format(project_name=project_name)

    def container_health_check_url(self, port: int, path: str) -> str:
        """The URL a container probes on itself: the loopback name, ``port`` and ``path``."""
        return self.container_health_check_url_template.format(
            host=self.loopback_name, port=port, path=path
        )

    @property
    def local_hosts(self) -> frozenset[str]:
        """The loopback name and its IPv4 address."""
        return frozenset({self.loopback_name, self.loopback_ipv4})

    @property
    def loopback_hosts(self) -> frozenset[str]:
        """The loopback name and both loopback addresses."""
        return self.local_hosts | {self.loopback_ipv6}

    @property
    def loopback_hosts_with_alias(self) -> frozenset[str]:
        """The loopback hosts and the IPv6 loopback alias."""
        return self.loopback_hosts | {self.loopback_ipv6_alias}


@cache
def _load_packaged() -> ModelNetworkDefaults:
    with _CONTRACT_PATH.open(encoding="utf-8") as contract:
        return ModelNetworkDefaults.model_validate(YAML(typ="safe").load(contract))
