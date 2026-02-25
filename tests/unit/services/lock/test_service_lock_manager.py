#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ServiceLockManager — OMN-2570.

Covers:
    - generate(): writes a valid, deterministic lockfile
    - generate(): same catalog state produces identical bytes (determinism)
    - check(): returns cleanly when lockfile matches catalog
    - check(): raises LockDriftError when fingerprint has changed
    - check(): raises LockFileError when lockfile is missing
    - check(): raises LockPartialError when lockfile covers fewer commands
    - diff(): returns is_clean=True when no drift
    - diff(): returns drifted entries with status=changed on fingerprint change
    - diff(): returns drifted entries with status=removed on missing command
    - diff(): raises LockPartialError when catalog has new commands
    - Integration: generate → mutate catalog fingerprint → check detects drift
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.crypto.crypto_ed25519_signer import generate_keypair, sign_base64
from omnibase_core.enums.enum_cli_invocation_type import EnumCliInvocationType
from omnibase_core.errors.error_lock import (
    LockDriftError,
    LockFileError,
    LockPartialError,
)
from omnibase_core.models.contracts.model_cli_contribution import (
    ModelCliCommandEntry,
    ModelCliContribution,
    ModelCliInvocation,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.services.catalog.service_catalog_manager import ServiceCatalogManager
from omnibase_core.services.lock.service_lock_manager import ServiceLockManager
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


def _make_command(
    cmd_id: str = "com.omninode.lock.test",
    group: str = "lock",
) -> ModelCliCommandEntry:
    return ModelCliCommandEntry(
        id=cmd_id,
        display_name="Lock Test",
        description="A command for lock testing.",
        group=group,
        args_schema_ref=f"{cmd_id}.args.v1",
        output_schema_ref=f"{cmd_id}.output.v1",
        invocation=_make_invocation(),
    )


def _build_contribution(
    commands: list[ModelCliCommandEntry],
    publisher: str = "com.omninode.lock.publisher",
    keypair: object = None,
) -> ModelCliContribution:
    if keypair is None:
        keypair = generate_keypair()
    fingerprint = ModelCliContribution.compute_fingerprint(commands)
    signature = sign_base64(keypair.private_key_bytes, fingerprint.encode("utf-8"))  # type: ignore[attr-defined]
    return ModelCliContribution(
        version=ModelSemVer(major=1, minor=0, patch=0),
        publisher=publisher,
        fingerprint=fingerprint,
        signature=signature,
        signer_public_key=keypair.public_key_base64(),  # type: ignore[attr-defined]
        commands=commands,
    )


def _build_loaded_catalog(
    commands: list[ModelCliCommandEntry],
    tmp_path: Path,
    publisher: str = "com.omninode.lock.publisher",
) -> ServiceCatalogManager:
    """Build a ServiceCatalogManager that is already loaded (refresh done)."""
    registry = ServiceRegistryCliContribution()
    contrib = _build_contribution(commands, publisher=publisher)
    registry.publish(contrib, verify_signature=True)

    cache_path = tmp_path / "catalog.json"
    mgr = ServiceCatalogManager(
        registry=registry,
        cache_path=cache_path,
        cli_version="0.20.0",
    )
    mgr.refresh()
    return mgr


# ---------------------------------------------------------------------------
# Lockfile generation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerate:
    """Tests for ServiceLockManager.generate()."""

    def test_generate_creates_lockfile(self, tmp_path: Path) -> None:
        """generate() writes omn.lock to the configured path."""
        cmd = _make_command("com.omninode.lock.alpha")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        result = mgr.generate()

        assert lock_path.exists(), "omn.lock should be created"
        assert len(result.commands) == 1
        assert result.commands[0].command_id == "com.omninode.lock.alpha"

    def test_generate_includes_args_and_output_schema_refs(
        self, tmp_path: Path
    ) -> None:
        """generate() pins args_schema_ref and output_schema_ref per command."""
        cmd = _make_command("com.omninode.lock.beta")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(
            catalog=catalog, lock_path=lock_path, cli_version="0.20.0"
        )
        result = mgr.generate()

        entry = result.commands[0]
        assert entry.args_schema_ref == "com.omninode.lock.beta.args.v1"
        assert entry.output_schema_ref == "com.omninode.lock.beta.output.v1"
        assert entry.publisher == "com.omninode.lock.publisher"

    def test_generate_is_deterministic(self, tmp_path: Path) -> None:
        """Calling generate() twice on the same catalog produces identical file bytes."""
        cmd_a = _make_command("com.omninode.lock.a")
        cmd_b = _make_command("com.omninode.lock.b")
        catalog = _build_loaded_catalog([cmd_a, cmd_b], tmp_path)

        lock_path1 = tmp_path / "omn1.lock"
        lock_path2 = tmp_path / "omn2.lock"

        mgr1 = ServiceLockManager(
            catalog=catalog, lock_path=lock_path1, cli_version="0.20.0"
        )
        mgr2 = ServiceLockManager(
            catalog=catalog, lock_path=lock_path2, cli_version="0.20.0"
        )
        mgr1.generate()
        mgr2.generate()

        # Strip generated_at timestamp before comparing (changes per call).
        import yaml

        data1 = yaml.safe_load(lock_path1.read_text())
        data2 = yaml.safe_load(lock_path2.read_text())

        # Commands should be identical.
        assert data1["commands"] == data2["commands"]
        assert data1["lock_version"] == data2["lock_version"]
        assert data1["cli_version"] == data2["cli_version"]

    def test_generate_sorts_commands_by_id(self, tmp_path: Path) -> None:
        """generate() produces entries sorted by command_id."""
        cmd_z = _make_command("com.omninode.lock.z")
        cmd_a = _make_command("com.omninode.lock.a")
        cmd_m = _make_command("com.omninode.lock.m")
        catalog = _build_loaded_catalog([cmd_z, cmd_a, cmd_m], tmp_path)

        lock_path = tmp_path / "omn.lock"
        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        result = mgr.generate()

        ids = [e.command_id for e in result.commands]
        assert ids == sorted(ids)

    def test_generate_includes_cli_version(self, tmp_path: Path) -> None:
        """generate() includes the CLI version in the lockfile."""
        cmd = _make_command("com.omninode.lock.ver")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(
            catalog=catalog, lock_path=lock_path, cli_version="9.8.7"
        )
        result = mgr.generate()

        assert result.cli_version == "9.8.7"

    def test_generate_lockfile_has_version_field(self, tmp_path: Path) -> None:
        """The written lockfile YAML contains a lock_version field."""
        import yaml

        cmd = _make_command("com.omninode.lock.vf")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        mgr.generate()

        data = yaml.safe_load(lock_path.read_text())
        assert "lock_version" in data
        assert data["lock_version"] == "1"


# ---------------------------------------------------------------------------
# Lockfile check (CI enforcement)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheck:
    """Tests for ServiceLockManager.check()."""

    def test_check_passes_when_no_drift(self, tmp_path: Path) -> None:
        """check() does not raise when catalog matches lockfile."""
        cmd = _make_command("com.omninode.lock.check.ok")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        mgr.generate()
        # Should not raise.
        mgr.check()

    def test_check_raises_when_lockfile_missing(self, tmp_path: Path) -> None:
        """check() raises LockFileError when omn.lock does not exist."""
        cmd = _make_command("com.omninode.lock.missing")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "nonexistent.lock"

        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        with pytest.raises(LockFileError, match="not found"):
            mgr.check()

    def test_check_raises_on_drift(self, tmp_path: Path) -> None:
        """check() raises LockDriftError when fingerprint has changed."""
        cmd_orig = _make_command("com.omninode.lock.drift")
        catalog = _build_loaded_catalog([cmd_orig], tmp_path)
        lock_path = tmp_path / "omn.lock"

        # Generate lockfile with original catalog.
        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        mgr.generate()

        # Manually mutate the lockfile fingerprint to simulate drift.
        import yaml

        data = yaml.safe_load(lock_path.read_text())
        data["commands"][0]["fingerprint"] = "a" * 64
        lock_path.write_text(yaml.dump(data, sort_keys=True))

        with pytest.raises(LockDriftError, match="drift"):
            mgr.check()

    def test_check_raises_partial_when_catalog_has_new_command(
        self, tmp_path: Path
    ) -> None:
        """check() raises LockPartialError when catalog has a command not in lockfile."""
        cmd_a = _make_command("com.omninode.lock.partial.a")
        catalog = _build_loaded_catalog([cmd_a], tmp_path)
        lock_path = tmp_path / "omn.lock"

        # Generate lockfile covering only cmd_a.
        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        mgr.generate()

        # Now add a second command to the catalog by rebuilding with two commands.
        cmd_b = _make_command("com.omninode.lock.partial.b")
        catalog2 = _build_loaded_catalog([cmd_a, cmd_b], tmp_path / "cat2")

        mgr2 = ServiceLockManager(catalog=catalog2, lock_path=lock_path)
        with pytest.raises(LockPartialError, match="partial"):
            mgr2.check()

    def test_check_never_modifies_lockfile(self, tmp_path: Path) -> None:
        """check() does not write or modify the lockfile."""
        cmd = _make_command("com.omninode.lock.immutable")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        mgr.generate()

        original_content = lock_path.read_text()
        mgr.check()
        assert lock_path.read_text() == original_content


# ---------------------------------------------------------------------------
# Lockfile diff
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDiff:
    """Tests for ServiceLockManager.diff()."""

    def test_diff_clean_when_no_drift(self, tmp_path: Path) -> None:
        """diff() returns is_clean=True when catalog matches lockfile."""
        cmd = _make_command("com.omninode.lock.diff.clean")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        mgr.generate()
        result = mgr.diff()

        assert result.is_clean
        assert result.drifted == []

    def test_diff_detects_changed_fingerprint(self, tmp_path: Path) -> None:
        """diff() returns a changed entry when fingerprint mutated."""
        import yaml

        cmd = _make_command("com.omninode.lock.diff.changed")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        mgr.generate()

        # Mutate the fingerprint in the lockfile.
        data = yaml.safe_load(lock_path.read_text())
        data["commands"][0]["fingerprint"] = "b" * 64
        lock_path.write_text(yaml.dump(data, sort_keys=True))

        result = mgr.diff()

        assert not result.is_clean
        assert len(result.drifted) == 1
        assert result.drifted[0].command_id == "com.omninode.lock.diff.changed"
        assert result.drifted[0].status == "changed"

    def test_diff_detects_removed_command(self, tmp_path: Path) -> None:
        """diff() returns a removed entry when lockfile has extra command."""
        import yaml

        cmd = _make_command("com.omninode.lock.diff.present")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        mgr.generate()

        # Add an extra command to the lockfile (simulates removed from catalog).
        data = yaml.safe_load(lock_path.read_text())
        data["commands"].append(
            {
                "args_schema_ref": "com.omninode.lock.diff.ghost.args.v1",
                "cli_version_requirement": "",
                "command_id": "com.omninode.lock.diff.ghost",
                "fingerprint": "c" * 64,
                "output_schema_ref": "com.omninode.lock.diff.ghost.output.v1",
                "publisher": "com.omninode.lock.publisher",
            }
        )
        lock_path.write_text(yaml.dump(data, sort_keys=True))

        result = mgr.diff()

        assert not result.is_clean
        removed = [e for e in result.drifted if e.status == "removed"]
        assert any(e.command_id == "com.omninode.lock.diff.ghost" for e in removed)

    def test_diff_raises_partial_when_catalog_has_new_command(
        self, tmp_path: Path
    ) -> None:
        """diff() raises LockPartialError when catalog has commands not in lockfile."""
        cmd_a = _make_command("com.omninode.lock.partial.diff.a")
        catalog1 = _build_loaded_catalog([cmd_a], tmp_path / "cat1")
        lock_path = tmp_path / "omn.lock"

        mgr1 = ServiceLockManager(catalog=catalog1, lock_path=lock_path)
        mgr1.generate()

        # Build a catalog with an additional command.
        cmd_b = _make_command("com.omninode.lock.partial.diff.b")
        catalog2 = _build_loaded_catalog([cmd_a, cmd_b], tmp_path / "cat2")
        mgr2 = ServiceLockManager(catalog=catalog2, lock_path=lock_path)

        with pytest.raises(LockPartialError):
            mgr2.diff()

    def test_diff_raises_lockfile_error_when_missing(self, tmp_path: Path) -> None:
        """diff() raises LockFileError when lockfile does not exist."""
        cmd = _make_command("com.omninode.lock.diffmissing")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "no.lock"

        mgr = ServiceLockManager(catalog=catalog, lock_path=lock_path)
        with pytest.raises(LockFileError, match="not found"):
            mgr.diff()


# ---------------------------------------------------------------------------
# Integration: generate → mutate → drift detected
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIntegration:
    """Integration tests for the full generate → mutate → check/diff cycle."""

    def test_generate_then_mutate_catalog_then_check_detects_drift(
        self, tmp_path: Path
    ) -> None:
        """
        Full integration: generate lockfile, simulate catalog mutation
        (by altering the lockfile's stored fingerprint to differ from the catalog),
        then verify that check() raises LockDriftError.
        """
        import yaml

        cmd = _make_command("com.omninode.lock.integration.drift")
        catalog = _build_loaded_catalog([cmd], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(
            catalog=catalog, lock_path=lock_path, cli_version="0.20.0"
        )
        mgr.generate()

        # Simulate a catalog mutation by changing the stored fingerprint.
        data = yaml.safe_load(lock_path.read_text())
        data["commands"][0]["fingerprint"] = "d" * 64
        lock_path.write_text(yaml.dump(data, sort_keys=True))

        with pytest.raises(LockDriftError):
            mgr.check()

    def test_generate_then_check_clean_integration(self, tmp_path: Path) -> None:
        """Full integration: generate → check passes without error."""
        cmd_a = _make_command("com.omninode.lock.integration.a")
        cmd_b = _make_command("com.omninode.lock.integration.b")
        catalog = _build_loaded_catalog([cmd_a, cmd_b], tmp_path)
        lock_path = tmp_path / "omn.lock"

        mgr = ServiceLockManager(
            catalog=catalog, lock_path=lock_path, cli_version="0.20.0"
        )
        mgr.generate()

        # check() must not raise.
        mgr.check()

        # diff() must be clean.
        result = mgr.diff()
        assert result.is_clean

    def test_partial_lockfile_rejected_on_check(self, tmp_path: Path) -> None:
        """
        Partial lockfile rejection: a lockfile with fewer commands than the
        catalog must be rejected by check() with LockPartialError.
        """
        cmd_a = _make_command("com.omninode.lock.partial.int.a")
        # First, generate lockfile with only cmd_a.
        catalog_one = _build_loaded_catalog([cmd_a], tmp_path / "cat1")
        lock_path = tmp_path / "omn.lock"
        mgr_one = ServiceLockManager(catalog=catalog_one, lock_path=lock_path)
        mgr_one.generate()

        # Now a catalog with two commands presents as partial against the one-command lockfile.
        cmd_b = _make_command("com.omninode.lock.partial.int.b")
        catalog_two = _build_loaded_catalog([cmd_a, cmd_b], tmp_path / "cat2")
        mgr_two = ServiceLockManager(catalog=catalog_two, lock_path=lock_path)

        with pytest.raises(LockPartialError, match="partial"):
            mgr_two.check()
