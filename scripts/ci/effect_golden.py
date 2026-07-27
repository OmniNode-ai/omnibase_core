# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Effect-golden readback oracle for EFFECT nodes (OMN-14358).

The EFFECT analog of ``compute_golden``. An EFFECT node's "output" is not a return
value — it is the SIDE EFFECT (a published event, a written file). This harness
proves the DECLARED side-effects actually happened by READBACK against a REAL
observable sink, NOT by "didn't throw".

Why not "didn't throw": a ``MagicMock`` event bus makes ``bus.publish(...)``
succeed silently with no real sink, so a "didn't throw" check passes even when
nothing was published (the OMN-14294 blind spot). Only a readback against a real
recording sink distinguishes a real publish from a mock/suppressed one — the T3
canary (Task #44) proved this discriminates (suppressed effect → readback FAIL
while "didn't throw" stayed identically True).

Effects are asserted CONJUNCTIVELY: every declared topic must have a captured
event AND every declared file glob must match a non-empty file. A volatile mask
excludes minted ``run_id``/``timestamp``/``correlation_id`` from effect-payload
equivalence.

Self-contained (does not import ``compute_golden``, which lives on a separate PR);
the mask/diff machinery is consolidated once both land.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model


class RecordingEventSink:
    """A REAL observable sink — appends every publish so effects can be read back.

    This is the anti-MagicMock: the readback oracle reads ``captured``, so a
    suppressed or mocked publish is visibly absent instead of silently "succeeding".
    """

    def __init__(self) -> None:
        self.captured: list[tuple[str, dict[str, Any]]] = []

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.captured.append((topic, payload))


class ModelEffectReadback(BaseModel):
    """Verdict of reading back an EFFECT node's DECLARED side-effects."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    published_ok: bool
    files_ok: bool
    declared_topics: list[str] = Field(default_factory=list)
    captured_topics: list[str] = Field(default_factory=list)
    declared_file_globs: list[str] = Field(default_factory=list)
    matched_files: list[str] = Field(default_factory=list)
    missing_effects: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.ok != (self.published_ok and self.files_ok):
            raise ValueError("ok must equal (published_ok and files_ok)")
        if self.ok and self.missing_effects:
            raise ValueError("ok=True forbids missing_effects")
        if not self.ok and not self.missing_effects:
            raise ValueError("ok=False requires at least one missing_effect")
        return self


class _ContractPublishTopics(BaseModel):
    """Minimal validated slice of a contract.yaml — just the declared topics."""

    model_config = ConfigDict(extra="ignore")
    publish_topics: list[str] = Field(default_factory=list)


def parse_publish_topics(contract_path: str | Path) -> list[str]:
    """Contract-driven declared topics: the node's ``contract.yaml`` publish_topics.

    Validates the contract slice via Pydantic (no manual dict access).
    """
    model = load_and_validate_yaml_model(Path(contract_path), _ContractPublishTopics)
    return model.publish_topics


def _glob_has_nonempty_match(root: Path, pattern: str) -> bool:
    return any(p.is_file() and p.read_bytes().strip() for p in root.glob(pattern))


def readback_effects(
    *,
    sink: RecordingEventSink,
    declared_topics: list[str],
    declared_file_globs: list[str],
    root: Path,
) -> ModelEffectReadback:
    """Assert ALL declared effects actually happened — conjunctively, by readback.

    A declared topic passes iff the recording sink captured ≥1 event on it. A
    declared file glob passes iff it matches ≥1 non-empty file under ``root``.
    NOT "didn't throw" — absence of an effect is a FAIL, never a silent pass.
    """
    captured_topics = sorted({t for t, _ in sink.captured})
    missing: list[str] = []

    for topic in declared_topics:
        if topic not in captured_topics:
            missing.append(f"topic:{topic}")

    matched: list[str] = []
    for pattern in declared_file_globs:
        if _glob_has_nonempty_match(root, pattern):
            matched.append(pattern)
        else:
            missing.append(f"file:{pattern}")

    published_ok = all(t in captured_topics for t in declared_topics)
    files_ok = len(matched) == len(declared_file_globs)
    return ModelEffectReadback(
        ok=(published_ok and files_ok),
        published_ok=published_ok,
        files_ok=files_ok,
        declared_topics=sorted(declared_topics),
        captured_topics=captured_topics,
        declared_file_globs=sorted(declared_file_globs),
        matched_files=sorted(matched),
        missing_effects=sorted(missing),
    )


def _apply_mask(payload: dict[str, Any], volatile_mask: list[str]) -> dict[str, Any]:
    """Remove top-level volatile keys (run_id/timestamp/correlation_id) before compare."""
    masked = json.loads(json.dumps(payload))
    for key in volatile_mask:
        masked.pop(key, None)
    return masked


def record_effect_golden(
    *,
    sink: RecordingEventSink,
    declared_topics: list[str],
    declared_file_globs: list[str],
    volatile_mask: list[str] | None = None,
) -> dict[str, Any]:
    """Serialize the observed effects (masked event payloads) as an effect golden."""
    mask = list(volatile_mask or [])
    return {
        "golden_version": "effect_golden.v1",
        "declared_topics": sorted(declared_topics),
        "declared_file_globs": sorted(declared_file_globs),
        "events": [[t, _apply_mask(p, mask)] for t, p in sink.captured],
        "volatile_mask": mask,
    }


def compare_effect_golden(
    golden: dict[str, Any], sink: RecordingEventSink
) -> list[str]:
    """Diff freshly-observed events against a golden under its volatile mask.

    Returns differing descriptions — EMPTY means the effect payloads are equivalent.
    """
    mask = list(golden.get("volatile_mask", []))
    expected = [[t, _apply_mask(p, mask)] for t, p in _events_of(golden)]
    actual = [[t, _apply_mask(p, mask)] for t, p in sink.captured]
    diffs: list[str] = []
    if len(expected) != len(actual):
        diffs.append(f"event count {len(expected)} -> {len(actual)}")
    for i, (e, a) in enumerate(zip(expected, actual, strict=False)):
        if e != a:
            diffs.append(f"event[{i}]: {e!r} != {a!r}")
    return diffs


def _events_of(golden: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(row[0], row[1]) for row in golden.get("events", [])]


__all__ = [
    "ModelEffectReadback",
    "RecordingEventSink",
    "compare_effect_golden",
    "parse_publish_topics",
    "readback_effects",
    "record_effect_golden",
]
