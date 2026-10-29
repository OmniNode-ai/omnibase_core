# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the cross-repo Kafka boundary parity check (OMN-20074)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from omnibase_core.models.nodes.boundary_parity.model_boundary_parity_input import (
    ModelBoundaryParityInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.nodes.node_cross_repo_boundary_check_effect.handler_boundary_parity import (
    HandlerBoundaryParity,
    format_report,
    load_boundary_manifest,
    load_manifest_yaml,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Gather declared files and run the parity CLI."""
    parser = argparse.ArgumentParser(
        description="Check cross-repo Kafka boundary parity"
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="Path to kafka_boundaries.yaml manifest (default: bundled in package)",
    )
    parser.add_argument(
        "--repos-root",
        type=str,
        required=True,
        help="Root directory containing bare repo clones",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON instead of human-readable text",
    )
    args = parser.parse_args(argv)
    manifest_path = Path(args.manifest) if args.manifest else None
    repos_root = Path(args.repos_root)
    if manifest_path is not None and not manifest_path.is_file():
        sys.stderr.write(f"ERROR: Manifest not found: {manifest_path}\n")
        return 1
    if not repos_root.is_dir():
        sys.stderr.write(f"ERROR: Repos root not found: {repos_root}\n")
        return 1
    manifest_yaml = (
        manifest_path.read_text(encoding="utf-8")
        if manifest_path
        else load_manifest_yaml()
    )
    entries = load_boundary_manifest(manifest_yaml)
    paths = {
        f"{repo}/{file}": str((repos_root / repo / file).absolute())
        for entry in entries
        for repo, file in (
            (entry.producer_repo, entry.producer_file),
            (entry.consumer_repo, entry.consumer_file),
        )
    }
    gathered = (
        NodeSourceFileGatherEffect().handle(
            ModelSourceFileGatherInput(
                root=str(repos_root),
                explicit_paths=list(paths.values()),
                include_patterns=["*"],
                decode_errors="replace",
            )
        )
        if paths
        else None
    )
    if gathered is not None:
        for skipped in gathered.skipped:
            if skipped.reason != "not a file":
                sys.stderr.write(f"ERROR: {skipped.path}: {skipped.reason}\n")
                return 1
    texts = {file.path: file.source for file in gathered.files} if gathered else {}
    report = HandlerBoundaryParity().handle(
        ModelBoundaryParityInput(
            boundaries=entries,
            files=[
                ModelSourceFile(path=key, source=texts[path])
                for key, path in paths.items()
                if path in texts
            ],
            now=datetime.now(tz=UTC),
        )
    )
    for entry in report.pending_in_grace:
        sys.stdout.write(
            f"  PENDING (grace): {entry.topic_name} "
            f"({entry.producer_repo} -> {entry.consumer_repo}) "
            f"— {entry.pending_reason or 'no reason given'}\n"
        )
    if args.json_output:
        output: dict[str, object] = {
            "total": len(report.results),
            "ok": sum(1 for r in report.results if r.producer_ok and r.consumer_ok),
            "mismatches": report.mismatch_count,
            "boundaries": [
                {
                    "topic": r.boundary.topic_name,
                    "producer_repo": r.boundary.producer_repo,
                    "consumer_repo": r.boundary.consumer_repo,
                    "producer_ok": r.producer_ok,
                    "consumer_ok": r.consumer_ok,
                    "error": r.error,
                }
                for r in report.results
            ],
        }
        sys.stdout.write(json.dumps(output, indent=2) + "\n")
    else:
        sys.stdout.write(format_report(report) + "\n")
    return 1 if report.has_mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
