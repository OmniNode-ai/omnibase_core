# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for SD-01 standalone CLI subcommands (OMN-8788).

Covers:
- onex health --json (Kafka reachability in structured JSON)
- onex run-node <node_id> --input <json> --timeout <sec>
- onex bootstrap apply (reads stdin, writes config)
- onex config init (scaffolds ~/.onex/config.yaml)
- onex config get <key> (reads from config)
- onex refresh-credentials (AWS Secrets Manager pull)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli

pytestmark = pytest.mark.unit


class TestHealthJsonOutput:
    """Tests for onex health --json (Kafka reachability)."""

    def test_health_json_flag_produces_valid_json(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=(True, "Kafka reachable at localhost:19092"),
        ):
            result = runner.invoke(cli, ["health", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "checks" in data
        assert "overall" in data

    def test_health_json_includes_kafka_check(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=(True, "Kafka reachable"),
        ):
            result = runner.invoke(cli, ["health", "--json"])
        data = json.loads(result.output)
        kafka_checks = [c for c in data["checks"] if "kafka" in c["name"].lower()]
        assert len(kafka_checks) == 1
        assert kafka_checks[0]["healthy"] is True

    def test_health_json_hard_fail_on_kafka_unreachable(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_commands._check_kafka_reachable",
            return_value=(False, "Kafka not reachable"),
        ):
            result = runner.invoke(cli, ["health", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["overall"] == "unhealthy"

    def test_health_without_json_still_works(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["health"])
        assert "ONEX Health Check" in result.output


class TestRunNodeCommand:
    """Tests for onex run-node <node_id> --input <json>."""

    def test_run_node_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["run-node", "--help"])
        assert result.exit_code == 0
        assert "node_id" in result.output.lower() or "NODE_ID" in result.output

    def test_run_node_missing_input_fails(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["run-node", "my.node.id"])
        assert result.exit_code != 0

    def test_run_node_invalid_json_input_fails(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["run-node", "my.node.id", "--input", "not-valid-json"]
        )
        assert result.exit_code != 0
        assert (
            "invalid json" in result.output.lower() or "json" in result.output.lower()
        )

    def test_run_node_kafka_publish_success(self) -> None:
        runner = CliRunner()
        mock_response = {"status": "completed", "result": {"key": "value"}}
        with patch(
            "omnibase_core.cli.cli_run_node.publish_and_poll",
            return_value=mock_response,
        ):
            result = runner.invoke(
                cli,
                ["run-node", "my.node.id", "--input", '{"foo": "bar"}'],
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "completed"

    def test_run_node_timeout_returns_skill_routing_error(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_run_node.publish_and_poll",
            return_value=None,
        ):
            result = runner.invoke(
                cli,
                [
                    "run-node",
                    "my.node.id",
                    "--input",
                    '{"foo": "bar"}',
                    "--timeout",
                    "1",
                ],
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error_type"] == "SkillRoutingError"
        assert "timeout" in data["message"].lower()

    def test_run_node_kafka_connection_failure(self) -> None:
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_run_node.publish_and_poll",
            side_effect=ConnectionError("Kafka unreachable"),
        ):
            result = runner.invoke(
                cli,
                ["run-node", "my.node.id", "--input", '{"foo": "bar"}'],
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error_type"] == "SkillRoutingError"


class TestBootstrapApplyCommand:
    """Tests for onex bootstrap apply."""

    def test_bootstrap_apply_reads_stdin_writes_config(self, tmp_path: Path) -> None:
        config_content = "kafka:\n  bootstrap_servers: localhost:9092\n"
        config_file = tmp_path / ".onex" / "config.yaml"

        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_bootstrap._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["bootstrap", "apply"], input=config_content)
        assert result.exit_code == 0
        assert config_file.exists()
        assert "kafka" in config_file.read_text()

    def test_bootstrap_apply_creates_parent_dirs(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_bootstrap._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["bootstrap", "apply"], input="key: value\n")
        assert result.exit_code == 0
        assert config_file.parent.exists()

    def test_bootstrap_apply_empty_stdin_fails(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_bootstrap._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["bootstrap", "apply"], input="")
        assert result.exit_code != 0


class TestConfigInitCommand:
    """Tests for onex config init."""

    def test_config_init_scaffolds_config_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_config._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["config", "init"])
        assert result.exit_code == 0
        assert config_file.exists()
        content = config_file.read_text()
        assert "kafka" in content
        assert "bootstrap_servers" in content

    def test_config_init_does_not_overwrite_existing(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("existing: config\n")
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_config._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["config", "init"])
        assert result.exit_code != 0
        assert "already exists" in result.output.lower()
        assert config_file.read_text() == "existing: config\n"

    def test_config_init_force_overwrites(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("existing: config\n")
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_config._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["config", "init", "--force"])
        assert result.exit_code == 0
        assert "kafka" in config_file.read_text()


class TestConfigGetCommand:
    """Tests for onex config get <key>."""

    def test_config_get_existing_key(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(
            "kafka:\n  bootstrap_servers: localhost:19092\nmode: standalone\n"
        )
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_config._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["config", "get", "mode"])
        assert result.exit_code == 0
        assert "standalone" in result.output

    def test_config_get_nested_key(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("kafka:\n  bootstrap_servers: localhost:19092\n")
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_config._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["config", "get", "kafka.bootstrap_servers"])
        assert result.exit_code == 0
        assert "localhost:19092" in result.output

    def test_config_get_missing_key_fails(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("kafka:\n  bootstrap_servers: localhost:19092\n")
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_config._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["config", "get", "nonexistent"])
        assert result.exit_code != 0

    def test_config_get_no_config_file_fails(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_config._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["config", "get", "mode"])
        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
        )


class TestRefreshCredentialsCommand:
    """Tests for onex refresh-credentials."""

    def test_refresh_credentials_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["refresh-credentials", "--help"])
        assert result.exit_code == 0
        assert "aws" in result.output.lower() or "credentials" in result.output.lower()

    def test_refresh_credentials_no_config_fails(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_refresh_credentials._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["refresh-credentials"])
        assert result.exit_code != 0

    def test_refresh_credentials_no_aws_section_fails(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("kafka:\n  bootstrap_servers: localhost:19092\n")
        runner = CliRunner()
        with patch(
            "omnibase_core.cli.cli_refresh_credentials._config_path",
            return_value=config_file,
        ):
            result = runner.invoke(cli, ["refresh-credentials"])
        assert result.exit_code != 0
        assert "aws" in result.output.lower()

    def test_refresh_credentials_success(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".onex" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(
            "aws:\n  secret_name: my-secret\n  region: us-east-1\n"
            "kafka:\n  bootstrap_servers: placeholder\n"
        )
        mock_secrets = {"kafka_bootstrap_servers": "real-broker:9092"}
        runner = CliRunner()
        with (
            patch(
                "omnibase_core.cli.cli_refresh_credentials._config_path",
                return_value=config_file,
            ),
            patch(
                "omnibase_core.cli.cli_refresh_credentials._fetch_aws_secrets",
                return_value=mock_secrets,
            ),
        ):
            result = runner.invoke(cli, ["refresh-credentials"])
        assert result.exit_code == 0
        assert (
            "updated" in result.output.lower() or "refreshed" in result.output.lower()
        )
