# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cross-repo Kafka boundary parity check (OMN-20074).

Ported from onex_change_control (``check-boundary-parity``, rev a89a6f30fabf,
identical at dev da751e728024) for OCC retirement step S8. The decisions are the
source's: for every boundary in the manifest, the producer file and the consumer
file must each exist and reference the topic, by the manifest regex, then by the
literal topic name, then by its event-name segment. A ``pending`` boundary is skipped for 14 days
from ``pending_since`` and fails after that.

The manifest moved to ``contracts/kafka_boundaries.yaml``.
The handler is pure over an explicit snapshot (:class:`ModelBoundaryParityInput`);
``main`` reads the files the manifest names under ``--repos-root`` through the
source-file gather EFFECT and prints the source's report text. The source's
``--json`` and ``--check-schemas`` options are not ported: no caller passed
them.

Usage::

    python -m omnibase_core.handlers.handler_boundary_parity --repos-root DIR [--manifest PATH]

Exit code 0 = all boundaries in parity. Exit code 1 = a mismatch, or a missing
manifest or repos root.
"""

from __future__ import annotations

import argparse
import importlib.resources
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Final, Literal

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.boundary_validation.model_boundary_parity_input import (
    ModelBoundaryParityInput,
)
from omnibase_core.models.nodes.boundary_validation.model_kafka_boundary import (
    ModelKafkaBoundary,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

VALIDATOR_ID: Final[str] = "boundary-parity"
MANIFEST_RESOURCE: Final[str] = "kafka_boundaries.yaml"
PENDING_GRACE_PERIOD_DAYS: Final[int] = 14

_TOPIC_MIN_SEGMENTS: Final[int] = 4


def _boundary_from(item: Mapping[object, object]) -> ModelKafkaBoundary:
    """Read one manifest entry with the source's defaults."""
    return ModelKafkaBoundary(
        topic_name=str(item["topic_name"]),
        producer_repo=str(item["producer_repo"]),
        consumer_repo=str(item["consumer_repo"]),
        producer_file=str(item["producer_file"]),
        consumer_file=str(item["consumer_file"]),
        topic_pattern=str(item["topic_pattern"]),
        status=str(item.get("status", "active")),
        pending_since=str(item.get("pending_since", "")),
        pending_reason=str(item.get("pending_reason", "")),
    )


def load_manifest_yaml() -> str:
    """Return the packaged boundary manifest as text."""
    ref = importlib.resources.files("omnibase_core.contracts") / MANIFEST_RESOURCE
    return ref.read_text(encoding="utf-8")


def _load_boundaries(manifest_yaml: str) -> list[ModelKafkaBoundary]:
    data = load_yaml_mapping_no_duplicates(manifest_yaml, source="boundary manifest")
    if "boundaries" not in data:
        raise ModelOnexError(
            message="Invalid manifest: missing 'boundaries' key",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )
    items = data["boundaries"]
    if not isinstance(items, list):
        raise ModelOnexError(
            message="Invalid manifest: 'boundaries' is not a list",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )
    return [_boundary_from(item) for item in items if isinstance(item, Mapping)]


def _topic_found(content: str, topic_pattern: str, topic_name: str) -> bool:
    """Return whether *content* references the topic, as the source decided."""
    if re.search(topic_pattern, content):
        return True
    if topic_name in content:
        return True
    parts = topic_name.split(".")
    return len(parts) >= _TOPIC_MIN_SEGMENTS and parts[3] in content


def _pending_elapsed_days(boundary: ModelKafkaBoundary, today: date) -> int:
    pending = datetime.strptime(boundary.pending_since, "%Y-%m-%d").replace(tzinfo=UTC)
    return (today - pending.date()).days


def _is_pending_within_grace(boundary: ModelKafkaBoundary, today: date) -> bool:
    if boundary.status != "pending" or not boundary.pending_since:
        return False
    try:
        elapsed = _pending_elapsed_days(boundary, today)
    except ValueError:
        return False  # unparseable date: treated as expired, as the source did
    return elapsed <= PENDING_GRACE_PERIOD_DAYS


def _finding(
    boundary: ModelKafkaBoundary,
    *,
    severity: Literal["PASS", "FAIL", "SKIP"],
    error: str,
    location: str | None,
    message: str,
) -> ModelValidationFindingEmbed:
    return ModelValidationFindingEmbed(
        validator_id=VALIDATOR_ID,
        severity=severity,
        rule_id=VALIDATOR_ID,
        location=location,
        message=message,
        evidence={
            "topic": boundary.topic_name,
            "producer_repo": boundary.producer_repo,
            "consumer_repo": boundary.consumer_repo,
            "error": error,
        },
    )


class HandlerBoundaryParity:
    """Decide, per manifest boundary, whether producer and consumer still agree."""

    def handle(self, request: ModelBoundaryParityInput) -> ModelValidationReport:
        """Return one finding per boundary in manifest order.

        PASS for a boundary in parity, FAIL for a mismatch or an expired pending
        boundary, SKIP for a pending boundary within its grace period.
        """
        sources = {f.path: f.source for f in request.files}
        findings: list[ModelValidationFindingEmbed] = []
        for boundary in _load_boundaries(request.manifest_yaml):
            findings.append(self._decide(boundary, sources, request.today))
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )

    @staticmethod
    def _decide(
        boundary: ModelKafkaBoundary, sources: Mapping[str, str], today: date
    ) -> ModelValidationFindingEmbed:
        if boundary.status == "pending":
            if _is_pending_within_grace(boundary, today):
                reason = boundary.pending_reason or "no reason given"
                return _finding(
                    boundary,
                    severity="SKIP",
                    error="",
                    location=None,
                    message=(
                        f"  PENDING (grace): {boundary.topic_name} "
                        f"({boundary.producer_repo} -> {boundary.consumer_repo}) "
                        f"— {reason}"
                    ),
                )
            elapsed = _pending_elapsed_days(boundary, today)
            error = (
                f"EXPIRED PENDING: {boundary.topic_name} has been pending for "
                f"{elapsed} days (since {boundary.pending_since}, "
                f"grace period is {PENDING_GRACE_PERIOD_DAYS} days). "
                f"Reason: {boundary.pending_reason or 'none'}"
            )
            return _finding(
                boundary,
                severity="FAIL",
                error=error,
                location=boundary.consumer_path,
                message=f"{boundary.topic_name}: {error}",
            )

        errors: list[str] = []
        location: str | None = None
        for role, path in (
            ("producer", boundary.producer_path),
            ("consumer", boundary.consumer_path),
        ):
            content = sources.get(path)
            if content is None:
                errors.append(f"{role} file missing: {path}")
            elif not _topic_found(content, boundary.topic_pattern, boundary.topic_name):
                errors.append(f"topic not found in {role}: {path}")
            else:
                continue
            location = location or path
        error = "; ".join(errors)
        if errors:
            return _finding(
                boundary,
                severity="FAIL",
                error=error,
                location=location,
                message=f"{boundary.topic_name}: {error}",
            )
        return _finding(
            boundary,
            severity="PASS",
            error="",
            location=None,
            message=(
                f"  [OK] {boundary.topic_name} "
                f"({boundary.producer_repo} -> {boundary.consumer_repo})"
            ),
        )


def format_report(report: ModelValidationReport) -> str:
    """Render the report in the source's ``format_report`` text."""
    checked = [f for f in report.findings if f.severity != "SKIP"]
    ok = [f for f in checked if f.severity == "PASS"]
    failed = [f for f in checked if f.severity == "FAIL"]
    rule = "=" * 72
    dash = "-" * 72
    lines = [rule, "Kafka Boundary Parity Report", rule, ""]
    lines += [
        f"Total boundaries: {len(checked)}",
        f"  OK:       {len(ok)}",
        f"  MISMATCH: {len(failed)}",
        "",
    ]
    if failed:
        lines += [dash, "MISMATCHES:", dash]
        for finding in failed:
            lines += [
                "",
                f"  Topic: {finding.evidence['topic']}",
                f"  Producer: {finding.evidence['producer_repo']} -> "
                f"Consumer: {finding.evidence['consumer_repo']}",
                f"  Error: {finding.evidence['error']}",
            ]
        lines.append("")
    if ok and not failed:
        lines.append("All boundaries are in parity.")
    elif ok:
        lines += [dash, "OK boundaries:", dash]
        lines += [finding.message for finding in ok]
    lines.append("")
    return "\n".join(lines)


def _manifest_paths(manifest_yaml: str, repos_root: Path) -> list[str]:
    """Return the absolute paths of every producer and consumer file named."""
    paths: list[str] = []
    for boundary in _load_boundaries(manifest_yaml):
        for rel in (boundary.producer_path, boundary.consumer_path):
            candidate = str(repos_root / rel)
            if candidate not in paths:
                paths.append(candidate)
    return paths


def _gather(
    manifest_yaml: str, repos_root: Path
) -> tuple[list[ModelSourceFile], list[str]]:
    """Read the named files that exist; return them and any unreadable ones."""
    gathered = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(repos_root),
            explicit_paths=_manifest_paths(manifest_yaml, repos_root),
            include_patterns=["**/*"],
        )
    )
    unreadable = [
        f"{s.path}: {s.reason}" for s in gathered.skipped if s.reason != "not a file"
    ]
    prefix = f"{repos_root}/"
    files = [
        ModelSourceFile(path=f.path.removeprefix(prefix), source=f.source)
        for f in gathered.files
    ]
    return files, unreadable


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point with the source's ``check-boundary-parity`` options."""
    parser = argparse.ArgumentParser(
        description="Check cross-repo Kafka boundary parity",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Path to a boundary manifest (default: bundled in package)",
    )
    parser.add_argument(
        "--repos-root",
        required=True,
        help="Root directory holding one checkout per peer repository",
    )
    args = parser.parse_args(argv)

    repos_root = Path(args.repos_root)
    if args.manifest is not None:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_file():
            sys.stderr.write(f"ERROR: Manifest not found: {manifest_path}\n")
            return 1
        manifest_yaml = manifest_path.read_text(encoding="utf-8")
    else:
        manifest_yaml = load_manifest_yaml()
    if not repos_root.is_dir():
        sys.stderr.write(f"ERROR: Repos root not found: {repos_root}\n")
        return 1

    files, unreadable = _gather(manifest_yaml, repos_root)
    if unreadable:
        for line in unreadable:
            sys.stderr.write(f"ERROR: unreadable boundary file {line}\n")
        return 1
    report = HandlerBoundaryParity().handle(
        ModelBoundaryParityInput(
            manifest_yaml=manifest_yaml,
            files=files,
            today=datetime.now(tz=UTC).date(),
        )
    )
    for finding in report.findings:
        if finding.severity == "SKIP":
            sys.stdout.write(f"{finding.message}\n")
    sys.stdout.write(f"{format_report(report)}\n")
    return 1 if report.overall_status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
