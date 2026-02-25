#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for the ``omn lock`` CLI command group — OMN-2570.

Covers:
    - ``omn lock --help``: help output includes subcommands
    - ``omn lock generate``: exits non-zero when catalog cache missing
    - ``omn lock generate``: exits 0 and writes lockfile with valid catalog
    - ``omn lock check``: exits 0 when lockfile matches catalog
    - ``omn lock check``: exits non-zero when lockfile has drift
    - ``omn lock check``: exits non-zero when lockfile missing
    - ``omn lock diff``: exits 0 when no drift, non-zero when drift detected
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli
from omnibase_core.crypto.crypto_ed25519_signer import generate_keypair, sign_base64
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.models.contracts.model_cli_contribution import (
    ModelCliCommandEntry,
    ModelCliContribution,
    ModelCliInvocation,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.services.catalog.service_catalog_manager import ServiceCatalogManager
from omnibase_core.services.registry.service_registry_cli_contribution import (
    ServiceRegistryCliContribution,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_invocation() -> ModelCliInvocation:
    return ModelCliInvocation(
        invocation_type=EnumCliInvocationType.KAFKA_EVENT,
        topic="onex.cmd.test.v1",
    )


def _make_command(cmd_id: str = "com.omninode.lock.cli.cmd") -> ModelCliCommandEntry:
    return ModelCliCommandEntry(
        id=cmd_id,
        display_name="Lock CLI Test",
        description="CLI test command.",
        group="lock",
        args_schema_ref=f"{cmd_id}.args.v1",
        output_schema_ref=f"{cmd_id}.output.v1",
        invocation=_make_invocation(),
    )


def _build_catalog(
    commands: list[ModelCliCommandEntry],
    tmp_path: Path,
    publisher: str = "com.omninode.lock.publisher",
) -> tuple[ServiceCatalogManager, Path]:
    """Build and refresh a ServiceCatalogManager, return (manager, cache_path).

    Note: cli_version is left empty ("") so that the catalog passes version checks
    regardless of the installed CLI version during testing.
    """
    kp = generate_keypair()
    fp = ModelCliContribution.compute_fingerprint(commands)
    sig = sign_base64(kp.private_key_bytes, fp.encode("utf-8"))  # type: ignore[attr-defined]
    contrib = ModelCliContribution(
        version=ModelSemVer(major=1, minor=0, patch=0),
        publisher=publisher,
        fingerprint=fp,
        signature=sig,
        signer_public_key=kp.public_key_base64(),  # type: ignore[attr-defined]
        commands=commands,
    )

    registry = ServiceRegistryCliContribution()
    registry.publish(contrib, verify_signature=True)

    cache_path = tmp_path / "catalog.json"
    # cli_version="" disables version-gating so the catalog loads under any CLI version.
    mgr = ServiceCatalogManager(
        registry=registry,
        cache_path=cache_path,
        cli_version="",
    )
    mgr.refresh()
    return mgr, cache_path


# ---------------------------------------------------------------------------
# Help output tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLockHelp:
    """Tests for the ``omn lock`` command group help output."""

    def test_lock_group_shows_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["lock", "--help"])
        assert result.exit_code == 0
        assert "generate" in result.output
        assert "check" in result.output
        assert "diff" in result.output

    def test_lock_generate_shows_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["lock", "generate", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output

    def test_lock_check_shows_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["lock", "check", "--help"])
        assert result.exit_code == 0
        assert "--lockfile" in result.output

    def test_lock_diff_shows_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["lock", "diff", "--help"])
        assert result.exit_code == 0
        assert "--lockfile" in result.output


# ---------------------------------------------------------------------------
# omn lock generate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLockGenerate:
    """Tests for ``omn lock generate``."""

    def test_generate_fails_when_catalog_missing(self, tmp_path: Path) -> None:
        """generate exits non-zero when catalog cache does not exist."""
        runner = CliRunner()
        missing = tmp_path / "missing_catalog.json"
        lock_path = tmp_path / "omn.lock"

        result = runner.invoke(
            cli,
            [
                "lock",
                "generate",
                "--catalog",
                str(missing),
                "--output",
                str(lock_path),
            ],
        )
        assert result.exit_code != 0

    def test_generate_writes_lockfile(self, tmp_path: Path) -> None:
        """generate exits 0 and writes omn.lock when catalog is valid."""
        cmd = _make_command("com.omninode.lock.gen.write")
        _mgr, cache_path = _build_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "lock",
                "generate",
                "--catalog",
                str(cache_path),
                "--output",
                str(lock_path),
            ],
        )
        assert result.exit_code == 0, f"Unexpected output: {result.output}"
        assert lock_path.exists()
        assert "1 command" in result.output

    def test_generate_lockfile_is_valid_yaml(self, tmp_path: Path) -> None:
        """generate produces valid YAML with expected fields."""
        cmd = _make_command("com.omninode.lock.gen.yaml")
        _mgr, cache_path = _build_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "lock",
                "generate",
                "--catalog",
                str(cache_path),
                "--output",
                str(lock_path),
            ],
        )
        data = yaml.safe_load(lock_path.read_text())
        assert "lock_version" in data
        assert "commands" in data
        assert len(data["commands"]) == 1
        assert data["commands"][0]["command_id"] == "com.omninode.lock.gen.yaml"


# ---------------------------------------------------------------------------
# omn lock check
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLockCheck:
    """Tests for ``omn lock check``."""

    def test_check_passes_when_no_drift(self, tmp_path: Path) -> None:
        """check exits 0 when catalog matches lockfile."""
        cmd = _make_command("com.omninode.lock.check.ok")
        _mgr, cache_path = _build_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        runner = CliRunner()
        # First generate.
        runner.invoke(
            cli,
            [
                "lock",
                "generate",
                "--catalog",
                str(cache_path),
                "--output",
                str(lock_path),
            ],
        )

        # Then check.
        result = runner.invoke(
            cli,
            [
                "lock",
                "check",
                "--catalog",
                str(cache_path),
                "--lockfile",
                str(lock_path),
            ],
        )
        assert result.exit_code == 0
        assert "passed" in result.output

    def test_check_exits_nonzero_when_lockfile_missing(self, tmp_path: Path) -> None:
        """check exits non-zero when lockfile does not exist."""
        cmd = _make_command("com.omninode.lock.check.missing")
        _mgr, cache_path = _build_catalog([cmd], tmp_path)
        nonexistent = tmp_path / "no.lock"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "lock",
                "check",
                "--catalog",
                str(cache_path),
                "--lockfile",
                str(nonexistent),
            ],
        )
        assert result.exit_code != 0

    def test_check_exits_nonzero_on_drift(self, tmp_path: Path) -> None:
        """check exits non-zero when fingerprint in lockfile differs from catalog."""
        cmd = _make_command("com.omninode.lock.check.drift")
        _mgr, cache_path = _build_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "lock",
                "generate",
                "--catalog",
                str(cache_path),
                "--output",
                str(lock_path),
            ],
        )

        # Mutate the lockfile fingerprint.
        data = yaml.safe_load(lock_path.read_text())
        data["commands"][0]["fingerprint"] = "a" * 64
        lock_path.write_text(yaml.dump(data, sort_keys=True))

        result = runner.invoke(
            cli,
            [
                "lock",
                "check",
                "--catalog",
                str(cache_path),
                "--lockfile",
                str(lock_path),
            ],
        )
        assert result.exit_code != 0

    def test_check_never_modifies_lockfile(self, tmp_path: Path) -> None:
        """check does not write or modify the lockfile."""
        cmd = _make_command("com.omninode.lock.check.immutable")
        _mgr, cache_path = _build_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "lock",
                "generate",
                "--catalog",
                str(cache_path),
                "--output",
                str(lock_path),
            ],
        )

        original = lock_path.read_text()
        runner.invoke(
            cli,
            [
                "lock",
                "check",
                "--catalog",
                str(cache_path),
                "--lockfile",
                str(lock_path),
            ],
        )
        assert lock_path.read_text() == original


# ---------------------------------------------------------------------------
# omn lock diff
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLockDiff:
    """Tests for ``omn lock diff``."""

    def test_diff_exits_zero_when_clean(self, tmp_path: Path) -> None:
        """diff exits 0 and prints 'No drift' when catalog matches lockfile."""
        cmd = _make_command("com.omninode.lock.diff.clean")
        _mgr, cache_path = _build_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "lock",
                "generate",
                "--catalog",
                str(cache_path),
                "--output",
                str(lock_path),
            ],
        )

        result = runner.invoke(
            cli,
            [
                "lock",
                "diff",
                "--catalog",
                str(cache_path),
                "--lockfile",
                str(lock_path),
            ],
        )
        assert result.exit_code == 0
        assert "No drift" in result.output

    def test_diff_exits_nonzero_when_drifted(self, tmp_path: Path) -> None:
        """diff exits non-zero and prints drifted command when fingerprint changed."""
        cmd = _make_command("com.omninode.lock.diff.changed")
        _mgr, cache_path = _build_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "lock",
                "generate",
                "--catalog",
                str(cache_path),
                "--output",
                str(lock_path),
            ],
        )

        # Mutate the lockfile fingerprint.
        data = yaml.safe_load(lock_path.read_text())
        data["commands"][0]["fingerprint"] = "b" * 64
        lock_path.write_text(yaml.dump(data, sort_keys=True))

        result = runner.invoke(
            cli,
            [
                "lock",
                "diff",
                "--catalog",
                str(cache_path),
                "--lockfile",
                str(lock_path),
            ],
        )
        assert result.exit_code != 0
        assert "com.omninode.lock.diff.changed" in result.output

    def test_diff_exits_nonzero_when_lockfile_missing(self, tmp_path: Path) -> None:
        """diff exits non-zero when lockfile does not exist."""
        cmd = _make_command("com.omninode.lock.diff.missing")
        _mgr, cache_path = _build_catalog([cmd], tmp_path)
        nonexistent = tmp_path / "no.lock"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "lock",
                "diff",
                "--catalog",
                str(cache_path),
                "--lockfile",
                str(nonexistent),
            ],
        )
        assert result.exit_code != 0
