# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-23012: a dependency refresh cannot upgrade the linter or the type checker.

``ruff`` and ``pyright`` decide what "clean" means here, so a range wide enough
for ``uv lock`` to upgrade either one lets a refresh change the verdict on an
unchanged tree. Measured 2026-11-07 on dev at 127140736, same tree both times:

* ruff 0.14.14 -- "All checks passed", 8350 files already formatted;
* ruff 0.17.4 -- 1009 errors, 9 files would be reformatted (0.17's formatter
  wraps a lambda body in parentheses);
* pyright 1.1.408 -- passes;
* pyright 1.1.414 -- fails on four diagnostics it did not previously report.

The 0.47.69 release cut (omnibase_core#2273) changes nothing but ``uv.lock``,
which re-resolved both tools inside the old ranges; every red on it is those two
causes or an echo of them.

These tests fail on a tree whose bounds admit another minor, which is what the
merge base looks like.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
LOCK = ROOT / "uv.lock"

#: Each tool, with the exclusive upper bound its requirement must carry and the
#: version the tree is measured clean under.
BOUNDED = {
    "ruff": ("<0.15.0", "0.14.14"),
    "pyright": ("<1.1.409", "1.1.408"),
    # OMN-23015: the same refresh took mypy from 1.19.1 to 2.4.1, and strict
    # mypy 2.x reports "object" not callable in cli_bootstrap.py and an
    # unreachable statement in model_enhanced_tool_collection.py.
    "mypy": ("<1.20.0", "1.19.1"),
}


def _requirements() -> list[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    groups = data.get("dependency-groups") or {}
    optional = (data.get("project") or {}).get("optional-dependencies") or {}
    out: list[str] = list((data.get("project") or {}).get("dependencies") or [])
    for block in (groups, optional):
        for entries in block.values():
            if isinstance(entries, list):
                out.extend(str(e) for e in entries)
    return out


def _requirement(tool: str) -> str:
    named = [r for r in _requirements() if r.split(">=")[0].strip().strip('"') == tool]
    assert named, f"{tool} is not a declared requirement of this project"
    return named[0]


def _locked(tool: str) -> str:
    """The version uv.lock pins, read from the package's own block."""
    lines = LOCK.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip() == f'name = "{tool}"':
            for follow in lines[i + 1 : i + 4]:
                if follow.startswith("version = "):
                    return follow.split("=", 1)[1].strip().strip('"')
    raise AssertionError(f"uv.lock names no version for {tool}")


def test_each_tool_requirement_carries_the_narrow_upper_bound() -> None:
    """Without it, `uv lock` may upgrade the tool and redefine clean."""
    for tool, (bound, _) in BOUNDED.items():
        requirement = _requirement(tool)
        assert bound in requirement, (
            f"{tool} is declared as {requirement!r}, which admits a version past "
            f"{bound}: a dependency refresh can then upgrade it and change this "
            "repository's verdict on an unchanged tree"
        )


def test_the_lock_resolves_the_version_the_tree_is_clean_under() -> None:
    """A narrowed bound with a stale lock still installs the newer tool."""
    for tool, (_, expected) in BOUNDED.items():
        assert _locked(tool) == expected, (
            f"uv.lock pins {tool} {_locked(tool)}, not the {expected} this tree is "
            "measured clean under"
        )
