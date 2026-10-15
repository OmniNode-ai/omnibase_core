# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the version-floor-ahead-of-consumers check (OMN-19998).

Backs the ``check-version-floor-consumers`` pre-commit hook, the reusable
``version-drift.yml`` workflow every repository inherits, and manual runs. All
I/O happens here: the repository's pyproject at the base ref and in the tree,
each registry consumer's pyproject read from its clone at its origin default
branch (``git show origin/<default>:pyproject.toml``), and the report write
(``node_validation_report_write_effect``). The verdict is the pure
``HandlerVersionFloorConsumers``.

Consumers are read from ``--consumers-root``, a directory holding one clone per
registry repository named as in ``contracts/repo_layers.yaml``. It defaults to
the directory that holds this repository's canonical clone, which is the
registry root for a canonical clone and for every linked worktree of one. A
consumer with no clone there is unreadable, and an unreadable consumer fails a
floor raise; a pull request that raises no floor reads no consumer verdict.

Usage::

    check-version-floor-consumers                        # base: merge-base with origin/HEAD|dev|main
    check-version-floor-consumers --base-ref origin/dev --consumers-root ../clones
    check-version-floor-consumers pyproject.toml         # pre-commit staged files

Exit codes: 0 -- PASS; 1 -- FAIL/ERROR.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Final

from omnibase_core.handlers.handler_dependency_direction_cli import (
    infer_repo,
    load_layer_map,
)
from omnibase_core.handlers.handler_version_floor_consumers import (
    VALIDATOR_ID,
    HandlerVersionFloorConsumers,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.version_drift.model_consumer_pyproject import (
    ModelConsumerPyproject,
)
from omnibase_core.models.version_drift.model_version_floor_check_input import (
    ModelVersionFloorCheckInput,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

__all__ = ["load_layer_map", "main", "read_consumer"]

PYPROJECT: Final[str] = "pyproject.toml"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def default_consumers_root(root: Path) -> Path:
    """The directory holding this repository's canonical clone (the registry root)."""
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common.returncode == 0 and common.stdout.strip():
        return Path(common.stdout.strip()).parent.parent
    return root.parent


def read_consumer(consumers_root: Path, repo: str) -> ModelConsumerPyproject:
    """A consumer's pyproject at its origin default branch.

    A clone whose default branch has no pyproject.toml declares no Python
    dependency and reads as empty text; a missing clone or an unresolvable
    default branch reads as None (unreadable).
    """
    clone = consumers_root / repo
    if not clone.is_dir():
        return ModelConsumerPyproject(repo=repo, ref="absent", pyproject=None)
    head = _git(clone, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    ref = head.stdout.strip()
    if head.returncode != 0 or not ref:
        return ModelConsumerPyproject(repo=repo, ref="origin/HEAD", pyproject=None)
    if _git(clone, "cat-file", "-e", f"{ref}:{PYPROJECT}").returncode != 0:
        return ModelConsumerPyproject(repo=repo, ref=ref, pyproject="")
    shown = _git(clone, "show", f"{ref}:{PYPROJECT}")
    text = shown.stdout if shown.returncode == 0 else None
    return ModelConsumerPyproject(repo=repo, ref=ref, pyproject=text)


def _base_ref(root: Path, given: str | None) -> tuple[str | None, str | None]:
    """The base commit and an error message, one of them None."""
    if given:
        if _git(
            root, "rev-parse", "--verify", "--quiet", f"{given}^{{commit}}"
        ).returncode:
            return None, (
                f"base ref {given!r} is not in the clone; fetch it, since a floor "
                "comparison with no base is never a pass"
            )
        return given, None
    for upstream in ("origin/HEAD", "origin/dev", "origin/main"):
        merge_base = _git(root, "merge-base", "HEAD", upstream)
        if merge_base.returncode == 0 and merge_base.stdout.strip():
            return merge_base.stdout.strip(), None
    return None, (
        "no --base-ref and no merge-base with origin/HEAD, origin/dev or "
        "origin/main; pass --base-ref"
    )


def _out(line: str) -> None:
    sys.stdout.write(line + "\n")


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns 0 on PASS, 1 on FAIL/ERROR."""
    parser = argparse.ArgumentParser(
        prog="check-version-floor-consumers",
        description=(
            "Refuse a floor raise on a sibling registry package ahead of the "
            "registry consumers that install it (OMN-19998)."
        ),
    )
    parser.add_argument("filenames", nargs="*", help="Staged files (pre-commit mode).")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--repo", default=None, help="Repository name (default: inferred)"
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help="The pull request base (default: merge-base with origin/HEAD, dev or main).",
    )
    parser.add_argument(
        "--consumers-root",
        default=None,
        help="Directory of registry clones (default: the canonical clone's parent).",
    )
    parser.add_argument(
        "--report-json", default=None, help="Write the report JSON here."
    )
    parsed = parser.parse_args(argv)

    root = Path(parsed.root).resolve()
    if parsed.filenames and PYPROJECT not in {Path(f).name for f in parsed.filenames}:
        return 0
    layer_map = load_layer_map()
    repo = parsed.repo or infer_repo(root, layer_map)
    head_file = root / PYPROJECT
    if not head_file.is_file():
        _out(f"OK: {repo} has no {PYPROJECT}; it raises no floor")
        return 0

    base, error = _base_ref(root, parsed.base_ref)
    if error is not None or base is None:
        message = error or "no base ref"
        _write_report(
            parsed.report_json,
            ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (message,)),
        )
        _out(f"ERROR: {message}")
        return 1
    shown = _git(root, "show", f"{base}:{PYPROJECT}")
    base_text = shown.stdout if shown.returncode == 0 else None

    consumers_root = (
        Path(parsed.consumers_root).resolve()
        if parsed.consumers_root
        else default_consumers_root(root)
    )
    consumers = tuple(
        read_consumer(consumers_root, entry.repo)
        for entry in layer_map.repos
        if entry.repo != repo
    )
    report = HandlerVersionFloorConsumers().handle(
        ModelVersionFloorCheckInput(
            repo=repo,
            layer_map=layer_map,
            base_pyproject=base_text,
            head_pyproject=head_file.read_text("utf-8"),
            consumers=consumers,
        )
    )
    _write_report(parsed.report_json, report)
    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status == "PASS":
        _out(
            f"OK: {repo} raises no sibling floor ahead of a registry consumer "
            f"(base {base}, consumers read from {consumers_root})"
        )
        return 0
    _out(
        f"{report.overall_status}: {repo} raises a floor ahead of its consumers; land "
        "the consumer pull requests named above first"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
