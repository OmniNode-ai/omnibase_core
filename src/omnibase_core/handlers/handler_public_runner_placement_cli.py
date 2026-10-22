# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the public-repository runner placement check (OMN-19998).

Backs the ``check-public-runner-placement`` pre-commit hook, the reusable
``version-drift.yml`` workflow every repository inherits, and manual runs. All
I/O happens here: the tracked-file listing (``node_git_file_listing_effect``),
file reads (``node_source_file_gather_effect``) and the report write
(``node_validation_report_write_effect``). The verdict is the pure
``HandlerPublicRunnerPlacement``.

There is no baseline and no base comparison (OMN-21280): every job of a public
repository that can run on a self-hosted runner fails, whenever it was added.

Usage::

    check-public-runner-placement --repo omnibase_infra --root ../omnibase_infra
    check-public-runner-placement --repo omnimarket --visibility private
    check-public-runner-placement .github/workflows/ci.yml     # pre-commit staged files

Exit codes: 0 -- PASS (and any private repository); 1 -- FAIL/ERROR.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

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

__all__ = ["is_workflow", "main"]

_WORKFLOW = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$")


def is_workflow(path: str) -> bool:
    """True for a top-level file of ``.github/workflows``."""
    return bool(_WORKFLOW.match(path))


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
        prog="check-public-runner-placement",
        description=(
            "Refuse every job of a public repository that can run on a "
            "self-hosted runner (OMN-19998, OMN-21280)."
        ),
    )
    parser.add_argument("filenames", nargs="*", help="Staged files (pre-commit mode).")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--repo",
        default=None,
        help="Repository name the findings name (default: the root's directory name).",
    )
    parser.add_argument(
        "--visibility",
        choices=("public", "private"),
        default="public",
        help="A private repository passes; an unknown one is treated as public.",
    )
    parser.add_argument(
        "--report-json", default=None, help="Write the report JSON here."
    )
    parsed = parser.parse_args(argv)

    root = Path(parsed.root).resolve()
    repository = parsed.repo or root.name

    files: list[ModelSourceFile] = []
    if parsed.visibility == "public":
        files, read_errors = gather(root, parsed.filenames)
        if read_errors:
            _write_report(
                parsed.report_json,
                ModelValidationReport.from_runtime_errors(
                    VALIDATOR_ID, tuple(read_errors)
                ),
            )
            for message in read_errors:
                _out(f"ERROR: {message}")
            return 1

    report = HandlerPublicRunnerPlacement().handle(
        ModelPublicRunnerPlacementInput(
            repository=repository,
            public=parsed.visibility == "public",
            files=tuple(files),
        )
    )
    _write_report(parsed.report_json, report)
    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status == "PASS":
        scope = (
            f"{len(files)} workflow files scanned"
            if parsed.visibility == "public"
            else "private repository: self-hosted runners are its CI"
        )
        _out(f"OK: {repository} has no self-hosted CI job ({scope})")
        return 0
    _out(
        f"{report.overall_status}: public repository {repository} has a job that "
        "can run on a self-hosted runner (CI runners are for private repositories only)"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
