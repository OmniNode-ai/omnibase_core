# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Kafka health effect for the onex CLI."""

from __future__ import annotations

import socket

__all__ = ["kafka_skipped_prefix", "NodeCliCommandsEffect", "check_kafka_reachable"]

kafka_skipped_prefix = "Kafka check skipped"


class NodeCliCommandsEffect:
    """Own the Kafka reachability effect behind the CLI wrapper."""

    def handle(self, request: object) -> tuple[bool, str]:
        """Runtime adapter entry point; CLI uses the static seam."""
        return check_kafka_reachable()

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
                return False, f"Invalid port in KAFKA_BOOTSTRAP_SERVERS: {port_str!r}"

        try:
            conn = socket.create_connection((host, port), timeout=3)
            conn.close()
            return True, f"Kafka reachable at {host}:{port}"
        except (TimeoutError, OSError):
            return False, f"Kafka not reachable at {host}:{port}"


def check_kafka_reachable(raw: str | None = None) -> tuple[bool, str]:
    """Keep the baselined CLI wrapper thin."""
    return NodeCliCommandsEffect.check_kafka_reachable(raw)
