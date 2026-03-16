# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the no-untyped-metadata pre-commit hook."""

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.mark.unit
def test_detects_untyped_metadata():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("metadata: dict[str, Any] = Field(default_factory=dict)\n")
        path = f.name
    result = subprocess.run(
        ["python", "scripts/check_no_untyped_metadata.py", path],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "untyped metadata dict" in result.stdout
    Path(path).unlink()


@pytest.mark.unit
def test_passes_with_exclude_comment():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(
            "metadata: dict[str, Any] = Field(...)  # ONEX_EXCLUDE: dict_str_any - extensibility\n"
        )
        path = f.name
    result = subprocess.run(
        ["python", "scripts/check_no_untyped_metadata.py", path],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    Path(path).unlink()


@pytest.mark.unit
def test_passes_with_typed_dict():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(
            "metadata: OutputMetadataDict = Field(default_factory=lambda: OutputMetadataDict())\n"
        )
        path = f.name
    result = subprocess.run(
        ["python", "scripts/check_no_untyped_metadata.py", path],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    Path(path).unlink()
