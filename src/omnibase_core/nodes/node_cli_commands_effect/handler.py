# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Kafka health effect and plain-words failure text for the onex CLI."""

from __future__ import annotations

import socket

from omnibase_core.models.cli.model_health_request import ModelHealthRequest
from omnibase_core.models.cli.model_health_result import ModelHealthResult

__all__ = [
    "kafka_skipped_prefix",
    "NodeCliCommandsEffect",
    "check_kafka_reachable",
    "plain_failure",
]

kafka_skipped_prefix = "Kafka check skipped"
_CONNECT_WAIT = 3.0

_REINSTALL = "Fix: Run `uv tool install --reinstall omninode-onex`."
_PLAIN_FAILURES = {
    "Core imports": f"Part of ONEX could not be loaded. {_REINSTALL}",
    "Validation system": f"The validation part of ONEX could not start. {_REINSTALL}",
    "Error handling": f"ONEX's own problem reporting is not working. {_REINSTALL}",
}
_UNEXPECTED = (
    f"An unexpected problem occurred while running a health check. {_REINSTALL}"
)
_BAD_ADDRESS = (
    "The configured message-bus address has a port that is not a number. "
    "Fix: Set the address again with a number after the colon."
)


def plain_failure(check_name: str) -> str:
    """Fixed words and a Fix line for a failed health check; never exception text."""
    return _PLAIN_FAILURES.get(check_name, _UNEXPECTED)


class NodeCliCommandsEffect:
    """Own the Kafka reachability effect behind the CLI wrapper."""

    def handle(self, request: ModelHealthRequest) -> ModelHealthResult:
        """Judge the message-bus address in the request."""
        healthy, message = self.check_kafka_reachable(request.kafka_bootstrap_servers)
        return ModelHealthResult(healthy=healthy, message=message)

    @staticmethod
    def check_kafka_reachable(raw: str | None = None) -> tuple[bool, str]:
        """Return a plain-words result for unset, invalid or unreachable Kafka."""
        if not raw or not str(raw).strip():
            return True, (
                f"{kafka_skipped_prefix} because no Kafka address is set. "
                "Fix: export KAFKA_BOOTSTRAP_SERVERS=<host>:<port>"
            )

        first = str(raw).strip().split(",", 1)[0].strip()
        host, sep, port_str = first.rpartition(":")
        if not sep:
            host, port = first, 19092
        else:
            try:
                port = int(port_str)
            except ValueError:
                return False, _BAD_ADDRESS

        try:
            conn = socket.create_connection((host, port), timeout=_CONNECT_WAIT)
            conn.close()
            return True, f"Kafka reachable at {host}:{port}"
        except (TimeoutError, OSError):
            return False, f"Kafka not reachable at {host}:{port}"


def check_kafka_reachable(raw: str | None = None) -> tuple[bool, str]:
    """Keep the baselined CLI wrapper thin."""
    return NodeCliCommandsEffect.check_kafka_reachable(raw)
