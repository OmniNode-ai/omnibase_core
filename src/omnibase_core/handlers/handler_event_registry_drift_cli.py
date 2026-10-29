# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the event-registry drift check — pre-commit hook + CI entrypoint (OMN-21416).

Reads every source through the paired ``node_source_file_gather_effect``
EFFECT node, parses it with the pure parsers in
:mod:`.handler_event_registry_drift_sources`, and dispatches the typed registrations to
the canonical ``HandlerEventRegistryDrift`` handler. All filesystem
I/O stays at this boundary, never inside the handler.

Sources:

* ``--source-contracts DIR`` (repeatable) — every ``*.yaml``/``*.yml`` file
  under ``DIR``; wire contracts with an ``event_registration`` block declare
  the producer's registrations.
* ``--source-document FILE`` (repeatable) — an ``event_registrations:``
  document of exported registrations.
* ``--registry-topics-yaml FILE`` — the emit registry to compare against.
* ``--baseline FILE`` — optional declared divergence.

A source that is missing, unreadable or malformed, a contract directory with
no files, or a source side that declares no registration at all, is an ERROR
report — never PASS.

Usage::

    python -m omnibase_core.handlers.handler_event_registry_drift_cli \\
        --source-contracts src/pkg/hooks/contracts/wire \\
        --registry-topics-yaml src/pkg/nodes/node_emit_daemon/registries/topics.yaml

Exit codes: 0 — ``overall_status == "PASS"``; 1 — FAIL/ERROR findings present.
"""

from __future__ import annotations

import argparse
import sys
from typing import Final

from omnibase_core.handlers.handler_event_registry_drift import (
    VALIDATOR_ID,
    HandlerEventRegistryDrift,
)
from omnibase_core.handlers.handler_event_registry_drift_sources import (
    parse_baseline,
    parse_emit_registry,
    parse_registration_contract,
    parse_registration_document,
)
from omnibase_core.models.event_registry_drift.model_event_registration import (
    ModelEventRegistration,
)
from omnibase_core.models.event_registry_drift.model_event_registry_drift_baseline import (
    ModelEventRegistryDriftBaseline,
)
from omnibase_core.models.event_registry_drift.model_event_registry_drift_check_input import (
    ModelEventRegistryDriftCheckInput,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output import (
    ModelGatheredSourceFile,
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
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

__all__ = ["main"]

_CONTRACT_PATTERNS: Final[list[str]] = ["**/*.yaml", "**/*.yml"]
_ANY_FILE: Final[list[str]] = ["**/*"]


def _read_named(path: str) -> tuple[ModelGatheredSourceFile | None, str]:
    """Read one named file through the gather EFFECT; a skip is an error."""
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=".", explicit_paths=[path], include_patterns=_ANY_FILE
        )
    )
    if output.files:
        return output.files[0], ""
    reason = output.skipped[0].reason if output.skipped else "not read"
    return None, f"{path}: {reason}"


def _read_contract_dir(
    directory: str,
) -> tuple[list[ModelGatheredSourceFile], list[str]]:
    """Walk one contract directory through the gather EFFECT."""
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(root=directory, include_patterns=_CONTRACT_PATTERNS)
    )
    errors = [
        f"{skipped.path}: {skipped.reason}"
        for skipped in output.skipped
        if skipped.reason.startswith(
            ("read error:", "error checking file size:", "exceeds max file size")
        )
    ]
    if not output.files and not errors:
        errors.append(
            f"{directory}: no contract file found (missing or empty directory); "
            "a scan that reads nothing is ERROR, never PASS"
        )
    return list(output.files), errors


def _gather_sources(
    contract_dirs: list[str], documents: list[str]
) -> tuple[list[ModelEventRegistration], list[str]]:
    registrations: list[ModelEventRegistration] = []
    errors: list[str] = []
    for directory in contract_dirs:
        files, read_errors = _read_contract_dir(directory)
        errors.extend(read_errors)
        declared = 0
        for gathered in files:
            registration, parse_errors = parse_registration_contract(
                gathered.path, gathered.source
            )
            errors.extend(parse_errors)
            if registration is not None:
                registrations.append(registration)
                declared += 1
        if files and not read_errors and declared == 0:
            errors.append(
                f"{directory}: no contract declares an event_registration; "
                "empty discovery is ERROR, never PASS"
            )
    for path in documents:
        gathered_doc, read_error = _read_named(path)
        if gathered_doc is None:
            errors.append(read_error)
            continue
        parsed, parse_errors = parse_registration_document(
            gathered_doc.path, gathered_doc.source
        )
        registrations.extend(parsed)
        errors.extend(parse_errors)
    return registrations, errors


def _say(line: str) -> None:
    """Write one CLI output line."""
    sys.stdout.write(line + "\n")


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    """Persist the canonical report through the write EFFECT node."""
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check-event-registry-drift",
        description=(
            "Compare a producer's declared event registrations with an emit "
            "registry in omnibase_core's generic validator format (OMN-21416)."
        ),
    )
    parser.add_argument(
        "--source-contracts",
        action="append",
        default=[],
        metavar="DIR",
        help="Directory of wire contracts; repeatable.",
    )
    parser.add_argument(
        "--source-document",
        action="append",
        default=[],
        metavar="FILE",
        help="An event_registrations: document; repeatable.",
    )
    parser.add_argument(
        "--registry-topics-yaml",
        required=True,
        metavar="FILE",
        help="The emit registry (topics.yaml with an events: mapping).",
    )
    parser.add_argument(
        "--baseline", default=None, metavar="FILE", help="Declared divergence."
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Write the canonical ValidationReport JSON on PASS, FAIL and ERROR.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns 0 on PASS, 1 on FAIL/ERROR."""
    parsed = _build_parser().parse_args(argv)

    errors: list[str] = []
    if not parsed.source_contracts and not parsed.source_document:
        errors.append("no source given: pass --source-contracts or --source-document")
    source, source_errors = _gather_sources(
        parsed.source_contracts, parsed.source_document
    )
    errors.extend(source_errors)

    registry: tuple[ModelEventRegistration, ...] = ()
    gathered_registry, read_error = _read_named(parsed.registry_topics_yaml)
    if gathered_registry is None:
        errors.append(read_error)
    else:
        registry, registry_errors = parse_emit_registry(
            gathered_registry.path, gathered_registry.source
        )
        errors.extend(registry_errors)

    baseline = ModelEventRegistryDriftBaseline()
    if parsed.baseline is not None:
        gathered_baseline, read_error = _read_named(parsed.baseline)
        if gathered_baseline is None:
            errors.append(read_error)
        else:
            parsed_baseline, baseline_errors = parse_baseline(
                gathered_baseline.path, gathered_baseline.source
            )
            errors.extend(baseline_errors)
            if parsed_baseline is not None:
                baseline = parsed_baseline

    if errors:
        error_report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, tuple(errors)
        )
        _write_report(parsed.report_json, error_report)
        _say(f"ERROR: the event-registry sources could not be judged ({len(errors)}):")
        for error in errors:
            _say(f"  {error}")
        return 1

    report = HandlerEventRegistryDrift().handle(
        ModelEventRegistryDriftCheckInput(
            source_registrations=tuple(source),
            registry_registrations=registry,
            baseline=baseline,
        )
    )
    _write_report(parsed.report_json, report)

    if report.overall_status == "PASS":
        _say(
            f"OK: {len(source)} declared event registration(s) match the emit registry"
        )
        return 0

    _say(f"{report.overall_status}: {report.metrics.total} event-registry finding(s):")
    for finding in report.findings:
        _say(f"  [{finding.rule_id}] {finding.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
