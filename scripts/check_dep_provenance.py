#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dep-provenance gate — forbid first-party git-source overrides on dev/main.

Root cause this closes (OMN-13873): omnibase_infra PR #2184 merged to dev
carrying ``[tool.uv.sources]`` git-rev overrides pinning ``omnibase-core`` /
``omnibase-spi`` to UNRELEASED commits. Every CI check passed because CI
resolved those exact commits and ran green against them — the breakage is
dependency *provenance*, not runtime behavior, so no test catches it. This is a
pure static provenance gate: it FAILS closed if any PyPI-published first-party
dependency is sourced from git instead of PyPI.

Forbidden first-party deps (both hyphen and underscore spellings):

    omnibase-core   omnibase-spi   omnibase-compat

A ``[tool.uv.sources]`` entry for any of the above with a ``git`` / ``rev`` /
``branch`` / ``tag`` key is a forbidden override and fails the gate.

``onex-change-control`` is deliberately NOT checked — it follows an
immutable-main pin release model (different from the three PyPI-released deps),
so its git pin is intentional and must remain allowed.

Escape hatch (Rule-10 style): a forbidden source line may carry an inline
comment ``# raw-override-ok: <ticket>`` with a NON-EMPTY token. This exempts the
single line. An empty token (``# raw-override-ok:`` with nothing after) does NOT
exempt — the gate still fails. Because the TOML parser drops comments, the token
is detected by reading the raw source line for each flagged package.

Exit codes:
    0  — no forbidden first-party git-source override present
    1  — a forbidden override was found (or a hard error, e.g. missing file)

This check is deterministic and offline — it makes no network calls.

Usage::

    uv run python scripts/check_dep_provenance.py
    uv run python scripts/check_dep_provenance.py --pyproject pyproject.toml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# First-party PyPI-published deps that must be resolved from PyPI, never git.
# Names are stored in canonical hyphen form; underscore spellings are
# normalized on lookup so both `omnibase-core` and `omnibase_core` are caught.
# ---------------------------------------------------------------------------

_FORBIDDEN_PACKAGES: frozenset[str] = frozenset(
    {
        "omnibase-core",
        "omnibase-spi",
        "omnibase-compat",
    }
)

# Source-override keys that indicate a git provenance (any one is forbidden for
# a first-party dep). A PyPI source has none of these.
_GIT_SOURCE_KEYS: frozenset[str] = frozenset({"git", "rev", "branch", "tag"})

# Inline escape token: `# raw-override-ok: <ticket>` with a non-empty token.
_ESCAPE_TOKEN_RE = re.compile(r"#\s*raw-override-ok:\s*(\S+)")

# ---------------------------------------------------------------------------
# [tool.uv.sources] parsing — regex-based, adapted (with attribution) from
# scripts/check-pinned-wheels.py::_parse_uv_sources. Copied rather than imported
# because that module's filename contains a hyphen (not a clean import target).
# We parse only the uv.sources block, which is sufficient for provenance.
#
# Note: the header pattern is anchored with ``^`` (start-of-line) so a commented
# ``#   [tool.uv.sources]`` example elsewhere in the file (as this repo carries
# in its dependency-guidance comments) does not shadow the real section.
# ---------------------------------------------------------------------------

_UVS_BLOCK_RE = re.compile(
    r"^\[tool\.uv\.sources\](.*?)(?=^\[|\Z)",
    re.MULTILINE | re.DOTALL,
)
_UVS_ENTRY_RE = re.compile(
    r"^(\S+)\s*=\s*\{([^}]+)\}",
    re.MULTILINE,
)
_KV_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def _normalize(pkg: str) -> str:
    """Canonicalize a package name to hyphen form for comparison."""
    return pkg.strip().strip('"').strip("'").replace("_", "-").lower()


def _uv_sources_block(text: str) -> str | None:
    """Return the raw text of the [tool.uv.sources] block, or None if absent."""
    block_m = _UVS_BLOCK_RE.search(text)
    return block_m.group(1) if block_m else None


def _parse_uv_source_entries(block: str) -> dict[str, dict[str, str]]:
    """Return {normalized_pkg: {key: value}} for [tool.uv.sources] entries."""
    sources: dict[str, dict[str, str]] = {}
    for entry_m in _UVS_ENTRY_RE.finditer(block):
        pkg = _normalize(entry_m.group(1))
        kv_str = entry_m.group(2)
        sources[pkg] = dict(_KV_RE.findall(kv_str))
    return sources


def _line_for_package(block: str, pkg: str) -> str | None:
    """Return the raw source line (with any trailing comment) declaring `pkg`."""
    for raw_line in block.splitlines():
        stripped = raw_line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        # Entry key is the text before the first '=' on the line.
        key = stripped.split("=", 1)[0]
        if _normalize(key) == pkg:
            return raw_line
    return None


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------


def find_violations(text: str) -> list[str]:
    """Return diagnostic messages for each forbidden git-source override.

    An empty list means the file is clean (exit 0). A non-empty list means the
    gate fails (exit 1). Lines carrying a valid `# raw-override-ok: <token>`
    escape are excluded.
    """
    block = _uv_sources_block(text)
    if block is None:
        # No [tool.uv.sources] block at all — nothing can be overridden.
        return []

    entries = _parse_uv_source_entries(block)
    violations: list[str] = []

    for pkg, attrs in entries.items():
        if pkg not in _FORBIDDEN_PACKAGES:
            continue
        git_keys = sorted(_GIT_SOURCE_KEYS & set(attrs))
        if not git_keys:
            # A non-git source (unusual, but not a provenance violation).
            continue

        raw_line = _line_for_package(block, pkg)
        if raw_line is not None:
            escape_m = _ESCAPE_TOKEN_RE.search(raw_line)
            if escape_m and escape_m.group(1).strip():
                # Valid non-empty escape token — this line is exempt.
                continue

        keys_desc = ", ".join(f"{k}={attrs[k]!r}" for k in git_keys)
        violations.append(
            f"{pkg}: forbidden git-source override ({keys_desc}). "
            f"First-party deps must resolve from PyPI, not git. "
            f"line: {raw_line.strip() if raw_line else '<unresolved>'}"
        )

    return violations


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pyproject",
        default="pyproject.toml",
        help="Path to pyproject.toml (default: pyproject.toml)",
    )
    args = parser.parse_args(argv)

    pyproject_path = Path(args.pyproject)
    if not pyproject_path.exists():
        print(
            f"ERROR: pyproject.toml not found: {pyproject_path}",
            file=sys.stderr,
        )
        return 1

    violations = find_violations(pyproject_path.read_text())

    if violations:
        print(
            "FAIL: forbidden first-party git-source override(s) in "
            f"{pyproject_path} [tool.uv.sources]:",
            file=sys.stderr,
        )
        for msg in violations:
            print(f"  - {msg}", file=sys.stderr)
        print(
            "\nomnibase-core / omnibase-spi / omnibase-compat are PyPI-published "
            "first-party deps and must NOT be pinned to git commits/branches/tags "
            "on dev/main. Resolve them from PyPI (release the dep first if the "
            "needed version is unpublished). If a temporary override is genuinely "
            "unavoidable, annotate the exact line with "
            "'# raw-override-ok: <ticket>' (non-empty token).",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: no forbidden first-party git-source override in "
        f"{pyproject_path} [tool.uv.sources]."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
