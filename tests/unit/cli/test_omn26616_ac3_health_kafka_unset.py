# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-26616 AC3: onex health names an unset Kafka setting in plain words."""

import json

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli


@pytest.fixture(autouse=True)
def _no_kafka(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)


def test_health_unset_kafka_prints_plain_sentence_and_fix() -> None:
    result = CliRunner().invoke(cli, ["health", "--component", "kafka"])
    assert result.exit_code == 0, result.output
    assert "KAFKA_BOOTSTRAP_SERVERS" in result.output
    assert "Fix: export KAFKA_BOOTSTRAP_SERVERS=" in result.output
    assert "Error: '" not in result.output


def test_health_json_unset_kafka_has_no_raw_exception() -> None:
    result = CliRunner().invoke(cli, ["health", "--component", "kafka", "--json"])
    assert result.exit_code == 0, result.output
    body = json.loads(result.output)
    message = body["checks"][0]["message"]
    assert "Fix: export KAFKA_BOOTSTRAP_SERVERS=" in message
    assert "Error: '" not in result.output


def test_health_empty_kafka_setting_is_treated_as_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "  ")
    result = CliRunner().invoke(cli, ["health", "--component", "kafka"])
    assert result.exit_code == 0, result.output
    assert "Fix:" in result.output


def test_health_bad_port_is_still_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "host:notaport")
    result = CliRunner().invoke(cli, ["health", "--component", "kafka"])
    assert result.exit_code != 0
