# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Check a document's diagrams against its paired contract fragments."""

from __future__ import annotations

import re
from collections.abc import Callable

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.diagram_drift.model_diagram_drift_report import (
    ModelDiagramDriftReport,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_rules import (
    ModelDiagramDriftRules,
)
from omnibase_core.models.diagram_drift.model_loaded_diagram_fragment import (
    ModelLoadedDiagramFragment,
)

# The caller's renderer: fragment text in, the loaded fragment out; ValueError when the core model refuses it.
type FragmentLoader = Callable[[str], ModelLoadedDiagramFragment]

# Language, body, opening fence index, closing fence index.
type _Block = tuple[str, list[str], int, int]


def _read_block(lines: list[str], marker_index: int, fence: str) -> _Block | None:
    """Read the fenced block after a marker, skipping blank lines."""
    index = marker_index + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or not lines[index].startswith(fence):
        return None
    language = lines[index][len(fence) :].strip()
    end = index + 1
    while end < len(lines) and not lines[end].startswith(fence):
        end += 1
    if end >= len(lines):
        return None
    return language, lines[index + 1 : end], index, end


class HandlerDiagramDrift:
    """Pure diagram comparison with contract rules and an injected fragment loader."""

    def check(
        self,
        document_text: str,
        rules: ModelDiagramDriftRules,
        load_fragment: FragmentLoader,
    ) -> ModelDiagramDriftReport:
        """Reproduce check_document_diagrams verdicts, counts, and issue order."""
        lines = document_text.splitlines()
        issues: list[ModelValidationIssue] = []
        diagram_marker = re.compile(rules.diagram_marker_pattern)
        fragment_marker = re.compile(rules.fragment_marker_pattern)

        def add(
            kind: str,
            contract_id: str,
            document_line: int,
            message: str,
            diagram_line: int = 0,
        ) -> None:
            if kind in rules.enabled_kinds:
                issues.append(
                    ModelValidationIssue(
                        code=kind,
                        rule_name=kind,
                        severity=EnumSeverity.ERROR,
                        line_number=document_line,
                        message=message,
                        context={
                            "contract_id": contract_id,
                            "diagram_line": str(diagram_line),
                        },
                    )
                )

        def check_caption(node: str, contract_id: str, block: _Block) -> None:
            _, _, _, end_index = block
            index = end_index + 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            if index >= len(lines) or node not in lines[index]:
                add(
                    "missing_contract_line",
                    contract_id,
                    end_index + 1,
                    f"the line under the diagram does not name {node}",
                )

        def compare(contract_id: str, generated: str, block: _Block) -> None:
            _, body, fence_index, _ = block
            expected = generated.splitlines()
            found = [line.rstrip() for line in body]
            for position in range(max(len(expected), len(found))):
                want = expected[position] if position < len(expected) else None
                have = found[position] if position < len(found) else None
                if want == have:
                    continue
                number = position + 1
                add(
                    "diagram_differs",
                    contract_id,
                    fence_index + 1 + number,
                    f"line {number} of the diagram differs from the one generated from the fragment: "
                    f"expected {want.strip() if want is not None else '(no line)'!r}, "
                    f"found {have.strip() if have is not None else '(no line)'!r}",
                    number,
                )
                return

        fragments: dict[str, tuple[int, _Block]] = {}
        diagrams: list[tuple[str, str, str, str, int, _Block]] = []
        for index, raw in enumerate(lines):
            marker = raw.strip()
            fragment_match = fragment_marker.match(marker)
            diagram_match = diagram_marker.match(marker)
            if not fragment_match and not diagram_match:
                continue
            block = _read_block(lines, index, rules.fence)
            if fragment_match:
                contract_id = f"{fragment_match[1]}:{fragment_match[2]}"
                if block is None or block[0] != rules.fragment_language:
                    add(
                        "malformed_marker",
                        contract_id,
                        index + 1,
                        "a contract-fragment marker is followed by no yaml block",
                    )
                elif contract_id in fragments:
                    add(
                        "duplicate_fragment",
                        contract_id,
                        index + 1,
                        f"a second fragment for {contract_id}; the first is at line {fragments[contract_id][0]}",
                    )
                else:
                    fragments[contract_id] = (index + 1, block)
            elif diagram_match:
                contract_id = f"{diagram_match[1]}:{diagram_match[2]}"
                if block is None or block[0] != rules.diagram_language:
                    add(
                        "malformed_marker",
                        contract_id,
                        index + 1,
                        "a diagram-contract marker is followed by no mermaid block",
                    )
                else:
                    view = rules.collapsed_view if diagram_match[3] else rules.full_view
                    diagrams.append(
                        (
                            contract_id,
                            diagram_match[1],
                            diagram_match[2],
                            view,
                            index + 1,
                            block,
                        )
                    )

        loaded: dict[str, ModelLoadedDiagramFragment | None] = {}
        for contract_id, (line, block) in fragments.items():
            try:
                loaded[contract_id] = load_fragment("\n".join(block[1]) + "\n")
            except ValueError as refused:
                loaded[contract_id] = None
                add(
                    "fragment_refused",
                    contract_id,
                    line,
                    f"the core model refused the fragment: {refused}",
                )

        drawn: set[str] = set()
        for contract_id, node, block_name, view, marker_line, block in diagrams:
            drawn.add(contract_id)
            check_caption(node, contract_id, block)
            if contract_id not in fragments:
                add(
                    "diagram_without_fragment",
                    contract_id,
                    marker_line,
                    f"no contract-fragment marker names {contract_id}",
                )
                continue
            fragment = loaded[contract_id]
            if fragment is None:
                continue
            if fragment.kind != block_name:
                add(
                    "fragment_refused",
                    contract_id,
                    fragments[contract_id][0],
                    f"the marker names block {block_name} but the fragment holds a {fragment.kind}",
                )
                continue
            kind_name = fragment.kind.replace("_", " ")
            drawing = fragment.drawings.get(view)
            if (
                fragment.kind in rules.full_view_only_kinds and view != rules.full_view
            ) or drawing is None:
                add(
                    "view_not_supported",
                    contract_id,
                    marker_line,
                    f"a {kind_name} has only the full view",
                )
                continue
            compare(contract_id, drawing, block)

        for contract_id, (line, _) in fragments.items():
            if contract_id not in drawn:
                add(
                    "fragment_without_diagram",
                    contract_id,
                    line,
                    f"no diagram-contract marker names {contract_id}",
                )

        return ModelDiagramDriftReport(
            issues=tuple(sorted(issues, key=lambda issue: issue.line_number or 0)),
            diagrams_checked=len(diagrams),
            fragments_found=len(fragments),
        )
