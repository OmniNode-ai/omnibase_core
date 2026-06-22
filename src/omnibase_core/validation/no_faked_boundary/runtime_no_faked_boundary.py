# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Two-transport runner for the no-faked-boundary COMPUTE validator (OMN-13497).

The seam that makes the SAME ``HandlerNoFakedBoundaryCompute`` run over a
swappable bus backend (identical to the private-IP / local-paths validators):

* **pre-commit** (default here): the in-memory backend (``EventBusInmemory``) —
  in-process, zero infra, no ``.201``/Kafka, deterministic, fast.
* **CI**: the same handler, a Kafka backend, fanned across the runner fleet.

Only the *backend* changes; the handler and dispatch shape are identical, so
local and CI verdicts cannot drift.

The runner owns the EFFECT boundary: ``_iter_source_files`` / ``_read_text`` load
the staged file set (the I/O). Each file is published as a typed command envelope
onto the bus; the COMPUTE handler scans the TEXT and publishes its verdict back on
the result topic; the runner aggregates findings and exits non-zero when any file
is flagged. The COMPUTE handler itself never touches the filesystem.

Scope: the validator targets fakes of the platform's own inference / routing /
dispatch boundary, which live in Python source (overwhelmingly tests claiming
real-dispatch coverage), so the runner scans ``.py`` files only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from omnibase_core.constants.constants_event_types import (
    TOPIC_VALIDATION_NO_FAKED_BOUNDARY_SCAN_COMPLETED_EVENT,
    TOPIC_VALIDATION_NO_FAKED_BOUNDARY_SCAN_REQUESTED_CMD,
)
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.no_faked_boundary.handler import (
    HandlerNoFakedBoundaryCompute,
)
from omnibase_core.validation.no_faked_boundary.models import (
    ModelNoFakedBoundaryScanInput,
    ModelNoFakedBoundaryScanResult,
)

__all__ = [
    "COMMAND_TOPIC",
    "RESULT_TOPIC",
    "NoFakedBoundaryBusRunner",
    "main",
]

# Contract-style topic names sourced from the canonical topic registry
# (constants_event_types) rather than inline literals.
COMMAND_TOPIC: Final[str] = TOPIC_VALIDATION_NO_FAKED_BOUNDARY_SCAN_REQUESTED_CMD
RESULT_TOPIC: Final[str] = TOPIC_VALIDATION_NO_FAKED_BOUNDARY_SCAN_COMPLETED_EVENT

_RUNNER_GROUP: Final[str] = "validator-no-faked-boundary-runner"
_HANDLER_GROUP: Final[str] = "validator-no-faked-boundary-compute"

# Python source only — the EFFECT boundary that decides which files are loaded.
_TEXT_EXTENSIONS: Final[frozenset[str]] = frozenset({".py"})
_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".tox",
        ".venv",
        "venv",
        ".next",
        "dist",
        "build",
        "graphify-out",
        "dod_receipts",
        "evidence",
        ".evidence",
        ".onex_state",
        # Nested worktrees are never the committing repo's own staged file set —
        # the pre-commit gate scans only the repo it runs in. Pruning them keeps
        # a directory-mode scan from recursing into checked-out sibling branches.
        "omni_worktrees",
    }
)


class NoFakedBoundaryBusRunner:
    """Dispatch source files to the COMPUTE handler over a swappable bus backend.

    The bus is injected: ``EventBusInmemory`` for pre-commit, a Kafka backend in
    CI. The runner subscribes the handler to the command topic and itself to the
    result topic, publishes one command envelope per file, and collects the typed
    verdicts. Same handler + dispatch shape regardless of backend.
    """

    def __init__(self, bus: EventBusInmemory) -> None:
        self._bus = bus
        self._handler = HandlerNoFakedBoundaryCompute()
        self._results: dict[str, ModelNoFakedBoundaryScanResult] = {}

    async def _on_command(self, message: ModelEventMessage) -> None:
        raw = json.loads(message.value.decode("utf-8"))
        scan_input = ModelNoFakedBoundaryScanInput.model_validate(raw)
        envelope: ModelEventEnvelope[ModelNoFakedBoundaryScanInput] = (
            ModelEventEnvelope(payload=scan_input)
        )
        output = await self._handler.handle(envelope)
        result = output.result
        assert result is not None  # COMPUTE always returns a result
        await self._bus.publish(
            RESULT_TOPIC, None, result.model_dump_json().encode("utf-8")
        )

    async def _on_result(self, message: ModelEventMessage) -> None:
        raw = json.loads(message.value.decode("utf-8"))
        result = ModelNoFakedBoundaryScanResult.model_validate(raw)
        self._results[result.path] = result

    async def scan_inputs(
        self, inputs: list[ModelNoFakedBoundaryScanInput]
    ) -> list[ModelNoFakedBoundaryScanResult]:
        """Dispatch every input over the bus and return verdicts in input order."""
        await self._bus.subscribe(
            COMMAND_TOPIC, on_message=self._on_command, group_id=_HANDLER_GROUP
        )
        await self._bus.subscribe(
            RESULT_TOPIC, on_message=self._on_result, group_id=_RUNNER_GROUP
        )
        for scan_input in inputs:
            await self._bus.publish(
                COMMAND_TOPIC, None, scan_input.model_dump_json().encode("utf-8")
            )
        # In-memory pub/sub delivers inline; a tick lets any scheduled callbacks
        # drain. Order-independence of findings is guaranteed inside the handler.
        await asyncio.sleep(0)
        return [
            self._results[scan_input.path]
            for scan_input in inputs
            if scan_input.path in self._results
        ]


def _iter_source_files(paths: list[Path]) -> Iterator[Path]:
    """EFFECT boundary: yield scannable files, pruning skip-dirs + non-py ext."""
    for p in paths:
        if p.is_file():
            if p.suffix in _TEXT_EXTENSIONS and not any(
                part in _SKIP_DIRS for part in p.parts
            ):
                yield p
        elif p.is_dir():
            for child in sorted(p.rglob("*")):
                if any(part in _SKIP_DIRS for part in child.parts):
                    continue
                if child.is_file() and child.suffix in _TEXT_EXTENSIONS:
                    yield child


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return ""


async def _run(paths: list[Path], *, quiet: bool, report_only: bool) -> int:
    inputs = [
        ModelNoFakedBoundaryScanInput(content=_read_text(fp), path=str(fp))
        for fp in _iter_source_files(paths)
    ]
    bus = EventBusInmemory()
    await bus.start()
    try:
        runner = NoFakedBoundaryBusRunner(bus)
        results = await runner.scan_inputs(inputs)
    finally:
        await bus.shutdown()

    flagged = [r for r in results if r.flagged]
    total_findings = 0
    for result in flagged:
        for finding in result.findings:
            total_findings += 1
            print(
                f"{finding.path}:{finding.line}: [{finding.pattern}] "
                f"{finding.matched_text!r}"
            )

    if not quiet:
        if total_findings:
            print(
                f"\n{total_findings} faked-boundary finding(s). Use the REAL "
                f"inference / routing / dispatch surface (a recorded-from-real "
                f"replay adapter, RoutingResolvedJudgeInferenceAdapter, or a real "
                f"EventBusInmemory test), or add `# onex-allow-faked-boundary` to "
                f"suppress an approved fixture."
            )
            if report_only:
                # OMN-13497: the gate lands REPORT-ONLY. The real shadow run across
                # omnimarket + omnibase_core + omniclaude surfaced a large pre-
                # existing population of genuine boundary-fakes in delegation /
                # golden-chain / dispatch tests (NOT false positives — exactly the
                # "handler-isolation passes while live fails" fakes this gate bans).
                # Flipping to blocking before those are remediated would red-wedge
                # three repos. Report-only burns them down; flip to blocking when
                # the population reaches zero. Tracked under OMN-13497.
                print(
                    "[report-only] not failing the commit (OMN-13497 burn-down "
                    "phase). Flip to blocking when findings reach zero."
                )
        else:
            print("No faked-boundary violations found.")
    if report_only:
        return 0
    return 1 if total_findings else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: scan staged files (pre-commit) or directories over the bus.

    Default backend is in-memory (``EventBusInmemory``) — the pre-commit
    transport. CI runs the same handler over Kafka by constructing the runner
    with a Kafka backend.

    Exit codes: 0 — no violations; 1 — violations found.
    """
    parser = argparse.ArgumentParser(
        prog="check-no-faked-boundary",
        description=(
            "Detect hand-written fakes/stubs of the platform's own inference / "
            "routing / dispatch boundary via the no-faked-boundary COMPUTE node "
            "executed over the in-memory event bus (OMN-13497)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress the trailing summary",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "Print findings but always exit 0 (OMN-13497 burn-down phase). The "
            "pre-commit wiring uses this until the pre-existing boundary-fake "
            "population reaches zero, then drops the flag to flip to blocking."
        ),
    )
    parsed = parser.parse_args(argv)
    return asyncio.run(
        _run(parsed.paths, quiet=parsed.quiet, report_only=parsed.report_only)
    )


if __name__ == "__main__":
    sys.exit(main())
