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


# ---------------------------------------------------------------------------
# OMN-16619: the classifier must stay loadable on a CI runner that has NOT
# installed the omnibase-core distribution, and a crash must never be reported
# as the verdict "not docs-only".
#
# The tests above all pass trivially in a synced dev venv (omnibase-core IS
# installed, so omnibase_core/__init__.py's importlib.metadata.version call
# succeeds). They therefore never exercised the CI condition, which is how the
# short-circuit shipped inert: on the runner the package init raised
# PackageNotFoundError, the traceback exited 1, and the workflow read 1 as a
# confident "production/mixed diff".
# ---------------------------------------------------------------------------

_ABSENT_DIST = "omnibase-core-deliberately-absent-omn16619"


def _staged_pkg(tmp_path: Path, *, init_body: str) -> Path:
    """Build a package tree mirroring what the CI job stages on disk."""
    pkg = tmp_path / "omnibase_core"
    (pkg / "enums").mkdir(parents=True)
    (pkg / "validation").mkdir(parents=True)
    (pkg / "__init__.py").write_text(init_body)
    (pkg / "enums" / "__init__.py").write_text("")
    (pkg / "validation" / "__init__.py").write_text("")
    src = REPO_ROOT / "src" / "omnibase_core"
    (pkg / "enums" / "enum_file_zone.py").write_text(
        (src / "enums" / "enum_file_zone.py").read_text()
    )
    (pkg / "validation" / "zone_classifier.py").write_text(
        (src / "validation" / "zone_classifier.py").read_text()
    )
    return tmp_path


def _run_with_pkg_root(pkg_root: Path, diff: str) -> int:
    import os

    env = os.environ.copy()
    # Shadow BOTH src/ and site-packages so the subprocess resolves
    # omnibase_core from pkg_root only — this is what the runner sees.
    env["PYTHONPATH"] = str(pkg_root)
    env["ZONE_DIFF_FILTER_FAKE_DIFF"] = diff
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check", "docs-only"],
        env=env,
        check=False,
    ).returncode


def test_uninstalled_distribution_exits_3_not_a_verdict(tmp_path: Path) -> None:
    """A package init that cannot resolve its distribution must exit 3, not 1.

    Reproduces the live failure: on the runner the real
    src/omnibase_core/__init__.py raised PackageNotFoundError and the uncaught
    traceback exited 1 — indistinguishable from a genuine non-docs verdict.
    """
    pkg_root = _staged_pkg(
        tmp_path,
        init_body=(
            "from importlib.metadata import version\n"
            f'__version__ = version("{_ABSENT_DIST}")\n'
        ),
    )
    rc = _run_with_pkg_root(pkg_root, "README.md")
    assert rc == 3, (
        f"expected internal-error code 3, got {rc}; "
        "code 1 would be read by CI as a confident 'production/mixed' verdict"
    )


def test_staged_standalone_package_classifies_docs_only(tmp_path: Path) -> None:
    """The staged layout the CI job builds must classify a README-only diff."""
    pkg_root = _staged_pkg(tmp_path, init_body="")
    assert _run_with_pkg_root(pkg_root, "README.md") == 0


def test_staged_standalone_package_still_rejects_production(tmp_path: Path) -> None:
    """Staging must not weaken the verdict — mixed diffs still exit 1."""
    pkg_root = _staged_pkg(tmp_path, init_body="")
    assert _run_with_pkg_root(pkg_root, "README.md,src/omnibase_core/x.py") == 1
