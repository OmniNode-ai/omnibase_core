# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Zone classifier: classify a file path into an EnumFileZone (OMN-10355)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.enums.enum_file_zone import EnumFileZone

_GENERATED_MARKERS = ("__pycache__", "dist/", ".generated.", "node_modules/")
_TEST_PREFIXES = ("tests/", "test/")
_DOCS_PREFIXES = ("docs/", "standards/")
_BUILD_PREFIXES = ("scripts/",)
_BUILD_NAMES = {"Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Makefile"}
_CONFIG_SUFFIXES = (".yaml", ".yml", ".toml", ".json", ".ini")


def classify_path(path: Path) -> EnumFileZone:
    """Classify *path* into its EnumFileZone.

    Priority order: generated > production > test > config > docs > build.
    Symlinks are resolved before classification so the target's directory
    structure determines the zone, not the link location.
    """
    resolved = path.resolve() if path.exists() else path
    s = resolved.as_posix()

    if any(m in s for m in _GENERATED_MARKERS):
        return EnumFileZone.GENERATED

    if "/src/" in f"/{s}" or s.startswith("src/"):
        return EnumFileZone.PRODUCTION

    if any(s.startswith(p) or f"/{p}" in f"/{s}" for p in _TEST_PREFIXES):
        return EnumFileZone.TEST

    if resolved.name in _BUILD_NAMES:
        return EnumFileZone.BUILD

    if any(s.startswith(p) for p in _DOCS_PREFIXES) or resolved.suffix == ".md":
        return EnumFileZone.DOCS

    if resolved.suffix in _CONFIG_SUFFIXES:
        return EnumFileZone.CONFIG

    if any(s.startswith(p) for p in _BUILD_PREFIXES):
        return EnumFileZone.BUILD

    return EnumFileZone.PRODUCTION
