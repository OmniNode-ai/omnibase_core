# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the public-repository runner placement check (OMN-19998).

Backs the ``check-public-runner-placement`` pre-commit hook, the reusable
``version-drift.yml`` workflow every repository inherits, and manual runs. All
I/O happens here: the tracked-file listing (``node_git_file_listing_effect``),
file reads (``node_source_file_gather_effect``), the base workflows and the
baseline at the ratchet base (git), and the report write
(``node_validation_report_write_effect``). The verdict is the pure
``HandlerPublicRunnerPlacement``.

The baseline is the one omnibase_core ships in the package, so a public
repository reads it from the validator's pinned checkout and cannot edit it.

Usage::

    check-public-runner-placement --repo omnibase_infra --root ../omnibase_infra
    check-public-runner-placement --repo omnimarket --visibility private
    check-public-runner-placement .github/workflows/ci.yml     # pre-commit staged files
    check-public-runner-placement --base-ref origin/dev --baseline-ratchet-base-ref origin/dev

Exit codes: 0 -- PASS or WARN only (and any private repository); 1 -- FAIL/ERROR,
or the baseline grew.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

from omnibase_core.handlers.handler_public_runner_placement import (
    VALIDATOR_ID,
    HandlerPublicRunnerPlacement,
)
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_input import (
    ModelGitFileListingInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.version_drift.model_public_runner_baseline import (
    ModelPublicRunnerBaseline,
)
from omnibase_core.models.version_drift.model_public_runner_placement_input import (
    ModelPublicRunnerPlacementInput,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler import (
    NodeGitFileListingEffect,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["baseline_growth", "is_workflow", "main", "parse_baseline"]

DEFAULT_BASELINE: Final[Path] = (
    Path(__file__).parent.parent / "contracts" / "public_runner_placement_baseline.yaml"
)
_WORKFLOW = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$")


def is_workflow(path: str) -> bool:
    """True for a top-level file of ``.github/workflows``."""
    return bool(_WORKFLOW.match(path))


def parse_baseline(text: str | None) -> ModelPublicRunnerBaseline:
    """The baseline from the YAML text of a baseline file (None means absent)."""
    if not text:
        return ModelPublicRunnerBaseline()
    return load_yaml_content_as_model(text, ModelPublicRunnerBaseline)


def baseline_growth(
    current: ModelPublicRunnerBaseline, base: ModelPublicRunnerBaseline | None
) -> list[str]:
    """Entries the current baseline adds over the base (shrink-only ratchet).

    A base with no baseline file (None) is the introduction and adds nothing.
    """
    if base is None:
        return []
    base_keys = base.entries()
    return [
        f"baseline grew: {repo} {path} {job} is not in the base baseline"
        for repo, path, job in sorted(current.entries() - base_keys)
    ]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def gather(root: Path, filenames: list[str]) -> tuple[list[ModelSourceFile], list[str]]:
    """Repository-relative (path, source) pairs of the workflow files."""
    if filenames:
        relative = [f for f in filenames if is_workflow(f)]
    else:
        listing = NodeGitFileListingEffect().handle(
            ModelGitFileListingInput(root=root, scope="tracked")
        )
        relative = [p for p in listing.paths if is_workflow(p)]
    if not relative:
        return [], []
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(root),
            explicit_paths=[str(root / p) for p in relative],
            include_patterns=["*"],
            decode_errors="replace",
        )
    )
    prefix = str(root) + "/"
    files = [
        ModelSourceFile(path=f.path.removeprefix(prefix), source=f.source)
        for f in output.files
    ]
    errors = [
        f"{s.path.removeprefix(prefix)}: {s.reason}"
        for s in output.skipped
        if s.reason.startswith("read error:")
    ]
    return files, errors


def gather_at_ref(root: Path, ref: str) -> tuple[list[ModelSourceFile], list[str]]:
    """The workflow files of ``ref``; an unresolvable ref is an error, never a pass."""
    if _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode:
        return [], [
            f"base ref {ref!r} is not in the clone; fetch it, since a comparison "
            "with no base is never a pass"
        ]
    listing = _git(root, "ls-tree", "-r", "--name-only", ref, ".github/workflows")
    files: list[ModelSourceFile] = []
    errors: list[str] = []
    for path in listing.stdout.split("\n"):
        if not is_workflow(path):
            continue
        shown = _git(root, "show", f"{ref}:{path}")
        if shown.returncode:
            errors.append(f"{path}: git show {ref} failed: {shown.stderr.strip()}")
            continue
        files.append(ModelSourceFile(path=path, source=shown.stdout))
    return files, errors


def _baseline_at_ref(
    baseline_file: Path, ref: str
) -> tuple[ModelPublicRunnerBaseline | None, str | None]:
    """The baseline file at ``ref`` of the repository holding it; (None, None) if absent."""
    parent = baseline_file.parent
    top = _git(parent, "rev-parse", "--show-toplevel")
    if top.returncode:
        return None, f"{baseline_file} is not inside a git clone: cannot ratchet it"
    toplevel = Path(top.stdout.strip()).resolve()
    if _git(
        toplevel, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"
    ).returncode:
        return None, (
            f"ratchet base ref {ref!r} is not in the clone; fetch it, since a "
            "ratchet with no base is never a pass"
        )
    relative = baseline_file.resolve().relative_to(toplevel).as_posix()
    shown = _git(toplevel, "show", f"{ref}:{relative}")
    return (parse_baseline(shown.stdout) if shown.returncode == 0 else None), None


def _out(line: str) -> None:
    sys.stdout.write(line + "\n")


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns 0 on PASS/WARN, 1 on FAIL/ERROR or baseline growth."""
    parser = argparse.ArgumentParser(
        prog="check-public-runner-placement",
        description=(
            "Refuse a public repository adding a job that runs on a self-hosted "
            "runner (OMN-19998)."
        ),
    )
    parser.add_argument("filenames", nargs="*", help="Staged files (pre-commit mode).")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--repo",
        default=None,
        help="Repository name the baseline is keyed on (default: the root's directory name).",
    )
    parser.add_argument(
        "--visibility",
        choices=("public", "private"),
        default="public",
        help="A private repository passes; an unknown one is treated as public.",
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE),
        help="Baseline path (default: the one packaged with omnibase_core).",
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help="Fail a baselined job that is new or newly self-hosted against this ref.",
    )
    parser.add_argument(
        "--baseline-ratchet-base-ref",
        default=None,
        help="Refuse baseline entries this ref's copy of the baseline does not have.",
    )
    parser.add_argument(
        "--report-json", default=None, help="Write the report JSON here."
    )
    parsed = parser.parse_args(argv)

    root = Path(parsed.root).resolve()
    repository = parsed.repo or root.name
    baseline_file = Path(parsed.baseline)
    baseline = parse_baseline(
        baseline_file.read_text("utf-8") if baseline_file.is_file() else None
    )

    runtime_errors: list[str] = []
    if parsed.baseline_ratchet_base_ref:
        base_baseline, error = _baseline_at_ref(
            baseline_file, parsed.baseline_ratchet_base_ref
        )
        if error:
            runtime_errors.append(error)
        else:
            runtime_errors.extend(baseline_growth(baseline, base_baseline))

    files: list[ModelSourceFile] = []
    base_files: list[ModelSourceFile] | None = None
    if parsed.visibility == "public":
        files, read_errors = gather(root, parsed.filenames)
        runtime_errors.extend(read_errors)
        if parsed.base_ref:
            base_files, base_errors = gather_at_ref(root, parsed.base_ref)
            runtime_errors.extend(base_errors)
    if runtime_errors:
        _write_report(
            parsed.report_json,
            ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID, tuple(runtime_errors)
            ),
        )
        for message in runtime_errors:
            _out(f"ERROR: {message}")
        return 1

    report = HandlerPublicRunnerPlacement().handle(
        ModelPublicRunnerPlacementInput(
            repository=repository,
            public=parsed.visibility == "public",
            files=tuple(files),
            base_files=None if base_files is None else tuple(base_files),
            baseline=frozenset(
                (path, job)
                for repo, path, job in baseline.entries()
                if repo == repository
            ),
            report_stale_baseline=not parsed.filenames,
        )
    )
    _write_report(parsed.report_json, report)
    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status in ("PASS", "WARN"):
        scope = (
            f"{len(files)} workflow files scanned"
            if parsed.visibility == "public"
            else "private repository: self-hosted runners are its CI"
        )
        _out(f"OK: {repository} adds no self-hosted CI job ({scope})")
        return 0
    _out(
        f"{report.overall_status}: public repository {repository} adds a job that "
        "runs on a self-hosted runner (CI runners are for private repositories only)"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
