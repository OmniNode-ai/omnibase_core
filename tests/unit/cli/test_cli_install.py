# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the onex install command (.oncp archive installation)."""

from __future__ import annotations

import io
import tarfile
from importlib.machinery import ModuleSpec
from pathlib import Path
from unittest.mock import patch

import click
import pytest
import yaml

from omnibase_core.cli.cli_install import (
    _install_oncp,
    _resolve_entry_point_contract_path,
)


def _make_oncp(
    tmp_path: Path,
    *,
    metadata: object,
    contract: dict[str, object] | None = None,
    extra_members: list[tuple[str, bytes]] | None = None,
    archive_name: str = "test_node-1.0.0.oncp",
) -> Path:
    """Build a minimal .oncp archive in tmp_path and return its path."""
    archive = tmp_path / archive_name

    if contract is None:
        contract = {
            "name": "test_node",
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "COMPUTE_GENERIC",
        }

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
            with pytest.raises(
                click.ClickException, match="'name' must be a non-empty"
            ):
                _install_oncp(archive, dry_run=True, upgrade=False, verbose=False)


@pytest.mark.unit
class TestInstallEntrypointContractResolution:
    """Entry-point contract lookup must not import node code."""

    def test_resolves_contract_from_module_spec(self, tmp_path: Path) -> None:
        node_dir = tmp_path / "node_pkg"
        node_dir.mkdir()
        contract = node_dir / "contract.yaml"
        contract.write_text(
            "name: node\ncontract_version: {major: 1, minor: 0, patch: 0}\n"
            "node_type: COMPUTE_GENERIC\n",
            encoding="utf-8",
        )
        spec = ModuleSpec("node_pkg", loader=None, is_package=True)
        spec.submodule_search_locations = [str(node_dir)]

        with patch(
            "omnibase_core.cli.cli_install.importlib.util.find_spec",
            return_value=spec,
        ) as find_spec:
            resolved = _resolve_entry_point_contract_path("node_pkg:Node")

        assert resolved == contract
        find_spec.assert_called_once_with("node_pkg")

    def test_missing_version_raises(self, tmp_path: Path) -> None:
        archive = _make_oncp(tmp_path, metadata={"name": "test_node"})
        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=tmp_path / "registry",
        ):
            with pytest.raises(
                click.ClickException, match="'version' must be a non-empty"
            ):
                _install_oncp(archive, dry_run=True, upgrade=False, verbose=False)

    def test_non_mapping_metadata_raises(self, tmp_path: Path) -> None:
        archive = _make_oncp(tmp_path, metadata=["not", "a", "mapping"])
        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=tmp_path / "registry",
        ):
            with pytest.raises(click.ClickException, match="not a valid YAML mapping"):
                _install_oncp(archive, dry_run=True, upgrade=False, verbose=False)

    def test_non_string_name_raises(self, tmp_path: Path) -> None:
        archive = _make_oncp(tmp_path, metadata={"name": 12345, "version": "1.0.0"})
        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=tmp_path / "registry",
        ):
            with pytest.raises(
                click.ClickException, match="'name' must be a non-empty"
            ):
                _install_oncp(archive, dry_run=True, upgrade=False, verbose=False)


@pytest.mark.unit
class TestInstallOncpUnsafeNameRejection:
    """Guard against path-escape via crafted metadata.yaml 'name' values.

    ``install_path = registry_dir / package_name`` plus the ``--upgrade``
    path's ``shutil.rmtree(install_path)`` means an attacker-controlled
    ``name`` like ``"../outside"`` could otherwise delete arbitrary dirs
    outside the registry. These tests lock in the rejection.
    """

    @pytest.mark.parametrize(
        "unsafe_name",
        [
            "../escape",
            "nested/path",
            "double/../nest",
            "leading/slash",
            ".",
            "..",
            "/absolute/name",
            "back\\slash",
        ],
    )
    def test_unsafe_name_rejected(self, tmp_path: Path, unsafe_name: str) -> None:
        archive = _make_oncp(
            tmp_path,
            metadata={"name": unsafe_name, "version": "1.0.0"},
            archive_name="unsafe-1.0.0.oncp",
        )
        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=tmp_path / "registry",
        ):
            with pytest.raises(click.ClickException, match="safe package basename"):
                _install_oncp(archive, dry_run=True, upgrade=False, verbose=False)


@pytest.mark.unit
class TestInstallOncpPathTraversal:
    """Guard against CVE-2007-4559 class tar extraction attacks.

    Combined with the PEP 706 ``filter="data"`` + staging-dir-then-move
    flow, tar members that attempt to escape or alias outside install_path
    must either be neutralized or rejected, and the real install dir must
    never be touched on failure.
    """

    def test_traversal_member_neutralized_by_data_filter(self, tmp_path: Path) -> None:
        """A member with ``..`` traversal must not escape the staging dir."""
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
                yaml.safe_dump(
                    {
                        "name": "node",
                        "contract_version": {"major": 1, "minor": 0, "patch": 0},
                        "node_type": "COMPUTE_GENERIC",
                    }
                ).encode(),
            )
            traversal = tarfile.TarInfo(name="../escape.txt")
            traversal.size = 3
            tar.addfile(traversal, io.BytesIO(b"pwn"))

        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=registry,
        ):
            with pytest.raises(tarfile.TarError):
                _install_oncp(malicious, dry_run=False, upgrade=False, verbose=False)

        assert not sentinel_outside.exists()
        # Staging failure must not leave a partial install behind.
        assert not (registry / "node").exists()

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
                yaml.safe_dump(
                    {
                        "name": "node",
                        "contract_version": {"major": 1, "minor": 0, "patch": 0},
                        "node_type": "COMPUTE_GENERIC",
                    }
                ).encode(),
            )
            absolute = tarfile.TarInfo(name="/tmp/absolute-escape.txt")
            absolute.size = 3
            tar.addfile(absolute, io.BytesIO(b"pwn"))

        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=registry,
        ):
            _install_oncp(malicious, dry_run=False, upgrade=False, verbose=False)

        install_path = registry / "node"
        assert (install_path / "tmp" / "absolute-escape.txt").exists()
        # No file at the absolute path outside the registry.
        assert not Path("/tmp/absolute-escape.txt").exists() or (
            Path("/tmp/absolute-escape.txt").read_text() != "pwn"
        )


@pytest.mark.unit
class TestInstallOncpAtomicity:
    """The staging-dir flow keeps --dry-run validating and --upgrade atomic."""

    def test_dry_run_validates_contract_before_returning(self, tmp_path: Path) -> None:
        """--dry-run must surface a broken contract.yaml, not silently pass."""
        # contract.yaml missing required 'name' field.
        archive = _make_oncp(
            tmp_path,
            metadata={"name": "node", "version": "1.0.0"},
            contract={
                "contract_version": {"major": 1, "minor": 0, "patch": 0},
                "node_type": "COMPUTE_GENERIC",
            },
        )
        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=tmp_path / "registry",
        ):
            with pytest.raises(click.ClickException, match=r"contract\.yaml missing"):
                _install_oncp(archive, dry_run=True, upgrade=False, verbose=False)

    def test_failed_upgrade_preserves_existing_install(self, tmp_path: Path) -> None:
        """If the new archive's contract fails to validate, the old install survives."""
        registry = tmp_path / "registry"
        install_path = registry / "node"
        install_path.mkdir(parents=True)
        (install_path / "sentinel.txt").write_text("OLD_VERSION")

        # New archive with an invalid contract.yaml (missing required 'name').
        bad_archive = _make_oncp(
            tmp_path,
            metadata={"name": "node", "version": "2.0.0"},
            contract={
                "contract_version": {"major": 2, "minor": 0, "patch": 0},
                "node_type": "COMPUTE_GENERIC",
            },
        )

        with patch(
            "omnibase_core.cli.cli_install._get_registry_dir",
            return_value=registry,
        ):
            with pytest.raises(click.ClickException):
                _install_oncp(bad_archive, dry_run=False, upgrade=True, verbose=False)

        # Old install must be untouched.
        assert (install_path / "sentinel.txt").read_text() == "OLD_VERSION"
