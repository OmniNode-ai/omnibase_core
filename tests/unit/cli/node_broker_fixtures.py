# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolved node broker bindings for the ``onex run-node`` tests (OMN-22362)."""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr

from omnibase_core.enums.enum_event_bus_type import EnumEventBusType
from omnibase_core.models.event_bus.model_node_broker_binding import (
    ModelNodeBrokerBinding,
)

#: Where the production tests patch the resolver ``onex run-node`` calls.
RESOLVER_PATCH_TARGET = "omnibase_core.cli.cli_run_node._resolve_binding"
OVERLAY_PATH = Path("/overlays/test-node/overlay.yaml")


def kafka_binding(
    bootstrap_servers: str = "testhost:19092",
    *,
    sasl_password: str | None = None,
) -> ModelNodeBrokerBinding:
    """A kafka binding; with a password it is a SCRAM lane, otherwise plaintext."""
    if sasl_password is None:
        return ModelNodeBrokerBinding(
            bus_type=EnumEventBusType.KAFKA,
            overlay_path=OVERLAY_PATH,
            lane="dev",
            bootstrap_servers=bootstrap_servers,
            security_protocol="PLAINTEXT",
        )
    return ModelNodeBrokerBinding(
        bus_type=EnumEventBusType.KAFKA,
        overlay_path=OVERLAY_PATH,
        lane="dev",
        bootstrap_servers=bootstrap_servers,
        security_protocol="SASL_PLAINTEXT",
        sasl_mechanism="SCRAM-SHA-256",
        sasl_username="dev-principal",
        sasl_password=SecretStr(sasl_password),
    )
