# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the merge-queue parity check (OMN-19998).

Backs the ``check-merge-queue-parity`` pre-commit hook, the reusable
``version-drift.yml`` workflow every repository inherits, and manual runs. All
I/O happens here: the tracked-file listing (``node_git_file_listing_effect``),
file reads (``node_source_file_gather_effect``), the baseline YAML at the tree
and at the ratchet base, and the report write
(``node_validation_report_write_effect``). The verdict is the pure
``HandlerMergeQueueParity``.

Usage::

    check-merge-queue-parity                              # every workflow in the tree
    check-merge-queue-parity --root ../omnibase_infra
    check-merge-queue-parity .github/workflows/ci.yml     # pre-commit staged files
    check-merge-queue-parity --ratchet-base-ref origin/dev --report-json r.json

Exit codes: 0 -- PASS or WARN only; 1 -- FAIL/ERROR, or the baseline grew.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Final

from omnibase_core.handlers.handler_merge_queue_parity import (
    VALIDATOR_ID,
    HandlerMergeQueueParity,
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
from omnibase_core.models.version_drift.model_merge_queue_parity_baseline import (
    ModelMergeQueueParityBaseline,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_baseline_entry import (
    ModelMergeQueueParityBaselineEntry,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_input import (
    ModelMergeQueueParityInput,
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
from omnibase_core.validation.checker_workflow_selection import (
    is_workflow,
    load_workflow_rule,
)

__all__ = ["is_workflow", "load_workflow_rule", "main", "parse_baseline"]

DEFAULT_BASELINE: Final[str] = ".onex_ratchets/merge_queue_parity_baseline.yaml"


def parse_baseline(text: str | None) -> tuple[ModelMergeQueueParityBaselineEntry, ...]:
    """Baseline entries from the YAML text of a baseline file (None means absent)."""
    if not text:
        return ()
    return load_yaml_content_as_model(text, ModelMergeQueueParityBaseline).violations


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


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def baseline_growth(
    current: tuple[ModelMergeQueueParityBaselineEntry, ...],
    base: tuple[ModelMergeQueueParityBaselineEntry, ...] | None,
) -> list[str]:
    """Entries the current baseline adds over the base (shrink-only ratchet).

    A base with no baseline file (None) is the introduction and adds nothing.
    """
    if base is None:
        return []
    base_keys = {entry.key() for entry in base}
    return [
        f"baseline grew: {e.path} {e.job} {e.rule.value} is not in the base baseline"
        for e in current
        if e.key() not in base_keys
    ]


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
        prog="check-merge-queue-parity",
        description=(
            "Refuse a job the merge queue runs and pull request CI skips (OMN-19998)."
        ),
    )
    parser.add_argument("filenames", nargs="*", help="Staged files (pre-commit mode).")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--baseline",
        default=DEFAULT_BASELINE,
        help=f"Baseline path relative to --root (default: {DEFAULT_BASELINE})",
    )
    parser.add_argument(
        "--ratchet-base-ref",
        default=None,
        help="Refuse baseline entries this ref's baseline does not have.",
    )
    parser.add_argument(
        "--report-json", default=None, help="Write the report JSON here."
    )
    parsed = parser.parse_args(argv)

    root = Path(parsed.root).resolve()
    files, read_errors = gather(root, parsed.filenames)
    baseline_file = root / parsed.baseline
    baseline = parse_baseline(
        baseline_file.read_text("utf-8") if baseline_file.is_file() else None
    )

    runtime_errors = list(read_errors)
    if parsed.ratchet_base_ref:
        ref = parsed.ratchet_base_ref
        if _git(
            root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"
        ).returncode:
            runtime_errors.append(
                f"ratchet base ref {ref!r} is not in the clone; fetch it, since a "
                "ratchet with no base is never a pass"
            )
        else:
            shown = _git(root, "show", f"{ref}:{parsed.baseline}")
            base = parse_baseline(shown.stdout) if shown.returncode == 0 else None
            runtime_errors.extend(baseline_growth(baseline, base))
    if runtime_errors:
        report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(runtime_errors)
        )
        _write_report(parsed.report_json, report)
        for message in runtime_errors:
            _out(f"ERROR: {message}")
        return 1

    report = HandlerMergeQueueParity().handle(
        ModelMergeQueueParityInput(
            files=tuple(files),
            baseline=baseline,
            report_stale_baseline=not parsed.filenames,
        )
    )
    _write_report(parsed.report_json, report)
    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status in ("PASS", "WARN"):
        _out(
            "OK: pull request CI runs every job the merge queue runs, outside the "
            f"baseline ({len(files)} workflow files scanned)"
        )
        return 0
    _out(
        f"{report.overall_status}: the merge queue runs a job pull request CI skips; "
        "a merge-queue-only failure is possible"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
