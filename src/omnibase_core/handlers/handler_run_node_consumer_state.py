# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Say whether a bus's runtime consumes a node's command topic, before a run-node request is sent (OMN-24561)."""

from __future__ import annotations

import importlib
from typing import Literal

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.util_consumer_group import TOPIC_SCOPE_INFIX
from omnibase_core.models.event_bus.model_node_broker_binding import (
    ModelNodeBrokerBinding,
)

RuntimeConsumerState = Literal["serving", "not_loaded", "unknown"]


def read_runtime_consumer_state(
    bootstrap_servers: str,
    client_security: dict[str, str],
    command_topic: str,
    timeout_s: float,
) -> RuntimeConsumerState:
    """One bounded admin read of the runtime's per-topic consumer groups.

    Only positive evidence refuses: the runtime's groups are visible to the caller, none of them is scoped to
    ``command_topic`` (or the ones that are hold no live member of it). A broker that cannot be read, a listing with
    errors, a group that is rebalancing, and a caller whose ACLs hide every runtime group are all ``"unknown"``,
    because absence of evidence is not evidence of absence. ``timeout_s`` (the caller's own run-node timeout) bounds
    every broker call.

    Returns:
        ``"serving"`` when a stable runtime group holds a partition of the topic, ``"not_loaded"`` when the visible
        runtime groups prove none does, ``"unknown"`` when the admin view is too incomplete to say.
    """
    try:
        kafka = importlib.import_module("confluent_kafka")
        admin_module = importlib.import_module("confluent_kafka.admin")
    except ImportError:
        return "unknown"
    try:
        admin = admin_module.AdminClient(
            {"bootstrap.servers": bootstrap_servers, **client_security}
        )
        listing = admin.list_consumer_groups(request_timeout=timeout_s).result(
            timeout=timeout_s
        )
        if listing.errors:
            return "unknown"
        group_ids = [group.group_id for group in listing.valid]
        if not any(TOPIC_SCOPE_INFIX in group_id for group_id in group_ids):
            return "unknown"
        topic_group_ids = [
            group_id
            for group_id in group_ids
            if group_id.endswith(TOPIC_SCOPE_INFIX + command_topic)
        ]
        if not topic_group_ids:
            return "not_loaded"
        described = admin.describe_consumer_groups(
            topic_group_ids, request_timeout=timeout_s
        )
        for group_id in topic_group_ids:
            description = described[group_id].result(timeout=timeout_s)
            state_name = str(
                getattr(description.state, "name", description.state)
            ).upper()
            if state_name in ("EMPTY", "DEAD"):
                continue
            if state_name != "STABLE":
                return "unknown"
            for member in description.members:
                for partition in member.assignment.topic_partitions:
                    if partition.topic == command_topic:
                        return "serving"
        return "not_loaded"
    except (kafka.KafkaException, OSError, ValueError, TimeoutError, RuntimeError):
        return "unknown"


def node_not_loaded_refusal(
    node_id: str,
    binding: ModelNodeBrokerBinding,
    command_topic: str,
    timeout_s: float,
) -> dict[str, str] | None:
    """The typed refusal fields (message, refusal, command_topic) when the bus's runtime provably has no consumer for
    ``command_topic``; None otherwise."""
    state = read_runtime_consumer_state(
        binding.bootstrap_servers or "",
        binding.client_security(),
        command_topic,
        timeout_s,
    )
    if state != "not_loaded":
        return None
    return {
        "message": (
            f"No runtime consumer serves {command_topic}: node {node_id} is not loaded "
            "in the runtime of this bus; nothing was sent."
        ),
        "refusal": "node_not_loaded",
        "command_topic": command_topic,
    }


def broker_unreachable_error(
    exc: Exception, bootstrap_servers: str, node_id: str, security: dict[str, str]
) -> ModelOnexError:
    """Build the actionable error for the first broker touch's raw client error (OMN-13857, OMN-17427).

    A SASL listener closes an unauthenticated connection with the same transport error, so the security protocol is
    named when none is configured. Only the protocol is ever echoed.
    """
    protocol = security.get("security.protocol")
    auth_hint = (
        f" The client connected with security.protocol={protocol}."
        if protocol
        else " The lane declares no security protocol, so the client "
        "connected in plaintext; a lane broker that requires SASL closes "
        "an unauthenticated connection with this same error."
    )
    return ModelOnexError(
        error_code=EnumCoreErrorCode.RUNTIME_ERROR,
        message=(
            f"Kafka broker unreachable at {bootstrap_servers!r}: {exc}. "
            "Verify the lane named in the node's contract overlay is "
            "reachable from this host, or run the node locally (bus-less) "
            f"with `onex run {node_id}`.{auth_hint}"
        ),
    )
