# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Zone classifier: classify a file path into an EnumFileZone (OMN-10355)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.enums.enum_file_zone import EnumFileZone

_GENERATED_MARKERS = ("__pycache__", "dist/", ".generated.", "node_modules/")
_TEST_PREFIXES = ("tests/", "test/")
# Top-level documentation and declarative-evidence trees: contract YAML,
# DoD receipts, and legacy .evidence/. Allowlists are policy inputs and must
# run the quality matrix. Production contract.yaml inside src/ is unaffected
# because the PRODUCTION check runs first.
_DOCS_PREFIXES = (
    "docs/",
    "standards/",
    "contracts/",
    "drift/dod_receipts/",
    ".evidence/",
)
_BUILD_PREFIXES = ("scripts/",)
_BUILD_NAMES = {"Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Makefile"}
_CONFIG_SUFFIXES = (".yaml", ".yml", ".toml", ".json", ".ini")


def classify_path(path: Path) -> EnumFileZone:
    """Classify *path* into its EnumFileZone.

    Priority: generated > production > test > build names > docs > config > build.
    Docs, test, and build prefixes are relative to the repository root (the current
    working directory), including when an existing file resolves to an
    absolute path.
    Symlinks are resolved before classification so the target's directory
    structure determines the zone, not the link location.
    """
    resolved = path.resolve() if path.exists() else path
    repo_root = Path.cwd().resolve()
    if resolved.is_absolute() and resolved.is_relative_to(repo_root):
        resolved = resolved.relative_to(repo_root)
    s = resolved.as_posix()

    if any(m in s for m in _GENERATED_MARKERS):
        return EnumFileZone.GENERATED

    if "/src/" in f"/{s}" or s.startswith("src/"):
        return EnumFileZone.PRODUCTION

    if s.startswith(_TEST_PREFIXES):
        return EnumFileZone.TEST

    if resolved.name in _BUILD_NAMES:
        return EnumFileZone.BUILD

    if s.startswith(_DOCS_PREFIXES) or resolved.suffix == ".md":
        return EnumFileZone.DOCS

    if resolved.suffix in _CONFIG_SUFFIXES:
        return EnumFileZone.CONFIG

    if s.startswith(_BUILD_PREFIXES):
        return EnumFileZone.BUILD

    return EnumFileZone.PRODUCTION
