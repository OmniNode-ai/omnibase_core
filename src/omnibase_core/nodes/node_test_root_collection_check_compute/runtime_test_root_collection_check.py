# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Repository discovery runtime; all content reads and writes use EFFECT nodes."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

from omnibase_core.enums.enum_ignore_pattern_source import EnumTraversalMode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.test_root_collection_check.model_test_root_collection_check_config import (
    ModelTestRootCollectionCheckConfig,
)
from omnibase_core.models.nodes.test_root_collection_check.model_test_root_collection_check_input import (
    ModelTestRootCollectionCheckInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_test_root_collection_check_compute.handler import (
    NodeTestRootCollectionCheckCompute,
)
from omnibase_core.nodes.node_test_root_collection_check_compute.matcher_test_root_collection import (
    CI_WORKFLOW,
    SELECTOR_FILE,
    VALIDATOR_ID,
    collected_roots,
    selector_from_source,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

PASS_MESSAGE = (
    "OK: every tests/ directory is reachable by a wired pytest invocation, the "
    "full suite inherits pyproject testpaths, and every collocated root is "
    "selector-reachable."
)
FAIL_MESSAGE = "FAIL: test-collection defect(s) detected (OMN-15378/OMN-15410 class):"


def _read_paths(
    root: Path, paths: list[Path]
) -> tuple[list[ModelSourceFile], list[str]]:
    """Read precisely these configuration dependencies through the EFFECT."""
    if not paths:
        return [], []
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(root),
            explicit_paths=[str(path) for path in paths],
            include_patterns=["*"],
        )
    )
    files = [
        ModelSourceFile(
            path=Path(file.path).relative_to(root).as_posix(), source=file.source
        )
        for file in output.files
    ]
    errors = [
        f"{skipped.path}: {skipped.reason}"
        for skipped in output.skipped
        if skipped.reason.startswith("read error:")
    ]
    return files, errors


def gather_request(
    root: Path,
    filenames: list[str] | None = None,
    config: ModelTestRootCollectionCheckConfig | None = None,
) -> tuple[ModelTestRootCollectionCheckInput, int, list[str]]:
    """Discover the original script's facts; pytest collection is not needed.

    Staged filenames trigger a whole-repository check because reachability and
    CI wiring depend on files beyond the staged set. Required workflow content
    uses explicit gathering since the general source walker excludes .github.
    """
    root = root.resolve()
    effective_config = (
        config if config is not None else ModelTestRootCollectionCheckConfig()
    )
    gather = NodeSourceFileGatherEffect()
    if filenames:
        paths = [Path(name).resolve() for name in filenames]
        files, errors = _read_paths(root, paths)
    else:
        output = gather.handle(
            ModelSourceFileGatherInput(
                root=str(root),
                include_patterns=["pyproject.toml"],
                traversal_mode=EnumTraversalMode.FLAT,
                max_file_size=0,
            )
        )
        files = [
            ModelSourceFile(
                path=Path(file.path).relative_to(root).as_posix(), source=file.source
            )
            for file in output.files
        ]
        errors = [
            f"{skipped.path}: {skipped.reason}"
            for skipped in output.skipped
            if skipped.reason.startswith(("read error:", "error checking file size:"))
        ]
    dependencies = [root / "pyproject.toml", root / SELECTOR_FILE, root / CI_WORKFLOW]
    workflows = root / ".github/workflows"
    dependencies.extend(sorted(workflows.glob("*.yml")))
    dependencies.extend(sorted(workflows.glob("*.yaml")))
    dependencies.extend(
        root / workflow for workflow in effective_config.standalone_projects.values()
    )
    present = {file.path for file in files}
    paths = sorted(
        {
            path
            for path in dependencies
            if path.is_file() and path.relative_to(root).as_posix() not in present
        }
    )
    additional, read_errors = _read_paths(root, paths)
    files.extend(additional)
    errors.extend(read_errors)
    sources = {file.path: file.source for file in files}
    directories = {
        path.relative_to(root).as_posix()
        for path in root.rglob("tests")
        if path.is_dir()
    }
    test_files: set[str] = set()
    for directory in directories:
        test_files.update(
            path.relative_to(root).as_posix()
            for path in (root / directory).rglob("test_*.py")
        )
    try:
        roots = collected_roots(sources.get("pyproject.toml"), str(root))
    except (ModelOnexError, tomllib.TOMLDecodeError, AttributeError, TypeError):
        roots = ()
    directories.update(path.rstrip("/") for path in roots if (root / path).is_dir())
    return (
        ModelTestRootCollectionCheckInput(
            files=files,
            directories=tuple(sorted(directories)),
            test_files=tuple(sorted(test_files)),
            standalone_pyprojects=tuple(
                f"{project}/pyproject.toml"
                for project in effective_config.standalone_projects
                if (root / project / "pyproject.toml").is_file()
            ),
            selector=selector_from_source(sources.get(SELECTOR_FILE), str(root)),
            config=effective_config,
            root_label=str(root),
        ),
        len(files) + len(test_files),
        errors,
    )


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """Run the same 0/1 gate as the infra oracle with canonical JSON output."""
    parser = argparse.ArgumentParser(prog="check-test-root-collection")
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("--root", default=".")
    parser.add_argument("--report-json", default=None)
    parser.add_argument(
        "--config",
        default=None,
        help="Typed standalone-project/debt configuration JSON",
    )
    parsed = parser.parse_args(argv)
    root = Path(parsed.root)
    config: ModelTestRootCollectionCheckConfig | None = None
    runtime_errors: list[str] = []
    if parsed.config is not None:
        config_path = Path(parsed.config).resolve()
        gathered = NodeSourceFileGatherEffect().handle(
            ModelSourceFileGatherInput(
                root=str(config_path.parent),
                explicit_paths=[str(config_path)],
                include_patterns=["*"],
            )
        )
        runtime_errors.extend(
            f"{skipped.path}: {skipped.reason}" for skipped in gathered.skipped
        )
        if gathered.files:
            try:
                config = ModelTestRootCollectionCheckConfig.model_validate_json(
                    gathered.files[0].source
                )
            except ValueError as exc:
                runtime_errors.append(str(exc))
    request, scanned, read_errors = gather_request(root, parsed.filenames, config)
    runtime_errors.extend(read_errors)
    if not parsed.filenames and scanned == 0:
        runtime_errors.append(
            f"zero files scanned under {root}: a full-tree run that scans nothing is ERROR, never PASS"
        )
    if runtime_errors:
        report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(runtime_errors)
        )
    else:
        report = NodeTestRootCollectionCheckCompute().handle(request)
    _write_report(parsed.report_json, report)
    if report.overall_status == "PASS":
        sys.stdout.write(PASS_MESSAGE + "\n")
        return 0
    if report.overall_status == "ERROR":
        for finding in report.findings:
            sys.stdout.write(f"ERROR: {finding.message}\n")
    else:
        sys.stdout.write(FAIL_MESSAGE + "\n")
        for finding in report.findings:
            sys.stdout.write(f"  - {finding.message}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
