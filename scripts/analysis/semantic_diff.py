#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI: compute AST-level semantic diff between two git refs (OMN-10375).

Usage:
    python scripts/analysis/semantic_diff.py --base origin/main --head HEAD --json

Exits 0 on completed analysis; argparse usage errors still exit non-zero.
Detected changes are advisory. Gating is opt-in via separate workflows.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from omnibase_core.analysis.consumer_graph import build_consumer_graph
from omnibase_core.analysis.semantic_diff import compute_diff
from omnibase_core.models.analysis.model_semantic_diff_report import (
    ModelSemanticDiffReport,
)
from omnibase_core.models.analysis.model_symbol_change import ModelSymbolChange


def _git_ref_exists(ref: str, repo_root: Path) -> bool:
    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def _ensure_ref_available(ref: str, repo_root: Path) -> bool:
    if _git_ref_exists(ref, repo_root):
        return True

    if ref.startswith("origin/"):
        branch = ref.removeprefix("origin/")
        subprocess.run(
            [
                "git",
                "fetch",
                "--depth=1",
                "origin",
                f"refs/heads/{branch}:refs/remotes/origin/{branch}",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    return _git_ref_exists(ref, repo_root)


def _git_changed_py_files(base: str, head: str, repo_root: Path) -> list[Path]:
    if not _ensure_ref_available(base, repo_root):
        print(  # noqa: T201
            f"warning: base ref {base!r} is unavailable; emitting empty advisory report",
            file=sys.stderr,
        )
        return []
    if not _ensure_ref_available(head, repo_root):
        print(  # noqa: T201
            f"warning: head ref {head!r} is unavailable; emitting empty advisory report",
            file=sys.stderr,
        )
        return []

    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMDR",
            f"{base}...{head}",
            "--",
            "*.py",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(  # noqa: T201
            "warning: git diff failed for "
            f"{base!r}...{head!r}: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return []
    return [repo_root / line for line in result.stdout.splitlines() if line]


def _decode_blob(raw: bytes) -> str:
    """Decode one blob the way the previous per-file ``git show`` read did.

    The old shape ran ``subprocess.run(..., text=True)``, i.e. universal
    newlines, so a CRLF or CR source arrived LF-normalised. Reading raw bytes
    out of the batch stream would silently drop that translation, so it is done
    explicitly here and pinned by a test. Decoding with ``errors="replace"`` is
    deliberately MORE forgiving than the old strict decode, which raised on a
    non-UTF-8 blob and aborted an advisory report outright.
    """
    return (
        raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    )


def _absent_response_length(out: bytes, pos: int, request: bytes) -> int | None:
    """Length of the "not resolvable" response at ``pos``, or None if it is a blob.

    ``git cat-file --batch`` answers an unresolvable name by echoing the request
    back verbatim plus a status word. Matching that echo against the request we
    actually sent is the only framing-independent way to consume the response:
    the echo carries whatever bytes the path carried, newlines included, so
    scanning for the next LF splits it and loses the FOLLOWING blob.
    """
    for status in (b" missing\n", b" ambiguous\n"):
        if out.startswith(request + status, pos):
            return len(request) + len(status)
    return None


def _git_files_at(
    repo_root: Path, requests: list[tuple[str, str]]
) -> dict[tuple[str, str], str]:
    """Read every requested ``<ref>:<path>`` blob in ONE git process.

    The previous shape spawned two ``git show`` processes per changed file, so a
    1,000-file diff paid ~2,000 process spawns and that dominated CLI runtime --
    enough, under the parallel test gate, to push the run past its per-test
    timeout. ``git cat-file --batch`` answers the whole set from a single
    process. Missing blobs yield "", matching the previous per-file behaviour.
    See OMN-15431.

    Requests are NUL-delimited (``-z``), not newline-delimited: git permits a
    newline inside a path, and a newline-framed request stream would split such
    a path into two requests and desynchronise every response after it --
    silently corrupting the content of unrelated files. The per-file ``git
    show`` shape this replaced had no such coupling, so ``-z`` is what keeps the
    batching behaviour-preserving.

    ``-z`` frames stdin ONLY; git's stdout stays LF-framed on every git version
    this repo supports (``-Z``, which also frames stdout, needs git >= 2.42 and
    the fleet runs 2.39). So responses are NOT scanned for the next LF -- an
    absent blob is answered by echoing the request VERBATIM followed by
    " missing", which re-injects the embedded newline and would burn one
    response slot per line. Each response is instead matched against the exact
    request that produced it, which is framing-independent. This is not an
    exotic case: :func:`_compute_report` asks for every changed path at BOTH
    base and head, so every added or deleted file is a missing-blob request.
    """
    if not requests:
        return {}

    payload = b"".join(f"{ref}:{rel}\0".encode() for ref, rel in requests)
    result = subprocess.run(
        ["git", "cat-file", "--batch", "-z"],
        cwd=repo_root,
        input=payload,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        # Degrade loudly. Every blob resolving to "" makes compute_diff report
        # "no semantic changes" for the WHOLE diff, which reads identically to
        # a genuinely clean diff; the per-file shape this replaced could only
        # ever lose one file at a time.
        print(  # noqa: T201
            "warning: git cat-file failed; emitting empty advisory report for "
            f"all {len(requests)} requested blobs: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}",
            file=sys.stderr,
        )
        return {}

    out = result.stdout
    sources: dict[tuple[str, str], str] = {}
    pos = 0
    for key in requests:
        ref, rel = key
        absent_len = _absent_response_length(out, pos, f"{ref}:{rel}".encode())
        if absent_len is not None:
            sources[key] = ""
            pos += absent_len
            continue
        end_of_header = out.find(b"\n", pos)
        if end_of_header == -1:
            break
        header = out[pos:end_of_header]
        pos = end_of_header + 1
        # Success is "<oid> <type> <size>"; absence was handled above.
        fields = header.split(b" ")
        try:
            size = int(fields[2])
        except (IndexError, ValueError):
            sources[key] = ""
            continue
        sources[key] = _decode_blob(out[pos : pos + size])
        pos += size + 1  # blob payload plus its trailing newline

    return sources


def _compute_report(base: str, head: str, repo_root: Path) -> ModelSemanticDiffReport:
    changed_files = _git_changed_py_files(base, head, repo_root)
    if not changed_files:
        return ModelSemanticDiffReport(
            changes=(),
            total_consumers_affected=0,
        )

    consumer_graph = build_consumer_graph(repo_root)

    all_changes: list[ModelSymbolChange] = []
    total_consumers = 0

    rel_paths = [
        file_path.relative_to(repo_root).as_posix() for file_path in changed_files
    ]
    sources = _git_files_at(
        repo_root,
        [(ref, rel) for rel in rel_paths for ref in (base, head)],
    )

    for rel in rel_paths:
        old_source = sources.get((base, rel), "")
        new_source = sources.get((head, rel), "")
        consumers = consumer_graph.get(rel, 0)
        report = compute_diff(old_source, new_source, rel, consumers)
        all_changes.extend(report.changes)
        if report.changes:
            total_consumers += consumers

    return ModelSemanticDiffReport(
        changes=tuple(all_changes),
        total_consumers_affected=total_consumers,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AST semantic diff between two git refs"
    )
    parser.add_argument("--base", required=True, help="Base git ref (e.g. origin/main)")
    parser.add_argument("--head", required=True, help="Head git ref (e.g. HEAD)")
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON report to stdout"
    )
    args = parser.parse_args()

    report = _compute_report(args.base, args.head, _REPO_ROOT)

    if args.json:
        print(json.dumps(report.model_dump(), indent=2))  # noqa: T201
    elif not report.changes:
        print("No semantic changes detected.")  # noqa: T201
    else:
        for change in report.changes:
            print(  # noqa: T201
                f"[{change.severity.upper()}] {change.kind}: {change.symbol_name} ({change.file_path})"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
