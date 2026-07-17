# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the no-direct-kafka-producer check — pre-commit hook + CI entrypoint.

Both invocation surfaces are backed by the SAME canonical COMPUTE node
(``NodeNoDirectKafkaProducerCheckCompute``) — DRY per the OMN-13305 pattern,
following the ``node_no_utcnow_check_compute`` template (OMN-14656): a single
module owns the pure handler plus a synchronous CLI ``main()`` that performs
all filesystem I/O at the CLI boundary, never inside the handler.

Two modes:

* **pre-commit** (explicit filenames): the staged files pre-commit hands us
  are read directly here — no directory walk needed.
* **full-tree** (no filenames — CI / manual ``python -m ...``): walks
  ``--root`` (default ``src``) via the paired ``node_source_file_gather_effect``
  EFFECT node, reproducing the oracle CI gate's whole-tree scan
  (``omniclaude/scripts/validation/validate_no_direct_kafka_producer.py``
  ``src_root.rglob("*.py")``).

Usage::

    python -m omnibase_core.nodes.node_no_direct_kafka_producer_check_compute.runtime_no_direct_kafka_producer_check file1.py file2.py
    python -m omnibase_core.nodes.node_no_direct_kafka_producer_check_compute.runtime_no_direct_kafka_producer_check
    python -m omnibase_core.nodes.node_no_direct_kafka_producer_check_compute.runtime_no_direct_kafka_producer_check --root src

Exit codes: 0 — ``overall_status == "PASS"``; 1 — FAIL/ERROR findings present.

Ticket: OMN-14659 (WS8 — convert-clean generic omniclaude arch validators).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.no_direct_kafka_producer_check.model_no_direct_kafka_producer_check_input import (  # onex-allow-kafka-producer: this check's own input-model name contains the "KafkaProducer" substring; not a producer client
    ModelNoDirectKafkaProducerCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_no_direct_kafka_producer_check_compute.handler import (  # onex-allow-kafka-producer: this check's own node-class name contains the "KafkaProducer" substring; not a producer client
    NodeNoDirectKafkaProducerCheckCompute,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)

__all__ = ["main"]

_DEFAULT_ROOT: Final[str] = "src"


def _gather_from_filenames(
    paths: list[Path],
) -> tuple[list[ModelSourceFile], list[str]]:
    """CLI I/O boundary for pre-commit's explicit staged-file mode.

    Non-``.py`` and missing paths are intentionally skipped. Read errors on
    existing Python files are returned as fatal diagnostics so the runtime
    does not report PASS with unscanned source.
    """
    files: list[ModelSourceFile] = []
    read_errors: list[str] = []
    for path in paths:
        if path.suffix != ".py" or not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            read_errors.append(f"{path}: read error: {exc}")
            continue
        files.append(ModelSourceFile(path=str(path), source=source))
    return files, read_errors


def _gather_from_root(root: str) -> tuple[list[ModelSourceFile], list[str]]:
    """Full-tree walk mode (CI / manual), reusing ``node_source_file_gather_effect``.

    This is the EFFECT boundary — the only filesystem walk in this module —
    delegated to the paired canonical node rather than re-implemented here.
    """
    output = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(root=root, include_patterns=["**/*.py"])
    )
    read_errors = [
        f"{skipped.path}: {skipped.reason}"
        for skipped in output.skipped
        if skipped.reason.startswith(("read error:", "error checking file size:"))
    ]
    return [
        ModelSourceFile(path=f.path, source=f.source) for f in output.files
    ], read_errors


def _run(files: list[ModelSourceFile]) -> ModelValidationReport:
    """Dispatch gathered (path, source) pairs to the canonical COMPUTE node."""
    return NodeNoDirectKafkaProducerCheckCompute().handle(
        ModelNoDirectKafkaProducerCheckInput(files=files)
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry: pre-commit staged-file mode, or a full-tree walk with no args.

    Returns:
        0 on PASS, 1 on FAIL/ERROR.
    """
    parser = argparse.ArgumentParser(
        prog="check-no-direct-kafka-producer",
        description=(
            "Detect direct Kafka producer client usage via the "
            "no-direct-kafka-producer-check COMPUTE node (OMN-14659)."
        ),
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        help=(
            "Files to check (pre-commit passes staged filenames here). "
            "When omitted, walks --root recursively (CI / manual mode)."
        ),
    )
    parser.add_argument(
        "--root",
        default=_DEFAULT_ROOT,
        help=(
            "Root directory for a full-tree walk when no filenames are given "
            f"(default: {_DEFAULT_ROOT})"
        ),
    )
    parsed = parser.parse_args(argv)

    if parsed.filenames:
        files, read_errors = _gather_from_filenames([Path(f) for f in parsed.filenames])
    else:
        files, read_errors = _gather_from_root(parsed.root)

    if read_errors:
        print(  # print-ok: CLI output
            f"ERROR: Failed to read {len(read_errors)} Python file(s):"
        )
        for read_error in read_errors:
            print(f"  {read_error}")  # print-ok: CLI output
        return 1

    report = _run(files)

    if report.overall_status == "PASS":
        print(  # print-ok: CLI output
            "OK: No direct Kafka producer usage found outside the shared publisher layer"
        )
        return 0

    print(  # print-ok: CLI output
        f"FAIL: Found {report.metrics.total} direct Kafka producer violation(s):"
    )
    for finding in report.findings:
        print(f"  {finding.message}")  # print-ok: CLI output
    print(  # print-ok: CLI output
        "\nDirect Kafka producer usage (AIOKafkaProducer, KafkaProducer, confluent_kafka)"
        " must only occur in the shared publisher layer."
        "\nUse emit_via_daemon() or the shared publisher abstraction instead."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
