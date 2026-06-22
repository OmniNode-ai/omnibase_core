# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# onex-allow-file-todo-marker OMN-13480 reason="corpus fixtures + assertions name the TODO/FIXME/HACK marker token the scanner-under-test must flag; the tokens are the subject"
"""Unit + corpus-acceptance tests for the TODO-marker COMPUTE validator (OMN-13480, G2).

These tests assert two things:

1. The generated COMPUTE handler is shaped canonically (ProtocolMessageHandler,
   COMPUTE kind, returns ``result``, pure) and runs over the in-memory bus — the
   same two-transport seam as the G1 local-paths canary and the G2 private-IP
   validator.
2. The committed ``scan_source`` reproduces the acceptance corpus verdicts that
   gated the generation run. The corpus
   (``node_generation_consumer.validator_corpora.corpus_todo_marker.TODO_MARKER_CORPUS``)
   is the acceptance authority; it lives in omnimarket (the generation producer)
   and cannot be imported here (core ↛ market layering), so its fixtures are
   re-pinned inline below. Every violation fixture must be flagged; every clean
   fixture must pass. The boundary cases (marker-substring identifier, lowercase
   ``hackathon`` substring, lowercase "to do" prose) are what make this a real
   gate, not a curated demo.

The marker tokens here are assembled from string parts (``"TO" + "DO"`` etc.) so
the literal token never appears verbatim in this source — exactly as the omnimarket
corpus does it — keeping the marker gate (which scans this repo's own source) from
flagging the test that pins it. The assembled *fixture values* still carry the real
marker the scanner must flag.
"""

from __future__ import annotations

import asyncio

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.validation.todo_marker.handler import (
    HandlerTodoMarkerCompute,
    scan_source,
)
from omnibase_core.validation.todo_marker.models import ModelTodoMarkerScanInput

# Marker tokens assembled at module load so the literal token never appears
# verbatim in this file (mirrors the omnimarket corpus convention).
_HASH = "#"
_TODO = "TO" + "DO"
_FIXME = "FIX" + "ME"
_HACK = "HA" + "CK"

# --- Acceptance corpus (re-pinned from the omnimarket corpus the generation run
# was accepted against). Each entry is the fixture source. ---------------------
_VIOLATION_FIXTURES: tuple[str, ...] = (
    f"{_HASH} {_TODO}: resolve the endpoint from the contract before merge",  # v-base-todo
    f"{_HASH} {_FIXME}: this loop double-counts retries",  # v-base-fixme
    f"    value = raw  {_HASH} {_HACK}: bypassing validation for now",  # v-mut-hack
    f"{_HASH} {_TODO} wire the projection consumer",  # v-mut-todo-no-colon
    f"raise NotImplementedError  {_HASH} {_FIXME}(jonah) implement the handler",  # v-mut-fixme-bracketed
)
_CLEAN_FIXTURES: tuple[str, ...] = (
    f"result = handler.handle(envelope)  {_HASH} resolves via DI container",  # c-base-clean-code
    f'{_TODO}LIST_TABLE = "user_{_TODO.lower()}list"',  # c-mut-todo-substring
    'dataset = "mastodon-hackathon-corpus"',  # c-mut-hack-substring
    'DESC = "items still to do are tracked in Linear"',  # c-mut-lowercase-prose
)


# ---------------------------------------------------------------------------
# Corpus acceptance — the verdict that gated the generation run
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("source", _VIOLATION_FIXTURES)
def test_every_violation_fixture_is_flagged(source: str) -> None:
    result = scan_source(source)
    assert result.flagged is True, f"violation fixture not flagged: {source!r}"
    assert result.findings, "a flagged result must carry at least one finding"


@pytest.mark.unit
@pytest.mark.parametrize("source", _CLEAN_FIXTURES)
def test_every_clean_fixture_passes(source: str) -> None:
    result = scan_source(source)
    assert result.flagged is False, f"clean fixture false-flagged: {source!r}"
    assert result.findings == ()


@pytest.mark.unit
def test_finding_carries_marker_line_context() -> None:
    result = scan_source(f"    value = raw  {_HASH} {_HACK}: bypassing validation")
    assert result.flagged is True
    (finding,) = result.findings
    assert finding.marker == _HACK
    assert finding.line == 1
    assert _HACK in finding.context


@pytest.mark.unit
def test_all_three_markers_are_flagged() -> None:
    assert scan_source(f"{_HASH} {_TODO}: x").findings[0].marker == _TODO
    assert scan_source(f"{_HASH} {_FIXME}: x").findings[0].marker == _FIXME
    assert scan_source(f"{_HASH} {_HACK}: x").findings[0].marker == _HACK


@pytest.mark.unit
def test_marker_as_identifier_substring_is_not_flagged() -> None:
    # Word boundary: the token inside a larger identifier must NOT match.
    assert scan_source(f"{_TODO}LIST = 1").flagged is False
    assert scan_source('x = "mastodon"').flagged is False


# ---------------------------------------------------------------------------
# Canonical COMPUTE handler shape + two-transport (in-memory bus) dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handler_is_a_protocol_message_handler() -> None:
    handler = HandlerTodoMarkerCompute()
    assert isinstance(handler, ProtocolMessageHandler)
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.handler_id == "validator-todo-marker-compute"


@pytest.mark.unit
def test_handler_returns_compute_result() -> None:
    handler = HandlerTodoMarkerCompute()
    envelope: ModelEventEnvelope[ModelTodoMarkerScanInput] = ModelEventEnvelope(
        payload=ModelTodoMarkerScanInput(content=f"{_HASH} {_TODO}: x", path="f.py")
    )
    output = asyncio.run(handler.handle(envelope))
    assert output.result is not None
    assert output.result.flagged is True
    assert output.result.path == "f.py"


@pytest.mark.unit
def test_runner_over_in_memory_bus_flags_and_passes() -> None:
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.validation.todo_marker.runtime_todo_marker import (
        TodoMarkerBusRunner,
    )

    async def _run() -> None:
        bus = EventBusInmemory()
        await bus.start()
        try:
            runner = TodoMarkerBusRunner(bus)
            results = await runner.scan_inputs(
                [
                    ModelTodoMarkerScanInput(
                        content=f"{_HASH} {_TODO}: fix it", path="bad.py"
                    ),
                    ModelTodoMarkerScanInput(
                        content="x = handler.handle(e)", path="ok.py"
                    ),
                ]
            )
        finally:
            await bus.shutdown()
        by_path = {r.path: r for r in results}
        assert by_path["bad.py"].flagged is True
        assert by_path["ok.py"].flagged is False

    asyncio.run(_run())


@pytest.mark.unit
def test_findings_are_order_independent() -> None:
    # Two violations on different lines: stable order by line.
    src = f"A  {_HASH} {_TODO}: a\nB  {_HASH} {_FIXME}: b"
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [1, 2]


# ---------------------------------------------------------------------------
# Suppression escape hatches
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_line_marker_suppresses_only_that_line() -> None:
    src = (
        f"A  {_HASH} {_TODO}: a  {_HASH} onex-allow-todo-marker approved\n"  # suppressed
        f"B  {_HASH} {_FIXME}: b"  # still flagged
    )
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [2]


@pytest.mark.unit
def test_file_marker_suppresses_the_whole_file() -> None:
    # A documentation-heavy file whose subject IS the marker token: one file-level
    # marker suppresses every finding so rendered docs stay clean.
    src = (
        f"{_HASH} onex-allow-file-todo-marker doc fixture\n"
        f"A  {_HASH} {_TODO}: a\n"
        f"B  {_HASH} {_FIXME}: b\n"
        f"C  {_HASH} {_HACK}: c"
    )
    result = scan_source(src)
    assert result.flagged is False
    assert result.findings == ()
