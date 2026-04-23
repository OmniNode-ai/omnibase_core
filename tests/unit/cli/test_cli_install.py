# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the onex install command (.oncp archive installation)."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path
from unittest.mock import patch

import click
import pytest
import yaml

from omnibase_core.cli.cli_install import _install_oncp


def _make_oncp(
    tmp_path: Path,
    *,
    metadata: object,
    contract: dict[str, object] | None = None,
    extra_members: list[tuple[str, bytes]] | None = None,
) -> Path:
    """Build a minimal .oncp archive in tmp_path and return its path."""
    archive = tmp_path / "test_node-1.0.0.oncp"

    if contract is None:
        contract = {"name": "test_node", "version": "1.0.0"}

    with tarfile.open(archive, "w:gz") as tar:

        def _add(name: str, data: bytes) -> None:
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

        if metadata is not None:
            _add("metadata.yaml", yaml.safe_dump(metadata).encode("utf-8"))
        _add("contract.yaml", yaml.safe_dump(contract).encode("utf-8"))
        for name, data in extra_members or []:
            _add(name, data)

    return archive


@pytest.mark.unit
class TestInstallOncpMetadataValidation:
    """Guard the metadata.yaml validation path — no silent 'unknown' fallback."""

    def test_missing_name_raises(self, tmp_path: Path) -> None:
        archive = _make_oncp(tmp_path, metadata={"version": "1.0.0"})
        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=tmp_path / "registry",
        ):
            with pytest.raises(click.ClickException, match="missing required 'name'"):
                _install_oncp(archive, dry_run=True, upgrade=False, verbose=False)

    def test_missing_version_raises(self, tmp_path: Path) -> None:
        archive = _make_oncp(tmp_path, metadata={"name": "test_node"})
        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=tmp_path / "registry",
        ):
            with pytest.raises(click.ClickException, match="missing required"):
                _install_oncp(archive, dry_run=True, upgrade=False, verbose=False)

    def test_non_mapping_metadata_raises(self, tmp_path: Path) -> None:
        archive = _make_oncp(tmp_path, metadata=["not", "a", "mapping"])
        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=tmp_path / "registry",
        ):
            with pytest.raises(click.ClickException, match="not a valid YAML mapping"):
                _install_oncp(archive, dry_run=True, upgrade=False, verbose=False)


@pytest.mark.unit
class TestInstallOncpPathTraversal:
    """Guard against CVE-2007-4559 class extraction attacks.

    PEP 706 ``filter="data"`` semantics: absolute paths are silently
    neutralized (leading "/" stripped), and symlinks / device files
    are rejected with a ``FilterError``. We assert the absolute-path
    member never escapes ``install_path``.
    """

    def test_traversal_member_neutralized_by_data_filter(self, tmp_path: Path) -> None:
        """A member with ``..`` traversal must not escape install_path."""
        registry = tmp_path / "registry"
        malicious = tmp_path / "node-1.0.0.oncp"
        sentinel_outside = tmp_path / "escape.txt"

        with tarfile.open(malicious, "w:gz") as tar:

            def _add(name: str, data: bytes) -> None:
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

            _add(
                "metadata.yaml",
                yaml.safe_dump({"name": "node", "version": "1.0.0"}).encode(),
            )
            _add(
                "contract.yaml",
                yaml.safe_dump({"name": "node", "version": "1.0.0"}).encode(),
            )
            # Attempt traversal: would land in tmp_path/escape.txt without filter.
            traversal = tarfile.TarInfo(name="../escape.txt")
            traversal.size = 3
            tar.addfile(traversal, io.BytesIO(b"pwn"))

        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=registry,
        ):
            # The ``data`` filter raises OutsideDestinationError for ``..``.
            with pytest.raises(tarfile.TarError):
                _install_oncp(malicious, dry_run=False, upgrade=False, verbose=False)

        # The sentinel outside install_path must never have been written.
        assert not sentinel_outside.exists()

    def test_absolute_path_member_neutralized_by_data_filter(
        self, tmp_path: Path
    ) -> None:
        """Absolute-path members are stripped to relative paths by the data filter."""
        registry = tmp_path / "registry"
        malicious = tmp_path / "node-1.0.0.oncp"

        with tarfile.open(malicious, "w:gz") as tar:

            def _add(name: str, data: bytes) -> None:
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

            _add(
                "metadata.yaml",
                yaml.safe_dump({"name": "node", "version": "1.0.0"}).encode(),
            )
            _add(
                "contract.yaml",
                yaml.safe_dump({"name": "node", "version": "1.0.0"}).encode(),
            )
            absolute = tarfile.TarInfo(name="/tmp/absolute-escape.txt")
            absolute.size = 3
            tar.addfile(absolute, io.BytesIO(b"pwn"))

        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=registry,
        ):
            _install_oncp(malicious, dry_run=False, upgrade=False, verbose=False)

        # If the data filter is active, the leading "/" was stripped and the
        # file was written under install_path, NOT at /tmp/absolute-escape.txt.
        install_path = registry / "node"
        assert (install_path / "tmp" / "absolute-escape.txt").exists()
        assert not Path("/tmp/absolute-escape.txt").exists() or (
            Path("/tmp/absolute-escape.txt").read_text() != "pwn"
        )
