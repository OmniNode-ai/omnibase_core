# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Compute-behavior golden recorder + equivalence comparator (OMN-14353 canary).

A minimal, general recorder for a PURE COMPUTE node: it serializes a node's
``input -> output`` as a golden and replays it, comparing the fresh output to the
recorded one under a declared volatile-field mask. This is the equivalence-oracle
primitive a self-verifying codegen factory (tier-4b) must generalize.

NOTE — this is deliberately NOT ``omnibase_core.runtime.golden_chain.record_fixture``.
That recorder freezes an LLM provider's *response bytes* over an HTTP transport
seam (pinned to provider/model/endpoint/routing_contract/request_hash); it does
not fit a pure COMPUTE node whose golden is ``typed input -> typed output`` with
no provider/model/endpoint at all. See the OMN-14353 report for the full rationale.
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class _JsonDumpable(Protocol):
    def model_dump(self, *, mode: str = ...) -> dict[str, Any]:
        # Protocol stub body: never executed (structural typing only).
        # `pass` (not `...`) avoids CodeQL py/ineffectual-statement (alert #2591).
        pass


def _canonical(payload: Any) -> str:
    """Deterministic JSON string for structural comparison (sorted keys)."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def apply_mask(payload: dict[str, Any], volatile_mask: list[str]) -> dict[str, Any]:
    """Return a deep copy of ``payload`` with each dotted-path volatile field removed.

    Masking excludes non-deterministic fields (timestamps, uuids, ...) from the
    equivalence compare. A path segment may address a dict key at any depth;
    list elements are descended into transparently.
    """
    masked: dict[str, Any] = json.loads(json.dumps(payload))  # deep copy via round-trip
    for dotted in volatile_mask:
        _remove_path(masked, dotted.split("."))
    return masked


def _remove_path(node: Any, segments: list[str]) -> None:
    if not segments:
        return
    head, rest = segments[0], segments[1:]
    if isinstance(node, list):
        for item in node:
            _remove_path(item, segments)
        return
    if not isinstance(node, dict):
        return
    if not rest:
        node.pop(head, None)
        return
    if head in node:
        _remove_path(node[head], rest)


def diff_paths(expected: Any, actual: Any, _prefix: str = "") -> list[str]:
    """Return dotted paths where ``expected`` and ``actual`` structurally differ."""
    diffs: list[str] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            child = f"{_prefix}.{key}" if _prefix else key
            if key not in expected:
                diffs.append(f"{child} (added)")
            elif key not in actual:
                diffs.append(f"{child} (removed)")
            else:
                diffs.extend(diff_paths(expected[key], actual[key], child))
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            diffs.append(f"{_prefix} (len {len(expected)}->{len(actual)})")
        for i, (e, a) in enumerate(zip(expected, actual, strict=False)):
            diffs.extend(diff_paths(e, a, f"{_prefix}[{i}]"))
    elif expected != actual:
        diffs.append(f"{_prefix}: {expected!r} != {actual!r}")
    return diffs


def record_golden(
    *,
    output: _JsonDumpable,
    input_model: _JsonDumpable,
    volatile_mask: list[str] | None = None,
) -> dict[str, Any]:
    """Serialize a compute node's input->output as a golden record."""
    return {
        "golden_version": "compute_golden.v1",
        "input_type": type(input_model).__name__,
        "output_type": type(output).__name__,
        "input": input_model.model_dump(mode="json"),
        "output": output.model_dump(mode="json"),
        "volatile_mask": list(volatile_mask or []),
    }


def compare_output(golden: dict[str, Any], fresh_output: _JsonDumpable) -> list[str]:
    """Compare a fresh output against a golden under the golden's volatile mask.

    Returns the list of differing paths — EMPTY means equivalent.
    """
    mask = list(golden.get("volatile_mask", []))
    expected = apply_mask(golden["output"], mask)
    actual = apply_mask(fresh_output.model_dump(mode="json"), mask)
    return diff_paths(expected, actual)


def outputs_equivalent(
    a: _JsonDumpable, b: _JsonDumpable, volatile_mask: list[str]
) -> bool:
    """True iff two outputs are byte-equal after masking + canonical normalization."""
    ma = apply_mask(a.model_dump(mode="json"), volatile_mask)
    mb = apply_mask(b.model_dump(mode="json"), volatile_mask)
    return _canonical(ma) == _canonical(mb)


__all__ = [
    "apply_mask",
    "compare_output",
    "diff_paths",
    "outputs_equivalent",
    "record_golden",
]
