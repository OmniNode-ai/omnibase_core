# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cross-repo Kafka boundary parity from onex_change_control (OMN-20074).

The handler is pure over declared boundaries, source snapshots and an explicit
clock instant. The CLI reads sources through NodeSourceFileGatherEffect.
The source's --check-schemas is not ported: the composite action never passed it.
"""

from __future__ import annotations

import argparse
import importlib.resources
import json
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.boundary_parity.model_boundary_parity_input import (
    ModelBoundaryParityInput,
)
from omnibase_core.models.nodes.boundary_parity.model_boundary_parity_report import (
    ModelBoundaryParityReport,
)
from omnibase_core.models.nodes.boundary_parity.model_boundary_parity_result import (
    ModelBoundaryParityResult,
)
from omnibase_core.models.nodes.boundary_parity.model_kafka_boundary_entry import (
    ModelKafkaBoundaryEntry,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

PENDING_GRACE_PERIOD_DAYS: Final[int] = 14
_TOPIC_MIN_SEGMENTS: Final[int] = 4
MANIFEST_RESOURCE: Final[str] = "kafka_boundaries.yaml"


def load_manifest_yaml() -> str:
    """Read the byte-for-byte OCC manifest packaged with the contracts."""
    return (
        importlib.resources.files("omnibase_core.contracts")
        / "boundaries"
        / MANIFEST_RESOURCE
    ).read_text(encoding="utf-8")


def load_boundary_manifest(manifest_yaml: str) -> list[ModelKafkaBoundaryEntry]:
    """Parse the manifest with the source's defaults and no duplicate keys."""
    data = load_yaml_mapping_no_duplicates(manifest_yaml, source=MANIFEST_RESOURCE)
    if "boundaries" not in data:
        raise ModelOnexError(
            message="Invalid manifest: missing 'boundaries' key",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )
    items = cast("list[dict[str, object]]", data["boundaries"])
    entries: list[ModelKafkaBoundaryEntry] = []
    for item in items:
        entries.append(
            ModelKafkaBoundaryEntry.model_validate(
                {
                    "topic_name": item["topic_name"],
                    "producer_repo": item["producer_repo"],
                    "consumer_repo": item["consumer_repo"],
                    "producer_file": item["producer_file"],
                    "consumer_file": item["consumer_file"],
                    "topic_pattern": item["topic_pattern"],
                    "event_schema": item.get("event_schema", ""),
                    "status": item.get("status", "active"),
                    "pending_since": item.get("pending_since", ""),
                    "pending_reason": item.get("pending_reason", ""),
                }
            )
        )
    return entries


def check_file_for_topic(
    source: str | None,
    topic_pattern: str,
    topic_name: str,
) -> tuple[bool, bool]:
    """Check if a file exists and contains a reference to the topic.

    Returns:
        (file_exists, topic_found)
    """
    if source is None:
        return False, False

    content = source

    # First try the regex pattern from the manifest
    if re.search(topic_pattern, content):
        return True, True

    # Fall back to literal topic name search
    if topic_name in content:
        return True, True

    # Try just the event-name segment (e.g. "agent-actions" from
    # "onex.evt.omniclaude.agent-actions.v1")
    parts = topic_name.split(".")
    if len(parts) >= _TOPIC_MIN_SEGMENTS:
        event_name = parts[3]
        if event_name in content:
            return True, True

    return True, False


def check_boundary(
    entry: ModelKafkaBoundaryEntry,
    files: Mapping[str, str],
) -> ModelBoundaryParityResult:
    """Check a single boundary for parity."""
    producer_path = f"{entry.producer_repo}/{entry.producer_file}"
    consumer_path = f"{entry.consumer_repo}/{entry.consumer_file}"

    producer_exists, producer_found = check_file_for_topic(
        files.get(producer_path), entry.topic_pattern, entry.topic_name
    )
    consumer_exists, consumer_found = check_file_for_topic(
        files.get(consumer_path), entry.topic_pattern, entry.topic_name
    )

    error_parts: list[str] = []
    if not producer_exists:
        error_parts.append(
            f"producer file missing: {entry.producer_repo}/{entry.producer_file}"
        )
    elif not producer_found:
        error_parts.append(
            f"topic not found in producer: {entry.producer_repo}/{entry.producer_file}"
        )
    if not consumer_exists:
        error_parts.append(
            f"consumer file missing: {entry.consumer_repo}/{entry.consumer_file}"
        )
    elif not consumer_found:
        error_parts.append(
            f"topic not found in consumer: {entry.consumer_repo}/{entry.consumer_file}"
        )

    return ModelBoundaryParityResult(
        boundary=entry,
        producer_ok=producer_found,
        consumer_ok=consumer_found,
        producer_file_exists=producer_exists,
        consumer_file_exists=consumer_exists,
        error="; ".join(error_parts),
    )


class HandlerBoundaryParity:
    """Decide parity without accessing the filesystem or clock."""

    def handle(self, request: ModelBoundaryParityInput) -> ModelBoundaryParityReport:
        """Return checked boundaries and pending entries still within grace."""
        files = {file.path: file.source for file in request.files}
        results: list[ModelBoundaryParityResult] = []
        pending_in_grace: list[ModelKafkaBoundaryEntry] = []
        for entry in request.boundaries:
            if entry.status == "pending":
                pending_date = datetime.strptime(
                    entry.pending_since, "%Y-%m-%d"
                ).replace(tzinfo=UTC)
                elapsed_days = (request.now - pending_date).days
                if elapsed_days <= PENDING_GRACE_PERIOD_DAYS:
                    pending_in_grace.append(entry)
                    continue
                results.append(
                    ModelBoundaryParityResult(
                        boundary=entry,
                        producer_ok=False,
                        consumer_ok=False,
                        producer_file_exists=True,
                        consumer_file_exists=False,
                        error=(
                            f"EXPIRED PENDING: {entry.topic_name} has been pending for "
                            f"{elapsed_days} days (since {entry.pending_since}, "
                            f"grace period is {PENDING_GRACE_PERIOD_DAYS} days). "
                            f"Reason: {entry.pending_reason or 'none'}"
                        ),
                    )
                )
                continue
            results.append(check_boundary(entry, files))
        return ModelBoundaryParityReport(
            results=results, pending_in_grace=pending_in_grace
        )


def format_report(report: ModelBoundaryParityReport) -> str:
    """Format the parity report for human consumption."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("Kafka Boundary Parity Report")
    lines.append("=" * 72)
    lines.append("")

    ok_count = sum(1 for r in report.results if r.producer_ok and r.consumer_ok)
    fail_count = report.mismatch_count
    total = len(report.results)

    lines.append(f"Total boundaries: {total}")
    lines.append(f"  OK:       {ok_count}")
    lines.append(f"  MISMATCH: {fail_count}")
    lines.append("")

    if fail_count > 0:
        lines.append("-" * 72)
        lines.append("MISMATCHES:")
        lines.append("-" * 72)
        for result in report.results:
            if not result.producer_ok or not result.consumer_ok:
                lines.append("")
                lines.append(f"  Topic: {result.boundary.topic_name}")
                lines.append(
                    f"  Producer: {result.boundary.producer_repo} -> "
                    f"Consumer: {result.boundary.consumer_repo}"
                )
                lines.append(f"  Error: {result.error}")
        lines.append("")

    if ok_count > 0 and fail_count == 0:
        lines.append("All boundaries are in parity.")
    elif ok_count > 0:
        lines.append("-" * 72)
        lines.append("OK boundaries:")
        lines.append("-" * 72)
        for result in report.results:
            if result.producer_ok and result.consumer_ok:
                lines.append(
                    f"  [OK] {result.boundary.topic_name} "
                    f"({result.boundary.producer_repo} -> "
                    f"{result.boundary.consumer_repo})"
                )

    lines.append("")
    return "\n".join(lines)


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
