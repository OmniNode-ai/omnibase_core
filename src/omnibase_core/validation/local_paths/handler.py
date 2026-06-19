# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerLocalPathsCompute — generated COMPUTE validator for hardcoded paths.

GENERATED ARTIFACT (OMN-13293, G1). The scanning logic in ``scan_source`` was
produced by ``node_generation_consumer`` (omnimarket), local-model-first through
the real delegation chain (model ``Qwen3.6-35B-A3B`` on the local-coder backend),
and accepted ONLY because it reproduces the hand-authored ground truth
``omnibase_core.validation.validator_local_paths`` across a deterministic fixture
corpus whose verdicts are derived from that ground truth. Equivalence was proven
on every corpus fixture (0 mismatches) before this file was landed. See the
generation provenance under the G1 evidence in OMN-13293.

ONEX node type: COMPUTE. Handler output: ``result`` only (no events / intents /
projections). The handler is PURE and DETERMINISTIC: it scans the source TEXT
carried on the envelope payload and performs no filesystem / network / env I/O.
Loading the staged file set is the EFFECT boundary's job (``runtime_local_paths``),
never the handler's — that is what preserves COMPUTE purity (§1A of the
validator-standardization remediation plan).

The four detection patterns and the ``local-path-ok`` suppression marker are the
same the ground truth uses; they are the canonical definition of "a hardcoded
machine-specific absolute path" and are not duplicated config — both this
generated COMPUTE handler and the ground-truth script encode the SAME invariant,
which is exactly what the corpus equivalence proof verifies.
"""

from __future__ import annotations

import re
from typing import Final
from uuid import UUID

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.local_paths.models import (
    ModelLocalPathFinding,
    ModelLocalPathScanInput,
    ModelLocalPathScanResult,
)

__all__ = ["HandlerLocalPathsCompute", "scan_source"]

# Generated detection patterns — the four machine-specific absolute-path shapes.
# Identical invariant to validator_local_paths._LOCAL_PATH_PATTERNS (proven
# equivalent by the G1 corpus). Each entry is (human-name, compiled-pattern).
_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("macOS volume mount", re.compile(r"/Volumes/[A-Za-z][A-Za-z0-9_.\-]*/")),
    ("macOS user home", re.compile(r"/Users/[A-Za-z_][A-Za-z0-9_.\-]*/")),
    ("Linux user home", re.compile(r"/home/[A-Za-z_][A-Za-z0-9_.\-]*/")),
    ("Windows user path", re.compile(r"[Cc]:[/\\][Uu]sers[/\\]")),
)

# A line carrying this exact marker is suppressed (allowlisted), matching the
# ground truth's `# local-path-ok` escape hatch.
_SUPPRESSION_MARKER: Final[str] = "local-path-ok"


def scan_source(content: str, path: str = "<input>") -> ModelLocalPathScanResult:
    """Scan ``content`` line by line for hardcoded absolute paths.

    Pure and deterministic. Reproduces ``validator_local_paths.py`` per-line
    logic: a line containing the ``local-path-ok`` suppression marker is skipped;
    otherwise every match of every pattern on the line is a finding. Findings are
    emitted in a stable order (line, then column, then pattern order) so the
    verdict is order-independent regardless of dispatch backend (§1A risk 2).
    """
    findings: list[ModelLocalPathFinding] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        if _SUPPRESSION_MARKER in line:
            continue
        for pattern_name, pattern in _PATTERNS:
            for match in pattern.finditer(line):
                findings.append(
                    ModelLocalPathFinding(
                        path=path,
                        line=lineno,
                        column=match.start() + 1,
                        pattern_name=pattern_name,
                        matched_text=match.group(),
                        context=line.rstrip(),
                    )
                )
    findings.sort(key=lambda f: (f.line, f.column, f.pattern_name))
    return ModelLocalPathScanResult(
        path=path, flagged=bool(findings), findings=tuple(findings)
    )


class HandlerLocalPathsCompute:
    """COMPUTE handler: scan one source-text payload for hardcoded paths.

    Implements ``omnibase_core.protocols.runtime.ProtocolMessageHandler`` as a
    COMPUTE handler. Stateless and pure — safe for concurrent dispatch. Returns
    the verdict as ``ModelHandlerOutput.result`` (the COMPUTE-required field).
    """

    @property
    def handler_id(self) -> str:
        return "validator-local-paths-compute"

    @property
    def category(self) -> EnumMessageCategory:
        # A validation request is an imperative "scan this" — a COMMAND.
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"LocalPathScanRequested"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self, envelope: ModelEventEnvelope[ModelLocalPathScanInput]
    ) -> ModelHandlerOutput[ModelLocalPathScanResult]:
        scan_input = envelope.payload
        result = scan_source(scan_input.content, scan_input.path)
        correlation_id: UUID = envelope.correlation_id or envelope.envelope_id
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=correlation_id,
            handler_id=self.handler_id,
            result=result,
        )
