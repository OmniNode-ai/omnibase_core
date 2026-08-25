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


def _warn_batch_read_failed(command: str, request_count: int, stderr: bytes) -> None:
    """Degrade LOUDLY when a batch git process fails.

    Every blob resolving to "" makes compute_diff report "no semantic changes"
    for the WHOLE diff, which reads identically to a genuinely clean diff; the
    per-file ``git show`` shape the batching replaced could only ever lose one
    file at a time.
    """
    print(  # noqa: T201
        f"warning: git {command} failed; emitting empty advisory report for "
        f"all {request_count} requested blobs: "
        f"{stderr.decode('utf-8', errors='replace').strip()}",
        file=sys.stderr,
    )


def _git_blob_oids_at(repo_root: Path, ref: str) -> dict[str, str] | None:
    """Map every blob path in ``ref``'s tree to its object id (None on failure).

    ``git ls-tree -r -z`` has framed its output with NUL since git 1.x, and a
    NUL-framed listing carries a path VERBATIM -- newline included -- so this is
    how a newline-bearing path is resolved without ever putting that path on a
    newline-framed request stream (see :func:`_git_files_at`).
    """
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", ref],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        _warn_batch_read_failed("ls-tree", 1, result.stderr)
        return None

    oids: dict[str, str] = {}
    # Each entry is "<mode> <type> <oid>\t<path>" terminated by NUL.
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        meta, _, path = entry.partition(b"\t")
        fields = meta.split(b" ")
        if len(fields) != 3 or fields[1] != b"blob":
            continue
        oids[path.decode("utf-8", errors="surrogateescape")] = fields[2].decode("ascii")
    return oids


def _git_blobs(repo_root: Path, oids: list[str]) -> dict[str, str] | None:
    """Read every listed blob in ONE ``git cat-file --batch`` process (None on failure).

    Requests are object ids, so the newline-framed request stream that plain
    ``--batch`` has accepted since git 1.5 is safe: an oid is 40 hex characters
    and can never contain the framing byte. The response header for a resolved
    object is ``<oid> <type> <size>`` on its own LF-terminated line, followed by
    ``<size>`` payload bytes and one trailing LF.
    """
    payload = "".join(f"{oid}\n" for oid in oids).encode("ascii")
    result = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=repo_root,
        input=payload,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        _warn_batch_read_failed("cat-file", len(oids), result.stderr)
        return None

    out = result.stdout
    blobs: dict[str, str] = {}
    pos = 0
    for oid in oids:
        end_of_header = out.find(b"\n", pos)
        if end_of_header == -1:
            break
        fields = out[pos:end_of_header].split(b" ")
        pos = end_of_header + 1
        if len(fields) != 3 or not fields[2].isdigit():
            # "<oid> missing" cannot happen for an oid ls-tree just listed, but
            # it must never desynchronise the stream if it does.
            blobs[oid] = ""
            continue
        size = int(fields[2])
        blobs[oid] = _decode_blob(out[pos : pos + size])
        pos += size + 1  # blob payload plus its trailing newline

    unanswered = [oid for oid in oids if oid not in blobs]
    if unanswered:
        _warn_batch_read_failed(
            "cat-file",
            len(unanswered),
            b"batch stream ended before every requested object was answered",
        )
        return None
    return blobs


def _git_files_at(
    repo_root: Path, requests: list[tuple[str, str]]
) -> dict[tuple[str, str], str]:
    """Read every requested ``<ref>:<path>`` blob with a fixed number of git processes.

    The original shape spawned two ``git show`` processes per changed file, so a
    1,000-file diff paid ~2,000 process spawns and that dominated CLI runtime --
    enough, under the parallel test gate, to push the run past its per-test
    timeout (OMN-15431). This shape spends one ``git ls-tree`` per distinct ref
    plus one ``git cat-file --batch`` for all blobs, regardless of file count.
    Missing blobs yield "", matching the original per-file behaviour.

    Why paths are resolved through ``ls-tree`` instead of being sent to
    ``cat-file`` as ``<ref>:<path>`` requests: git permits a newline inside a
    path, and a newline-framed request stream would split such a path into two
    requests and desynchronise every response after it -- silently corrupting
    the content of unrelated files. The NUL-framed request switches that would
    avoid this (``cat-file -z`` / ``-Z``) do NOT exist on the git 2.34.1 that
    the self-hosted runner fleet ships: the OMN-15431 batching used ``-z`` and
    every ``cat-file`` call died there with ``error: unknown switch 'z'``,
    which resolved EVERY blob to "" and made the CLI report "no semantic
    changes" for genuinely non-empty diffs (OMN-16347). ``ls-tree -r -z`` and
    plain ``cat-file --batch`` fed object ids are available on every git this
    repo runs against, so nothing here depends on the runner's git version.
    """
    if not requests:
        return {}

    oids_by_ref: dict[str, dict[str, str]] = {}
    for ref in dict.fromkeys(ref for ref, _ in requests):
        listing = _git_blob_oids_at(repo_root, ref)
        if listing is None:
            return {}
        oids_by_ref[ref] = listing

    wanted: dict[tuple[str, str], str] = {}
    for ref, rel in requests:
        oid = oids_by_ref[ref].get(rel)
        if oid is not None:
            wanted[(ref, rel)] = oid

    # A path absent at a ref is not an error: _compute_report asks for every
    # changed path at BOTH base and head, so every added or deleted file is
    # absent at one of them.
    sources: dict[tuple[str, str], str] = dict.fromkeys(requests, "")
    if not wanted:
        return sources

    blobs = _git_blobs(repo_root, list(dict.fromkeys(wanted.values())))
    if blobs is None:
        return {}
    for key, oid in wanted.items():
        sources[key] = blobs[oid]
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
