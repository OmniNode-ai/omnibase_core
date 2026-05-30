# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for architecture-handshakes/gitignore-baseline.yaml (OMN-12451).

This spec is the machine-readable source of truth for which .gitignore
managed blocks every downstream repo must contain. The T2 validator reads
this file, assembles the verbatim block (start marker → ordered patterns →
end marker), and asserts its presence in each target .gitignore.

These tests lock the schema shape so changes to the spec cannot silently
break the validator. If a test fails here, update the schema version in
the spec file before landing the change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

SPEC_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "architecture-handshakes"
    / "gitignore-baseline.yaml"
)

# Sections the DoD requires. Extending this list is a backwards-compatible
# change; removing from it is not.
REQUIRED_SECTIONS = {"universal", "python"}

REQUIRED_BLOCK_FIELDS = {
    "description",
    "start_marker",
    "end_marker",
    "applies_when",
    "patterns",
}

VALID_APPLIES_WHEN = {"always", "pyproject_toml_present"}

# Patterns the spec must declare per section. These are the exact strings
# specified in OMN-12451; removing or reordering any of them is a breaking
# change (the validator asserts sequence, not just membership).
UNIVERSAL_REQUIRED_PATTERNS = [
    ".env",
    ".env.*",
    "!.env.example",
    ".DS_Store",
    "*.log",
    ".idea/",
    ".vscode/",
    "test-results/",
    "playwright-report/",
]

PYTHON_REQUIRED_PATTERNS = [
    "__pycache__/",
    "*.py[cod]",
    "*$py.class",
    ".venv/",
    "venv/",
    "env/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".coverage",
    "htmlcov/",
    "dist/",
    "build/",
    "*.egg-info/",
]


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    assert SPEC_PATH.exists(), f"gitignore-baseline.yaml missing at {SPEC_PATH}"
    with SPEC_PATH.open() as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), "spec root must be a mapping"
    return data


def test_top_level_schema_shape(spec: dict[str, Any]) -> None:
    """Spec file has the top-level keys the validator expects."""
    required = {"schema_version", "managed_blocks", "metadata"}
    assert required <= set(spec.keys()), (
        f"missing top-level keys: {required - set(spec.keys())}"
    )


def test_schema_version_is_semver(spec: dict[str, Any]) -> None:
    """schema_version uses major/minor/patch mapping per ONEX convention."""
    version = spec["schema_version"]
    assert isinstance(version, dict), (
        f"schema_version must be a mapping, got {type(version).__name__}"
    )
    assert set(version.keys()) == {"major", "minor", "patch"}, (
        f"schema_version keys must be {{major, minor, patch}}, got {set(version.keys())}"
    )
    for key, value in version.items():
        assert isinstance(value, int) and value >= 0, (
            f"schema_version.{key} must be a non-negative int, got {value!r}"
        )


def test_required_sections_present(spec: dict[str, Any]) -> None:
    """Both 'universal' and 'python' blocks must be declared."""
    blocks = spec["managed_blocks"]
    assert isinstance(blocks, dict), "managed_blocks must be a mapping"
    missing = REQUIRED_SECTIONS - set(blocks.keys())
    assert not missing, f"managed_blocks missing required sections: {missing}"


def test_every_block_has_required_fields(spec: dict[str, Any]) -> None:
    """Each managed block declares all fields the validator reads."""
    missing: dict[str, set[str]] = {}
    for name, block in spec["managed_blocks"].items():
        gap = REQUIRED_BLOCK_FIELDS - set(block.keys())
        if gap:
            missing[name] = gap
    assert not missing, f"managed blocks missing fields: {missing}"


def test_applies_when_is_valid(spec: dict[str, Any]) -> None:
    """applies_when must be one of the known discriminator values."""
    for name, block in spec["managed_blocks"].items():
        value = block["applies_when"]
        assert value in VALID_APPLIES_WHEN, (
            f"{name}.applies_when must be one of {VALID_APPLIES_WHEN}, got {value!r}"
        )


def test_universal_applies_always(spec: dict[str, Any]) -> None:
    """Universal block must apply to every repo (no pyproject.toml gate)."""
    assert spec["managed_blocks"]["universal"]["applies_when"] == "always"


def test_python_applies_when_pyproject_toml_present(spec: dict[str, Any]) -> None:
    """Python block is gated on pyproject.toml presence."""
    assert spec["managed_blocks"]["python"]["applies_when"] == "pyproject_toml_present"


def test_markers_are_non_empty_strings(spec: dict[str, Any]) -> None:
    for name, block in spec["managed_blocks"].items():
        for marker_field in ("start_marker", "end_marker"):
            value = block[marker_field]
            assert isinstance(value, str) and value.strip(), (
                f"{name}.{marker_field} must be a non-empty string, got {value!r}"
            )


def test_patterns_are_ordered_lists_of_strings(spec: dict[str, Any]) -> None:
    for name, block in spec["managed_blocks"].items():
        patterns = block["patterns"]
        assert isinstance(patterns, list), f"{name}.patterns must be a list"
        assert len(patterns) > 0, f"{name}.patterns must not be empty"
        for pat in patterns:
            assert isinstance(pat, str), (
                f"{name}.patterns entries must be strings, got {type(pat).__name__!r}"
            )


def test_universal_contains_required_patterns_in_order(spec: dict[str, Any]) -> None:
    """Universal block contains exactly the OMN-12451 specified patterns in order.

    Sequence matters — the T2 validator assembles a verbatim block and asserts
    presence. Any reordering is a breaking change.
    """
    patterns = spec["managed_blocks"]["universal"]["patterns"]
    assert patterns == UNIVERSAL_REQUIRED_PATTERNS, (
        f"universal patterns diverge from OMN-12451 spec.\n"
        f"  expected: {UNIVERSAL_REQUIRED_PATTERNS}\n"
        f"  actual:   {patterns}"
    )


def test_python_contains_required_patterns_in_order(spec: dict[str, Any]) -> None:
    """Python block contains exactly the OMN-12451 specified patterns in order."""
    patterns = spec["managed_blocks"]["python"]["patterns"]
    assert patterns == PYTHON_REQUIRED_PATTERNS, (
        f"python patterns diverge from OMN-12451 spec.\n"
        f"  expected: {PYTHON_REQUIRED_PATTERNS}\n"
        f"  actual:   {patterns}"
    )


def test_markers_follow_onex_convention(spec: dict[str, Any]) -> None:
    """Markers must follow the '# === onex-managed: <name> ===' convention."""
    for name, block in spec["managed_blocks"].items():
        start = block["start_marker"]
        end = block["end_marker"]
        assert start == f"# === onex-managed: {name} ===", (
            f"{name}.start_marker does not follow convention: {start!r}"
        )
        assert end == f"# === end onex-managed: {name} ===", (
            f"{name}.end_marker does not follow convention: {end!r}"
        )


def test_metadata_references_owning_ticket(spec: dict[str, Any]) -> None:
    metadata = spec["metadata"]
    assert isinstance(metadata, dict), "metadata must be a mapping"
    related = metadata.get("related_tickets", [])
    assert "OMN-12451" in related, (
        "metadata.related_tickets must include OMN-12451 (this spec's owner ticket)"
    )
