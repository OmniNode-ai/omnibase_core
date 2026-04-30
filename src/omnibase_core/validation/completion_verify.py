# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import re
from pathlib import Path

from omnibase_core.models.validation.model_completion_verify_result import (
    ModelCompletionVerifyResult,
)

_BACKTICK = re.compile(r"`([A-Za-z_][\w.]*)`")
_CAMEL = re.compile(r"\b([a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*)\b")
_PASCAL_TOKEN = re.compile(r"\b([A-Z][a-zA-Z0-9]*)\b")
_DOTTED = re.compile(r"\b([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,})\b")


def _is_pascal_identifier(value: str) -> bool:
    return len(value) >= 3 and sum(char.isupper() for char in value) >= 2


def extract_identifiers(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for pat in (_BACKTICK, _CAMEL):
        for m in pat.findall(text):
            if m not in seen:
                seen.add(m)
                out.append(m)
    for m in _PASCAL_TOKEN.findall(text):
        if _is_pascal_identifier(m) and m not in seen:
            seen.add(m)
            out.append(m)
    for m in _DOTTED.findall(text):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


_PATH_PAT = re.compile(r'["`]([^"`\s]+)["`]')


def resolve_file_targets(
    text: str,
    project_root: Path,
    files_touched: list[str] | None = None,
) -> list[Path]:
    candidates: list[str] = []
    if files_touched:
        candidates.extend(files_touched)
    # Extract quoted strings that look like file paths (contain / or . or ..)
    for m in _PATH_PAT.findall(text):
        if "/" in m or m.startswith(".."):
            candidates.append(m)
    project_root = project_root.resolve()
    seen: set[Path] = set()
    out: list[Path] = []
    for c in candidates:
        p = (project_root / c).resolve()
        try:
            p.relative_to(project_root)
        except ValueError:
            raise ValueError(  # error-ok: path-escape is a boundary-validation signal, not a framework error
                f"path {c!r} escapes project root {project_root}"
            )
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def verify(
    task_id: str,
    description: str,
    files_touched: list[str] | None,
    project_root: Path,
) -> ModelCompletionVerifyResult:
    targets = resolve_file_targets(description, project_root, files_touched or [])
    if not targets:
        return ModelCompletionVerifyResult(
            task_id=task_id,
            checked_identifiers=[],
            found={},
            missing=[],
            skipped=True,
            skipped_reason="no file targets resolved",
        )
    idents = extract_identifiers(description)
    found: dict[str, str] = {}
    for ident in idents:
        for t in targets:
            if not t.is_file():
                continue
            if ident in t.read_text(errors="ignore"):
                found[ident] = str(t)
                break
    missing = [i for i in idents if i not in found]
    return ModelCompletionVerifyResult(
        task_id=task_id,
        checked_identifiers=idents,
        found=found,
        missing=missing,
        skipped=False,
        skipped_reason=None,
    )
