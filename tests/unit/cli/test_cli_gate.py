# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the thin OmniGate CLI surface."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_gate import gate
from omnibase_core.gate import load_omnigate_config

pytestmark = pytest.mark.unit


def _init_git_dir(repo: Path) -> None:
    (repo / ".git" / "hooks").mkdir(parents=True)


def test_install_scaffolds_valid_config_and_pre_push_hook(tmp_path: Path) -> None:
    _init_git_dir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        gate,
        [
            "install",
            "--repo",
            str(tmp_path),
            "--project-name",
            "demo",
            "--project-url",
            "https://github.com/org/demo",
        ],
    )

    assert result.exit_code == 0, result.output
    config_path = tmp_path / ".omnigate.yaml"
    hook_path = tmp_path / ".git" / "hooks" / "pre-push"
    config = load_omnigate_config(config_path)
    assert config.project_name == "demo"
    assert config.project_url.unicode_string() == "https://github.com/org/demo"
    assert config.checks[0].name == "unit"
    assert hook_path.read_text(encoding="utf-8").startswith("#!/bin/sh")
    assert "onex gate run" in hook_path.read_text(encoding="utf-8")


def test_install_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    _init_git_dir(tmp_path)
    config_path = tmp_path / ".omnigate.yaml"
    config_path.write_text("already here\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(gate, ["install", "--repo", str(tmp_path)])

    assert result.exit_code != 0
    assert "Config already exists" in result.output


def test_validate_config_reports_hash_json(tmp_path: Path) -> None:
    _init_git_dir(tmp_path)
    runner = CliRunner()
    install_result = runner.invoke(gate, ["install", "--repo", str(tmp_path)])
    assert install_result.exit_code == 0, install_result.output

    result = runner.invoke(
        gate,
        ["validate-config", "--repo", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["valid"] is True
    assert payload["checks"] == 1
    assert payload["config_hash"].startswith("sha256:")


def test_validate_config_missing_file_fails_json(tmp_path: Path) -> None:
    _init_git_dir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        gate,
        ["validate-config", "--repo", str(tmp_path), "--json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["valid"] is False
    assert "OmniGate config not found" in payload["error"]


def test_validate_config_hash_error_fails_json(tmp_path: Path) -> None:
    _init_git_dir(tmp_path)
    runner = CliRunner()
    install_result = runner.invoke(gate, ["install", "--repo", str(tmp_path)])
    assert install_result.exit_code == 0, install_result.output

    with patch(
        "omnibase_core.cli.cli_gate.compute_config_hash",
        side_effect=OSError("hash read failed"),
    ):
        result = runner.invoke(
            gate,
            ["validate-config", "--repo", str(tmp_path), "--json"],
        )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["valid"] is False
    assert payload["error"] == "hash read failed"


def test_diff_hash_delegates_to_staged_helper(tmp_path: Path) -> None:
    runner = CliRunner()

    with patch(
        "omnibase_core.cli.cli_gate.compute_staged_diff_hash",
        return_value="sha256:abc",
    ) as compute:
        result = runner.invoke(gate, ["diff-hash", "--repo", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "sha256:abc"
    compute.assert_called_once_with(tmp_path.resolve(), allow_empty=False)


def test_diff_hash_delegates_to_pr_helper_json(tmp_path: Path) -> None:
    runner = CliRunner()

    with patch(
        "omnibase_core.cli.cli_gate.compute_pr_diff_hash",
        return_value="sha256:def",
    ) as compute:
        result = runner.invoke(
            gate,
            [
                "diff-hash",
                "--repo",
                str(tmp_path),
                "--base-ref",
                "base",
                "--head-ref",
                "head",
                "--allow-empty",
                "--json",
            ],
        )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"diff_hash": "sha256:def", "mode": "pr"}
    compute.assert_called_once_with(
        tmp_path.resolve(),
        base_sha="base",
        head_sha="head",
        allow_empty=True,
    )


def test_status_reports_config_and_hook(tmp_path: Path) -> None:
    _init_git_dir(tmp_path)
    runner = CliRunner()
    install_result = runner.invoke(gate, ["install", "--repo", str(tmp_path)])
    assert install_result.exit_code == 0, install_result.output

    result = runner.invoke(gate, ["status", "--repo", str(tmp_path), "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["config_found"] is True
    assert payload["config_valid"] is True
    assert payload["pre_push_hook_installed"] is True
    assert payload["checks"] == 1


def test_install_rejects_empty_git_metadata_file(tmp_path: Path) -> None:
    runner = CliRunner()
    (tmp_path / ".git").write_text("", encoding="utf-8")

    result = runner.invoke(gate, ["install", "--repo", str(tmp_path)])

    assert result.exit_code != 0
    assert "Git metadata file is empty" in result.output


def test_effectful_command_fails_cleanly_without_provider() -> None:
    runner = CliRunner()

    with patch("omnibase_core.cli.cli_gate.entry_points", return_value=()):
        result = runner.invoke(gate, ["run"])

    assert result.exit_code != 0
    assert "requires an installed gate services provider" in result.output


def test_effectful_command_delegates_to_gate_service() -> None:
    runner = CliRunner()
    services = SimpleNamespace()
    captured: dict[str, list[str]] = {}

    def verify(*, args: list[str]) -> str:
        captured["args"] = args
        return "verified"

    services.verify = verify  # type: ignore[attr-defined]  # NOTE(OMN-11139): SimpleNamespace test double intentionally exposes dynamic service attributes.
    entry_point = SimpleNamespace(
        name="omnigate",
        value="tests.omnigate_services",
        load=lambda: services,
    )

    with patch("omnibase_core.cli.cli_gate.entry_points", return_value=(entry_point,)):
        result = runner.invoke(gate, ["verify", "--receipt", "receipt.json"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "verified"
    assert captured["args"] == ["--receipt", "receipt.json"]
