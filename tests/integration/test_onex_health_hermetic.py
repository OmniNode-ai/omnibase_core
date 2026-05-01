# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hermetic integration tests for `onex health` CLI command (OMN-8797).

Runs end-to-end through the Click CLI runner with all external services
mocked. No network access required — suitable for CI.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli

pytestmark = pytest.mark.integration

HEALTHY_KAFKA = (True, "Kafka reachable at mock-host:19092")
UNHEALTHY_KAFKA = (False, "Kafka not reachable at mock-host:19092")


class TestHealthJsonOutput:
    """Verify --json produces valid structured output."""

    def test_all_checks_healthy(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["overall"] == "healthy"
        assert len(data["checks"]) == 4
        for check in data["checks"]:
            assert check["healthy"] is True
            assert isinstance(check["name"], str)
            assert isinstance(check["message"], str)

    def test_kafka_unhealthy_marks_overall_unhealthy(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=UNHEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["overall"] == "unhealthy"
        kafka_check = [c for c in data["checks"] if "kafka" in c["name"].lower()]
        assert len(kafka_check) == 1
        assert kafka_check[0]["healthy"] is False

    def test_json_check_schema(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health", "--json"])
        data = json.loads(result.output)
        assert "overall" in data
        assert "checks" in data
        for check in data["checks"]:
            assert "name" in check
            assert "healthy" in check
            assert "message" in check

    def test_expected_check_names(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health", "--json"])
        data = json.loads(result.output)
        names = [c["name"] for c in data["checks"]]
        assert "Core imports" in names
        assert "Validation system" in names
        assert "Error handling" in names
        assert "Kafka reachability" in names


class TestHealthHumanOutput:
    """Verify human-readable output formatting."""

    def test_header_present(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health"])
        assert "ONEX Health Check" in result.output

    def test_all_healthy_message(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health"])
        assert "All health checks passed!" in result.output

    def test_failure_message(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=UNHEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health"])
        assert "Some health checks failed." in result.output

    def test_verbose_shows_messages_for_healthy(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["--verbose", "health"])
        assert "Kafka reachable at mock-host:19092" in result.output

    def test_non_verbose_hides_healthy_details(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health"])
        assert "Kafka reachable at mock-host:19092" not in result.output

    def test_non_verbose_shows_unhealthy_details(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=UNHEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health"])
        assert "Kafka not reachable at mock-host:19092" in result.output


class TestHealthComponentFilter:
    """Verify --component filtering."""

    def test_filter_core(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health", "--component", "core"])
        assert "Core imports" in result.output
        assert "Kafka" not in result.output

    def test_filter_kafka(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health", "--component", "kafka"])
        assert "Kafka reachability" in result.output
        assert "Core imports" not in result.output

    def test_filter_no_match_exits_error(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health", "--component", "nonexistent"])
        assert result.exit_code != 0
        assert "No health checks match" in result.output

    def test_filter_json_error(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(
                cli, ["health", "--component", "nonexistent", "--json"]
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert "error" in data
        assert "available_components" in data

    def test_filter_case_insensitive(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health", "--component", "KAFKA"])
        assert "Kafka reachability" in result.output


class TestHealthExitCodes:
    """Verify exit codes map to health status."""

    def test_exit_zero_when_all_healthy(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health"])
        assert result.exit_code == 0

    def test_exit_nonzero_when_any_unhealthy(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=UNHEALTHY_KAFKA,
        ):
            result = runner.invoke(cli, ["health"])
        assert result.exit_code == 1

    def test_exit_nonzero_on_check_exception(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            side_effect=RuntimeError("unexpected failure"),
        ):
            result = runner.invoke(cli, ["health", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["overall"] == "unhealthy"
        kafka_check = [c for c in data["checks"] if "kafka" in c["name"].lower()]
        assert len(kafka_check) == 1
        assert kafka_check[0]["healthy"] is False
        assert "unexpected failure" in kafka_check[0]["message"]


class TestHealthHermeticIsolation:
    """Verify the test suite itself is hermetic — no real network access."""

    def test_kafka_env_var_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=HEALTHY_KAFKA,
        ) as mock_kafka:
            result = runner.invoke(cli, ["health", "--json"])
        mock_kafka.assert_called_once()
        assert result.exit_code == 0

    def test_no_real_socket_calls(self) -> None:
        with (
            patch(
                "omnibase_core.cli.cli_commands._check_kafka_reachable",
                return_value=HEALTHY_KAFKA,
            ),
            patch("socket.create_connection") as mock_socket,
        ):
            runner = CliRunner()
            runner.invoke(cli, ["health", "--json"])
            mock_socket.assert_not_called()
