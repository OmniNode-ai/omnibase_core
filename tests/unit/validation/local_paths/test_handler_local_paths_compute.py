# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit + equivalence tests for the local-paths COMPUTE validator (OMN-13293, G1).

These tests assert two things:

1. The generated COMPUTE handler is shaped canonically (ProtocolMessageHandler,
   COMPUTE kind, returns ``result``, pure) and runs over the in-memory bus.
2. Behavioral EQUIVALENCE with the hand-authored ground truth
   ``omnibase_core.validation.validator_local_paths.ValidatorLocalPaths`` — the
   acceptance authority for landing the generated source. For every fixture, the
   COMPUTE handler's ``flagged`` verdict must equal the ground truth's verdict.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.validation.local_paths.handler import (
    HandlerLocalPathsCompute,
    scan_source,
)
from omnibase_core.validation.local_paths.models import ModelLocalPathScanInput
from omnibase_core.validation.validator_local_paths import (
    _LOCAL_PATH_PATTERNS,
    _SUPPRESSION_MARKER,
)

# --- Equivalence corpus (verdicts derived from the ground truth) -----------
# violation/clean lines whose required verdict is COMPUTED below from the real
# ValidatorLocalPaths per-line logic, so the corpus cannot drift from the ground
# truth. Mirrors the G1 acceptance corpus used during generation.
_VIOLATION_LINES: tuple[str, ...] = (
    '"/Users/alice/Code/project"  # comment',  # test-literal-ok: corpus violation fixture
    'Path("/Volumes/DISK/Code/worktrees")',  # test-literal-ok: corpus violation fixture
    'CACHE = "/home/runner/.cache/onex"',  # test-literal-ok: corpus violation fixture
    r'WIN = "C:\Users\bob\Documents"',  # test-literal-ok: corpus violation fixture
    'WIN = "c:/Users/bob/Documents"',  # test-literal-ok: corpus violation fixture
    'subprocess.run(["cp", "/Users/dev/file", "d"])',  # test-literal-ok: corpus violation fixture
    'import os\nB = "/Users/ci/workspace/repo"\n',  # test-literal-ok: corpus violation fixture (2nd line)
)
_CLEAN_LINES: tuple[str, ...] = (
    'CONFIG = Path(__file__).parent / "c.yaml"',
    'ROOT = Path(os.environ["OMNI_HOME"])',
    'D = "/Users/jonah/Code/omni_home"  # local-path-ok',  # test-literal-ok: suppressed
    '"/node_modules/some/pkg/index.js"',
    'BREW = "/usr/local/bin/python3.13"',  # test-literal-ok: near-miss, must stay clean
    'HOST = "/homelab/data/cache"',  # test-literal-ok: near-miss, must stay clean
    'NOTE = "see /Users for the home dirs"',  # test-literal-ok: no trailing slash, clean
    'API = "https://example.com/users/alice/x"',  # test-literal-ok: URL, lowercase, clean
)


def _ground_truth_flags(source: str) -> bool:
    """Reproduce ValidatorLocalPaths per-line verdict (the acceptance authority)."""
    for line in source.splitlines():
        if _SUPPRESSION_MARKER in line:
            continue
        for _name, pattern in _LOCAL_PATH_PATTERNS:
            if pattern.search(line):
                return True
    return False


@pytest.mark.unit
def test_handler_is_canonical_compute_protocol() -> None:
    handler = HandlerLocalPathsCompute()
    assert isinstance(handler, ProtocolMessageHandler)
    assert handler.node_kind is EnumNodeKind.COMPUTE
    assert handler.handler_id == "validator-local-paths-compute"


@pytest.mark.unit
@pytest.mark.parametrize("source", list(_VIOLATION_LINES))
def test_scan_source_flags_every_violation(source: str) -> None:
    result = scan_source(source, path="t.py")
    assert result.flagged is True
    assert len(result.findings) >= 1
    # ground truth agrees this is a violation
    assert _ground_truth_flags(source) is True


@pytest.mark.unit
@pytest.mark.parametrize("source", list(_CLEAN_LINES))
def test_scan_source_passes_every_clean(source: str) -> None:
    result = scan_source(source, path="t.py")
    assert result.flagged is False
    assert result.findings == ()
    assert _ground_truth_flags(source) is False


@pytest.mark.unit
@pytest.mark.parametrize("source", [*_VIOLATION_LINES, *_CLEAN_LINES])
def test_equivalence_with_ground_truth(source: str) -> None:
    """The COMPUTE verdict must equal the hand-authored ground-truth verdict."""
    compute_flags = scan_source(source).flagged
    assert compute_flags == _ground_truth_flags(source), (
        f"COMPUTE/ground-truth disagree on {source!r}: "
        f"compute={compute_flags} ground_truth={_ground_truth_flags(source)}"
    )


@pytest.mark.unit
def test_findings_are_stably_ordered() -> None:
    # two violations on two lines -> findings in (line, column) order
    src = '"/Users/a/x/"\n"/Volumes/D/y/"'  # test-literal-ok: ordering fixture
    findings = scan_source(src).findings
    assert [f.line for f in findings] == [1, 2]


@pytest.mark.unit
def test_suppression_marker_suppresses_line() -> None:
    src = (
        'X = "/Users/jonah/x/"  # local-path-ok'  # test-literal-ok: suppression fixture
    )
    assert scan_source(src).flagged is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handler_returns_compute_result_over_envelope() -> None:
    handler = HandlerLocalPathsCompute()
    envelope: ModelEventEnvelope[ModelLocalPathScanInput] = ModelEventEnvelope(
        payload=ModelLocalPathScanInput(
            content='X = "/Users/jonah/x/"',  # test-literal-ok: handler fixture
            path="t.py",
        )
    )
    output = await handler.handle(envelope)
    assert output.node_kind is EnumNodeKind.COMPUTE
    assert output.result is not None
    assert output.result.flagged is True
    assert output.input_envelope_id == envelope.envelope_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runner_dispatches_over_in_memory_bus() -> None:
    """End-to-end: the COMPUTE handler runs over the real in-memory bus backend."""
    from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
    from omnibase_core.validation.local_paths.runtime_local_paths import (
        LocalPathsBusRunner,
    )

    bus = EventBusInmemory()
    await bus.start()
    try:
        runner = LocalPathsBusRunner(bus)
        results = await runner.scan_inputs(
            [
                ModelLocalPathScanInput(
                    content='X = "/Users/jonah/x/"',  # test-literal-ok: bus fixture
                    path="v.py",
                ),
                ModelLocalPathScanInput(content="X = 1", path="c.py"),
            ]
        )
    finally:
        await bus.shutdown()

    by_path = {r.path: r for r in results}
    assert by_path["v.py"].flagged is True
    assert by_path["c.py"].flagged is False
