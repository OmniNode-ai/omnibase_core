# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Addresses and ports used by omnibase_core's connection models and loopback checks (OMN-21778).

The values live in ``network_defaults.yaml`` beside this module. Every field is required
and the model refuses an unknown key, so a value missing from the contract fails the load
instead of silently falling back to a literal in code. Call sites read the values through
``packaged_network_defaults()``.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

_PACKAGED_CONTRACT = Path(__file__).with_name("network_defaults.yaml")


class ModelNetworkDefaults(BaseModel):
    """Hosts and ports declared by the packaged network-defaults contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    local_hosts: frozenset[str] = Field(
        description="Host names and addresses that mean this machine (IPv4 and name only).",
    )
    loopback_hosts: frozenset[str] = Field(
        description="Host names and addresses that mean this machine, IPv6 loopback included.",
    )
    service_bind_host: str = Field(
        description="Interface a service binds when its config names none."
    )
    http_port: int = Field(ge=1, le=65535, description="Default HTTP port.")
    grpc_port: int = Field(ge=1, le=65535, description="Default gRPC port.")
    postgres_port: int = Field(ge=1, le=65535, description="Default PostgreSQL port.")
    mysql_port: int = Field(ge=1, le=65535, description="Default MySQL port.")
    sqlite_placeholder_port: int = Field(
        ge=0,
        le=65535,
        description="Port recorded for a SQLite config, which has no port.",
    )
    node_registry_port: int = Field(
        ge=1, le=65535, description="Service port of the node registry defaults."
    )
    node_registry_prometheus_port: int = Field(
        ge=1, le=65535, description="Prometheus port of the node registry defaults."
    )


@cache
def packaged_network_defaults() -> ModelNetworkDefaults:
    """The packaged network defaults, read once."""
    return load_and_validate_yaml_model(_PACKAGED_CONTRACT, ModelNetworkDefaults)
