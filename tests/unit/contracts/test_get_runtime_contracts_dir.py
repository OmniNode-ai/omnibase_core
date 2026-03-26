#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for get_runtime_contracts_dir() resolution order.

Validates the 3-tier resolution strategy (OMN-6484):
    1. ONEX_RUNTIME_CONTRACTS_DIR env var
    2. Repository-relative path
    3. importlib.resources package data (PyPI installs)
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.contracts.runtime_contracts import get_runtime_contracts_dir

EXPECTED_CONTRACTS = {
    "contract_loader_effect.yaml",
    "contract_registry_reducer.yaml",
    "event_bus_wiring_effect.yaml",
    "node_graph_reducer.yaml",
    "runtime_orchestrator.yaml",
}


@pytest.mark.unit
class TestGetRuntimeContractsDirEnvOverride:
    """Tests for env var override (resolution tier 1)."""

    def test_env_override_returns_specified_dir(self, tmp_path: Path) -> None:
        """Env var ONEX_RUNTIME_CONTRACTS_DIR takes highest priority."""
        with patch.dict("os.environ", {"ONEX_RUNTIME_CONTRACTS_DIR": str(tmp_path)}):
            result = get_runtime_contracts_dir()
        assert result == tmp_path

    def test_env_override_nonexistent_dir_falls_through(self) -> None:
        """Non-existent env var path falls through to next tier."""
        with patch.dict(
            "os.environ",
            {"ONEX_RUNTIME_CONTRACTS_DIR": "/nonexistent/path/abc123"},
        ):
            # Should not raise because repo-relative path exists in dev
            result = get_runtime_contracts_dir()
        assert result.is_dir()


@pytest.mark.unit
class TestGetRuntimeContractsDirRepoRelative:
    """Tests for repo-relative resolution (resolution tier 2)."""

    def test_repo_relative_resolves_in_dev(self) -> None:
        """In a dev checkout, repo-relative path resolves correctly."""
        os.environ.pop("ONEX_RUNTIME_CONTRACTS_DIR", None)
        result = get_runtime_contracts_dir()

        assert result.is_dir()
        found = {f.name for f in result.glob("*.yaml")}
        assert EXPECTED_CONTRACTS.issubset(found), (
            f"Missing contracts: {EXPECTED_CONTRACTS - found}"
        )


@pytest.mark.unit
class TestGetRuntimeContractsDirPackageData:
    """Tests for importlib.resources fallback (resolution tier 3)."""

    def test_importlib_fallback_when_repo_path_missing(self) -> None:
        """When repo-relative path doesn't exist, importlib.resources resolves.

        This simulates a PyPI install by patching the module's __file__ so
        the repo-relative path computation points to a non-existent directory,
        forcing the function to fall through to the importlib.resources tier.
        """
        import omnibase_core.contracts.runtime_contracts as mod

        original_file = mod.__file__
        # Point __file__ to a fake location so repo-relative resolution fails
        fake = "/tmp/fake_pypi_site/omnibase_core/contracts/runtime_contracts.py"

        os.environ.pop("ONEX_RUNTIME_CONTRACTS_DIR", None)
        try:
            mod.__file__ = fake  # type: ignore[misc]
            result = get_runtime_contracts_dir()
        finally:
            mod.__file__ = original_file  # type: ignore[misc]

        # Should resolve via importlib.resources to the runtime_data package
        assert result.is_dir()
        found = {f.name for f in result.glob("*.yaml")}
        assert EXPECTED_CONTRACTS.issubset(found), (
            f"Missing contracts from package data: {EXPECTED_CONTRACTS - found}"
        )

    def test_package_data_dir_has_all_contracts(self) -> None:
        """The runtime_data package directory contains all expected YAMLs."""
        import importlib.resources

        ref = importlib.resources.files("omnibase_core.contracts.runtime_data")
        pkg_data_dir = Path(str(ref))

        assert pkg_data_dir.is_dir(), f"runtime_data not found at {pkg_data_dir}"
        found = {f.name for f in pkg_data_dir.glob("*.yaml")}
        assert EXPECTED_CONTRACTS.issubset(found), (
            f"Missing contracts in runtime_data: {EXPECTED_CONTRACTS - found}"
        )


@pytest.mark.unit
class TestGetRuntimeContractsDirAllPathsFail:
    """Tests for error case when no path resolves."""

    def test_raises_file_not_found_when_all_fail(self) -> None:
        """FileNotFoundError raised when all resolution tiers fail."""
        import omnibase_core.contracts.runtime_contracts as mod

        original_file = mod.__file__
        fake = "/tmp/no_such_install/omnibase_core/contracts/runtime_contracts.py"

        os.environ.pop("ONEX_RUNTIME_CONTRACTS_DIR", None)

        with patch(
            "omnibase_core.contracts.runtime_contracts.importlib.resources.files",
            side_effect=ModuleNotFoundError("no such package"),
        ):
            try:
                mod.__file__ = fake  # type: ignore[misc]
                with pytest.raises(
                    FileNotFoundError, match="Runtime contracts not found"
                ):
                    get_runtime_contracts_dir()
            finally:
                mod.__file__ = original_file  # type: ignore[misc]
