# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared CLI runtime of the baselined source-finding hooks (OMN-21433).

Backs ``check-no-dict-any`` and ``check-no-backward-compat``. All I/O happens
here, at the CLI boundary: file discovery and reads, the baseline read and write.
The verdict is the pure ``HandlerFindingBaseline``.

Options shared by every hook that uses it::

    <hook> [files ...] [--dir DIR ...] [--baseline FILE] [--write-baseline]

``--baseline FILE`` compares findings with the committed baseline: a finding not in
it fails, an entry with no finding fails as stale. ``--write-baseline`` creates the
file when absent and afterwards only shrinks it; it refuses a write that would add
an entry. Without ``--baseline`` every finding fails. Files (pre-commit passes the
staged filenames) judge only the entries of those files for staleness; ``--dir``
judges every entry under the directory.

Exit codes: 0 -- clean or within the baseline; 1 -- a finding outside the baseline,
a stale entry, a refused write or an unreadable input.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_finding_baseline import HandlerFindingBaseline
from omnibase_core.models.finding_baseline.model_finding_baseline import (
    ModelFindingBaseline,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_input import (
    ModelFindingBaselineInput,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_scope import (
    ModelFindingBaselineScope,
)
from omnibase_core.models.finding_baseline.model_finding_detect_result import (
    ModelFindingDetectResult,
)
from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["run_baselined_hook"]

RULE_FILE_ERROR: Final[str] = "file-error"


def _out(line: str) -> None:
    sys.stdout.write(line + "\n")


def _label(path: Path) -> str:
    """Repository-relative posix label: what a baseline entry records."""
    text = path.as_posix()
    if path.is_absolute():
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return text
    return text.removeprefix("./")


def _file_error(path: str, message: str) -> ModelSourceFinding:
    return ModelSourceFinding(
        path=path,
        line=0,
        rule=RULE_FILE_ERROR,
        text="",
        message=message,
        baselinable=False,
    )


def _read(
    path: Path, encodings: Sequence[str], max_bytes: int | None
) -> str | ModelSourceFinding:
    label = _label(path)
    try:
        size = path.stat().st_size
        if max_bytes is not None and size > max_bytes:
            return _file_error(label, f"File too large ({size} bytes), skipping")
        data = path.read_bytes()
    except OSError as exc:
        return _file_error(label, f"OS/IO error reading file - {exc}")
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return _file_error(
        label,
        "Unable to decode file with any supported encoding "
        f"(tried: {', '.join(encodings)})",
    )


def _collect(
    files: Sequence[str], dirs: Sequence[str], skip_dir_parts: frozenset[str]
) -> tuple[list[Path], list[ModelSourceFinding]]:
    errors: list[ModelSourceFinding] = []
    found: list[Path] = []
    for name in files:
        path = Path(name)
        if not path.exists():
            errors.append(_file_error(_label(path), "File not found"))
        elif path.is_dir():
            dirs = [*dirs, name]
        elif path.suffix == ".py":
            found.append(path)
    for name in dirs:
        directory = Path(name)
        if not directory.is_dir():
            errors.append(
                _file_error(
                    _label(directory), "Directory does not exist or is not a directory"
                )
            )
            continue
        found.extend(
            py
            for py in directory.rglob("*.py")
            if not skip_dir_parts.intersection(py.parts)
        )
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in found:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique, errors


def _load_baseline(path: Path, hook_id: str) -> ModelFindingBaseline | None:
    """The baseline document, or None when the file is absent; raises on a bad one."""
    if not path.is_file():
        return None
    baseline = load_yaml_content_as_model(
        path.read_text(encoding="utf-8"), ModelFindingBaseline
    )
    if baseline.hook != hook_id:
        raise ModelOnexError(
            message=f"{path} is the baseline of hook {baseline.hook!r}, not {hook_id!r}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return baseline


def run_baselined_hook(
    argv: Sequence[str] | None,
    *,
    hook_id: str,
    description: str,
    detect: Callable[[tuple[ModelSourceFile, ...]], ModelFindingDetectResult],
    remediation: str,
    default_dirs: Sequence[str] = (),
    encodings: Sequence[str] = ("utf-8",),
    max_bytes: int | None = None,
    skip_dir_parts: frozenset[str] = frozenset(),
) -> int:
    """Run one hook: collect, detect, then compare with or write the baseline."""
    parser = argparse.ArgumentParser(prog=hook_id, description=description)
    parser.add_argument("files", nargs="*", help="Python files (pre-commit mode).")
    parser.add_argument(
        "-d",
        "--dir",
        action="append",
        dest="directories",
        default=[],
        help="Directory to scan recursively (repeatable).",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        metavar="FILE",
        help="Committed shrink-only baseline; a finding outside it fails.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Create the baseline when absent; afterwards only shrink it.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parsed = parser.parse_args(list(argv) if argv is not None else None)
    if parsed.write_baseline and parsed.baseline is None:
        parser.error("--write-baseline needs --baseline FILE")

    files: list[str] = list(parsed.files)
    dirs: list[str] = list(parsed.directories)
    if not files and not dirs:
        if not default_dirs:
            _out("Error: Must provide either files or directories to scan")
            return 1
        dirs = list(default_dirs)

    paths, findings = _collect(files, dirs, skip_dir_parts)
    sources: list[ModelSourceFile] = []
    for path in paths:
        text = _read(path, encodings, max_bytes)
        if isinstance(text, ModelSourceFinding):
            findings.append(text)
        else:
            sources.append(ModelSourceFile(path=_label(path), source=text))
    result = detect(tuple(sources))
    findings = [*findings, *result.findings]
    scope = ModelFindingBaselineScope(
        files=tuple(_label(p) for p in paths),
        dirs=tuple("" if _label(Path(d)) == "." else _label(Path(d)) for d in dirs),
    )

    handler = HandlerFindingBaseline()
    baseline_path = Path(parsed.baseline) if parsed.baseline is not None else None
    try:
        baseline = (
            _load_baseline(baseline_path, hook_id)
            if baseline_path is not None
            else None
        )
    except (OSError, ValueError, ModelOnexError) as exc:
        _out(f"ERROR: cannot read baseline {parsed.baseline}: {exc}")
        return 1

    if parsed.write_baseline and baseline_path is not None:
        return _write_baseline(
            handler, hook_id, baseline_path, baseline, findings, scope
        )

    if baseline_path is not None and baseline is None:
        _out(
            f"NOTE: baseline {parsed.baseline} does not exist; every finding fails. "
            "Run the hook with --write-baseline to create it."
        )
    report = handler.handle(
        ModelFindingBaselineInput(
            hook_id=hook_id,
            findings=tuple(findings),
            baseline=baseline,
            scope=scope,
            remediation=remediation,
        )
    )
    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status in ("PASS", "WARN"):
        _out(f"OK: {hook_id} passed ({len(sources)} files checked)")
        return 0
    _out(f"FAILED: {hook_id}; see the findings above")
    _out(remediation)
    return 1


def _write_baseline(
    handler: HandlerFindingBaseline,
    hook_id: str,
    path: Path,
    baseline: ModelFindingBaseline | None,
    findings: Sequence[ModelSourceFinding],
    scope: ModelFindingBaselineScope,
) -> int:
    if baseline is None:
        shrink = handler.shrink(findings, (), scope)
        if shrink.unbaselinable:
            return _refuse_unbaselinable(shrink.unbaselinable)
        created = handler.create(hook_id, findings)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(handler.render(created), encoding="utf-8")
        _out(f"WROTE: {path} with {len(created.entries)} entries")
        return 0
    shrink = handler.shrink(findings, baseline.entries, scope)
    if shrink.unbaselinable:
        return _refuse_unbaselinable(shrink.unbaselinable)
    if shrink.added:
        for finding in shrink.added:
            _out(
                f"REFUSED: --write-baseline would add an entry: {finding.path} "
                f"[{finding.rule}] {finding.text!r}"
            )
        _out(f"{path} was not written; a baseline only shrinks")
        return 1
    shrunk = baseline.model_copy(update={"entries": shrink.kept})
    path.write_text(handler.render(shrunk), encoding="utf-8")
    _out(
        f"WROTE: {path} shrunk from {len(baseline.entries)} to "
        f"{len(shrunk.entries)} entries"
    )
    return 0


def _refuse_unbaselinable(findings: Sequence[ModelSourceFinding]) -> int:
    for finding in findings:
        _out(f"ERROR: {finding.path}: {finding.message}")
    _out("REFUSED: an unreadable input cannot be baselined; nothing was written")
    return 1
