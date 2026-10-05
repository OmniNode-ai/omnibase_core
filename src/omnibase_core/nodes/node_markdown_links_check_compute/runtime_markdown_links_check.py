# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Offline core markdown CLI; source reads and report writes use EFFECT nodes."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Literal, cast

from omnibase_core.models.nodes.markdown_links_check.model_markdown_link_config import (
    ModelMarkdownLinkConfig,
)
from omnibase_core.models.nodes.markdown_links_check.model_markdown_link_inventory_entry import (
    ModelMarkdownLinkInventoryEntry,
)
from omnibase_core.models.nodes.markdown_links_check.model_markdown_links_check_input import (
    ModelMarkdownLinksCheckInput,
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
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_markdown_links_check_compute.handler import (
    NodeMarkdownLinksCheckCompute,
)
from omnibase_core.nodes.node_markdown_links_check_compute.matcher_markdown_links import (
    extract_headings_as_anchors,
    extract_links_from_markdown,
    is_external_link,
)
from omnibase_core.nodes.node_markdown_links_check_compute.validation_markdown_links import (
    VALIDATOR_ID,
    analyze,
    target_key,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)


def _read(
    paths: list[Path], decode_errors: Literal["strict", "replace"] = "replace"
) -> tuple[dict[str, str], list[str]]:
    if not paths:
        return {}, []
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(paths[0].parent),
            include_patterns=["*"],
            explicit_paths=[str(path) for path in paths],
            decode_errors=decode_errors,
        )
    )
    return {file.path: file.source for file in output.files}, [
        f"{item.path}: {item.reason}" for item in output.skipped
    ]


def _load_config(path: Path) -> ModelMarkdownLinkConfig:
    if not path.exists():
        return ModelMarkdownLinkConfig()
    try:
        sources, errors = _read([path], decode_errors="strict")
        if errors:
            sys.stdout.write(
                f"Warning: Could not load config from {path}: {errors[0].split('read error: ', 1)[-1]}\n"
            )
            return ModelMarkdownLinkConfig()
        data = cast(dict[str, object], json.loads(sources[str(path)]))
    except (json.JSONDecodeError, OSError) as exc:
        sys.stdout.write(f"Warning: Could not load config from {path}: {exc}\n")
        return ModelMarkdownLinkConfig()
    patterns: list[str] = []
    raw = data.get("ignorePatterns", [])
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("pattern"), str):
                pattern = cast(str, item["pattern"])
                try:
                    re.compile(pattern)
                    patterns.append(pattern)
                except re.error:
                    sys.stdout.write(f"Warning: Invalid regex pattern: {pattern}\n")
    excludes = data.get("excludeFiles", list(ModelMarkdownLinkConfig().exclude_files))
    timeout = data.get("externalTimeout", 5000)
    return ModelMarkdownLinkConfig(
        ignore_patterns=tuple(patterns),
        exclude_files=tuple(item for item in excludes if isinstance(item, str))
        if isinstance(excludes, list)
        else (),
        check_external=bool(data.get("checkExternal", False)),
        external_timeout=int(timeout) if isinstance(timeout, (int, float)) else 5000,
    )


def _discover(root: Path, config: ModelMarkdownLinkConfig) -> list[Path]:
    return [
        path
        for path in root.rglob("*.md")
        if path.is_file()
        and not any(
            fnmatch.fnmatch(str(path.relative_to(root)), pattern)
            or fnmatch.fnmatch(path.name, pattern)
            for pattern in config.exclude_files
        )
    ]


def _inventory_entry(
    path: Path, sources: dict[str, str], resolve_path: bool = True
) -> ModelMarkdownLinkInventoryEntry:
    try:
        resolved = path.resolve() if resolve_path else path
    except OSError as exc:
        return ModelMarkdownLinkInventoryEntry(
            path=str(path),
            resolved_path=str(path),
            exists=False,
            resolution_error=f"Cannot resolve path (possible circular symlink): {exc}",
        )
    try:
        exists = resolved.exists()
    except OSError as exc:
        return ModelMarkdownLinkInventoryEntry(
            path=str(path),
            resolved_path=str(resolved),
            exists=False,
            resolution_error=f"Cannot check if target exists (permission error?): {exc}",
        )
    anchors: tuple[str, ...] = ()
    if exists and resolved.suffix.lower() == ".md":
        if str(resolved) not in sources:
            new_sources, _ = _read([resolved])
            sources.update(new_sources)
        anchors = tuple(
            sorted(extract_headings_as_anchors(sources.get(str(resolved), "")))
        )
    return ModelMarkdownLinkInventoryEntry(
        path=str(path), resolved_path=str(resolved), exists=exists, anchors=anchors
    )


def build_request(
    root: Path,
    paths: list[Path],
    config_path: Path,
    cross_repo_root: Path | None,
    check_external: bool = False,
) -> tuple[ModelMarkdownLinksCheckInput, list[str]]:
    """Gather documents and target metadata before invoking the pure handler.

    The generic gather walk applies additional ignores. Explicit supplemental
    reads recover core's fnmatch-only scope, including schema and hidden paths.
    """
    config = _load_config(config_path)
    if check_external:
        config = config.model_copy(update={"check_external": True})
    selected: list[Path] = []
    if paths:
        for path in paths:
            selected.extend([path] if path.is_file() else _discover(path, config))
    else:
        selected = _discover(root, config)
    sources: dict[str, str] = {}
    if not paths and selected:
        gathered = NodeSourceFileGatherEffect().handle(
            ModelSourceFileGatherInput(
                root=str(root),
                include_patterns=["**/*.md"],
                max_file_size=0,
                exclude_patterns=list(config.exclude_files),
                decode_errors="replace",
            )
        )
        sources.update({file.path: file.source for file in gathered.files})
    errors: list[str] = []
    for path in selected:
        if str(path) not in sources:
            new_sources, new_errors = _read([path])
            sources.update(new_sources)
            errors.extend(new_errors)
    files = tuple(
        ModelSourceFile(path=str(path), source=sources.get(str(path), ""))
        for path in selected
    )
    inventory: dict[str, ModelMarkdownLinkInventoryEntry] = {}
    for file in files:
        inventory[file.path] = _inventory_entry(Path(file.path), sources)
        for link in extract_links_from_markdown(file.source, file.path):
            if is_external_link(link.url):
                continue
            if link.url.startswith("#"):
                continue
            if link.is_missing_reference:
                continue
            key = target_key(file.path, link.url, str(root))
            if key not in inventory:
                inventory[key] = _inventory_entry(Path(key), sources)
            entry = inventory[key]
            if not entry.exists and not entry.resolution_error:
                implicit = entry.resolved_path + ".md"
                inventory[implicit] = _inventory_entry(
                    Path(implicit), sources, resolve_path=False
                )
            if cross_repo_root:
                cross = cross_repo_root / link.url.split("#", 1)[0]
                inventory[str(cross)] = _inventory_entry(cross, sources)
    return ModelMarkdownLinksCheckInput(
        repo_root=str(root),
        files=files,
        config=config,
        inventory=tuple(inventory.values()),
        cross_repo_root=str(cross_repo_root) if cross_repo_root else None,
    ), errors


def _detect_root() -> Path:
    current = Path.cwd()
    return next(
        (path for path in (current, *current.parents) if (path / ".git").exists()),
        current,
    )


def _format_report(
    report: ModelValidationReport, root: Path, files: int, checked: int, skipped: int
) -> str:
    if not report.findings:
        return f"Markdown Links: PASS ({files} files, {checked} links checked, {skipped} skipped)"
    lines = [
        "MARKDOWN LINK VALIDATION FAILED",
        "=" * 60,
        "",
        f"Found {len(report.findings)} broken link(s):",
        "",
    ]
    for finding in report.findings:
        assert finding.location is not None
        path, line = finding.location.rsplit(":", 1)
        lines.extend(
            [
                f"  {Path(path).relative_to(root)}:{line}",
                f"    Link: {finding.evidence['display_link']}",
                f"    Reason: {finding.message}",
                "",
            ]
        )
    lines.extend(
        [
            "=" * 60,
            f"Summary: {files} files, {checked} links checked, {len(report.findings)} broken, {skipped} skipped",
            "",
        ]
    )
    return "\n".join(lines)


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate markdown links in ONEX repositories"
    )
    parser.add_argument(
        "filenames",
        metavar="path",
        nargs="?",
        help="Specific file or directory to check (default: entire repository)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--check-external", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--cross-repo-root", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--report-json")
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else _detect_root()
    config_path = args.config or root / ".markdown-link-check.json"
    paths = [Path(args.filenames).resolve()] if args.filenames else []
    cross = args.cross_repo_root.resolve() if args.cross_repo_root else None
    try:
        request, errors = build_request(
            root, paths, config_path, cross, args.check_external
        )
        if args.verbose:
            sys.stdout.write(
                f"Validating markdown links in: {root}\nConfiguration: {config_path}\nCheck external: {request.config.check_external}\n"
            )
            if cross:
                sys.stdout.write(f"Cross-repo root: {cross}\n")
            sys.stdout.write("\n")
        report = NodeMarkdownLinksCheckCompute().handle(request)
        _, checked, skipped, verbose = analyze(request)
        if args.verbose:
            for line in verbose:
                sys.stdout.write(line + "\n")
                for error in errors:
                    path, reason = error.split(": ", 1)
                    if line == f"Checking: {Path(path).relative_to(root)}":
                        sys.stdout.write(
                            f"  Warning: Could not read file: {reason.removeprefix('read error: ')}\n"
                        )
        saved_report = report
        if errors or not request.files:
            error_report = ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID,
                tuple(errors) if errors else (f"zero files scanned under {root}",),
            )
            saved_report = ModelValidationReport.from_findings(
                findings=report.findings + error_report.findings,
                request=ModelValidationRequestRef(profile="default"),
                validators_run=(VALIDATOR_ID,),
            )
        _write_report(args.report_json, saved_report)
        sys.stdout.write(
            _format_report(report, root, len(request.files), checked, skipped) + "\n"
        )
        if report.overall_status == "ERROR":
            return 2
        return 0 if report.overall_status == "PASS" else 1
    except (FileNotFoundError, ValueError) as exc:
        _write_report(
            args.report_json,
            ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (str(exc),)),
        )
        sys.stderr.write(f"Error: {exc}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
