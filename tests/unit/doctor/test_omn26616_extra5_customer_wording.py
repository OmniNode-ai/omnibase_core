# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-26616 EXTRA5: what a customer reads from doctor never names an environment variable.

Each test runs the real check with its setting unset (or malformed) and reads the message.
Red on the previous head, where the message named LINEAR_API_KEY or KAFKA_BOOTSTRAP_SERVERS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.doctor.checks.check_kafka import CheckKafka
from omnibase_core.doctor.checks.check_linear import CheckLinear

if TYPE_CHECKING:
    import pytest


def test_linear_skip_message_does_not_name_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    message = CheckLinear().run().message
    assert "LINEAR_API_KEY" not in message
    assert "Linear API key" in message


def test_kafka_skip_message_does_not_name_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
    message = CheckKafka().run().message
    assert "KAFKA_BOOTSTRAP_SERVERS" not in message


def test_kafka_bad_port_message_does_not_name_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "host:notaport")
    message = CheckKafka().run().message
    assert "KAFKA_BOOTSTRAP_SERVERS" not in message
