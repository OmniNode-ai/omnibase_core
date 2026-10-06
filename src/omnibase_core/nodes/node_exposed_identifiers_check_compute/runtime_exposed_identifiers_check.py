# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI for the exposed identifier COMPUTE gate and its EFFECT boundaries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.exposed_identifiers_check.model_exposed_identifiers_check_input import (
    ModelExposedIdentifiersCheckInput,
)
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_input import (
    ModelGitFileListingInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_exposed_identifiers_check_compute.denylist_failure import (
    DenylistError,
)
from omnibase_core.nodes.node_exposed_identifiers_check_compute.handler import (
    NodeExposedIdentifiersCheckCompute,
)
from omnibase_core.nodes.node_exposed_identifiers_check_compute.matcher_exposed_identifiers import (
    EXCLUDED_DIR_PARTS,
    EXCLUDED_SUFFIXES,
    MAX_BYTES,
    VALIDATOR_ID,
    Denylist,
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


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _error(path: str | None, message: str, exit_code: int) -> int:
    report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (message,))
    _write_report(path, report)
    sys.stderr.write(f"exposed-id-gate: ERROR {message}\n")
    return exit_code


def _gather(
    paths: list[Path], root: Path, *, lossless: bool = False
) -> tuple[list[ModelSourceFile], list[str]]:
    if not paths:
        return [], []
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(root),
            explicit_paths=[str(path) for path in paths],
            include_patterns=["**/*"],
            decode_errors="surrogateescape" if lossless else "strict",
        )
    )
    return (
        [ModelSourceFile(path=file.path, source=file.source) for file in output.files],
        [f"{file.path}: {file.reason}" for file in output.skipped],
    )


def _file_eligible(path: Path) -> bool:
    """Only filesystem eligibility lives here; path/text exclusions are pure."""
    try:
        return (
            path.is_file()
            and not path.is_symlink()
            and path.stat().st_size <= MAX_BYTES
        )
    except OSError:
        return False


def _label(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _default_root() -> Path:
    """Resolve the invocation directory through the Git EFFECT boundary."""
    return NodeGitFileListingEffect().resolve_root(Path.cwd())


def main(argv: list[str] | None = None) -> int:
    """Return 0 clean/advisory, 1 findings/runtime ERROR, or 2 configuration error."""
    parser = argparse.ArgumentParser(description="Exposed identifier gate")
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--scope", choices=("all", "diff"), default="all")
    parser.add_argument("--base-ref", default="origin/dev")
    parser.add_argument("--denylist", type=Path)
    parser.add_argument("--mode", choices=("blocking", "advisory"), default="blocking")
    parser.add_argument("--report-json")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    if args.denylist is None:
        return _error(args.report_json, "--denylist PATH is required", 2)
    root = (args.root or _default_root()).resolve()
    documents, errors = _gather([args.denylist], root)
    if errors or not documents:
        return _error(
            args.report_json,
            "; ".join(errors) or f"denylist not found: {args.denylist}",
            2,
        )
    document = documents[0].source
    try:
        denylist = Denylist.from_json(document)
    except DenylistError as exc:
        return _error(args.report_json, str(exc), 2)
    full_tree = not args.filenames and args.scope == "all"
    if args.filenames:
        # Paths belong to the invocation CWD; preserve symlinks for eligibility.
        candidates = [Path(name).absolute() for name in args.filenames]
        missing = [path for path in candidates if not path.exists()]
        if missing:
            return _error(
                args.report_json,
                "these paths do not exist: " + ", ".join(str(path) for path in missing),
                2,
            )
    else:
        try:
            listed = NodeGitFileListingEffect().handle(
                ModelGitFileListingInput(
                    root=root, scope=args.scope, base_ref=args.base_ref
                )
            )
        except (OSError, ModelOnexError) as exc:
            message = exc.message if isinstance(exc, ModelOnexError) else str(exc)
            return _error(
                args.report_json, f"could not list repository files: {message}", 1
            )
        if listed.fell_back_to_all:
            full_tree = True
            sys.stderr.write(
                f"exposed-id-gate: WARN {args.base_ref} not found; falling back to scope=all\n"
            )
        candidates = [root / name for name in listed.paths]
    paths = [path for path in candidates if _file_eligible(path)]
    files, errors = _gather(paths, root, lossless=True)
    if errors:
        return _error(args.report_json, "; ".join(errors), 1)
    files = [
        ModelSourceFile(path=_label(Path(file.path), root), source=file.source)
        for file in files
    ]
    # Binary files count as scanned in the oracle; directory/suffix exclusions do not.
    scanned = sum(
        not EXCLUDED_DIR_PARTS.intersection(Path(file.path).parts)
        and not Path(file.path).name.lower().endswith(EXCLUDED_SUFFIXES)
        for file in files
    )
    if full_tree and scanned == 0:
        return _error(args.report_json, f"zero files scanned under {root}", 1)
    report = NodeExposedIdentifiersCheckCompute().handle(
        ModelExposedIdentifiersCheckInput(files=files, denylist_json=document)
    )
    _write_report(args.report_json, report)
    sys.stdout.write(
        f"exposed-id-gate: mode={args.mode} scope={'paths' if args.filenames else args.scope} "
        f"entries={len(denylist.entries)} files_scanned={scanned} findings={len(report.findings)}\n"
    )
    for finding in report.findings:
        sys.stdout.write(f"  {finding.location}: {finding.message}\n")
    if args.mode == "advisory":
        sys.stdout.write(
            "exposed-id-gate: advisory mode -- exit 0 regardless of findings\n"
        )
        return 0
    return 1 if report.overall_status != "PASS" else 0


if __name__ == "__main__":
    sys.exit(main())
