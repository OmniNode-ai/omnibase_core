# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for scripts/zone_diff_filter.py (OMN-10356)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "zone_diff_filter.py"
# Make the package importable in subprocess — mirrors what uv run does.
_SRC = str(REPO_ROOT / "src")


def _run(env_override: dict[str, str], *args: str) -> int:
    import os

    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{_SRC}:{existing_pp}" if existing_pp else _SRC
    env.update(env_override)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        check=False,
    ).returncode


def test_docs_only_diff_exits_0() -> None:
    rc = _run({"ZONE_DIFF_FILTER_FAKE_DIFF": "docs/foo.md"}, "--check", "docs-only")
    assert rc == 0


def test_src_diff_exits_1() -> None:
    rc = _run(
        {"ZONE_DIFF_FILTER_FAKE_DIFF": "src/omnibase_core/foo.py"},
        "--check",
        "docs-only",
    )
    assert rc == 1


def test_mixed_zone_exits_1() -> None:
    rc = _run(
        {"ZONE_DIFF_FILTER_FAKE_DIFF": "docs/foo.md,src/omnibase_core/bar.py"},
        "--check",
        "docs-only",
    )
    assert rc == 1


def test_empty_diff_exits_0() -> None:
    # Empty diff = no production zone touched — treat as docs-only
    rc = _run({"ZONE_DIFF_FILTER_FAKE_DIFF": ""}, "--check", "docs-only")
    assert rc == 0


def test_bad_usage_exits_2() -> None:
    rc = _run({}, "--check", "unknown-mode")
    assert rc == 2
