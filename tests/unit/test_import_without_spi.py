# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test that omnibase_core is importable without omnibase_spi installed."""

import subprocess
import sys

import pytest


@pytest.mark.unit
def test_core_importable_without_spi() -> None:
    """Verify omnibase_core can be imported even if omnibase_spi is absent."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import omnibase_core; print(omnibase_core.__version__)",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, f"Import failed: {result.stderr}"


@pytest.mark.unit
def test_onex_cli_works_without_spi() -> None:
    """Verify the onex CLI entry-point loads without omnibase_spi."""
    result = subprocess.run(
        [sys.executable, "-m", "omnibase_core.cli.cli_commands", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, f"CLI --help failed: {result.stderr}"
