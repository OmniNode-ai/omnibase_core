# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Cross-boundary regression: the 3 canon-shape-rank2 def-B flips (OMN-14629)
dispatch correctly through the REAL runtime_local_adapter, not a hand-built
envelope.

Each flipped node's ``handle(request) -> response`` signature is exercised via
``LocalRuntimeBusAdapter.on_message`` — the actual bus-message deserialization
+ typed-dispatch + result-publish path the deployed runtime uses — proving the
adapter's coercion (``_invoke_handle_method`` / magic-param recognition) still
adapts each node's new composite-request signature after the OMN-14355 def-B
flip. A hand-built ``ModelEventEnvelope`` would only prove a hypothetical old
async-envelope path exists; it would not prove the runtime boundary these 3
nodes never had wired before this change.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import cast

import pytest

from omnibase_core.models.nodes.compliance_evidence.model_compliance_check_entry import (
    ModelComplianceCheckEntry,
)
from omnibase_core.models.nodes.compliance_evidence.model_compliance_evidence_output import (
    ModelComplianceEvidenceOutput,
)
from omnibase_core.models.nodes.compliance_evidence.model_evidence_check_detail import (
    ModelEvidenceCheckDetail,
)
from omnibase_core.models.nodes.compliance_evidence.model_evidence_report_state import (
    ModelEvidenceReportState,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_check_result import (
    ModelComplianceCheckResult,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_report_reduce_request import (
    ModelComplianceReportReduceRequest,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_report_reduce_response import (
    ModelComplianceReportReduceResponse,
)
from omnibase_core.models.nodes.compliance_report.model_compliance_report_state import (
    ModelComplianceReportState,
)
from omnibase_core.models.nodes.compliance_scan.model_compliance_scan_request import (
    ModelComplianceScanRequest,
)
from omnibase_core.models.nodes.compliance_scan.model_compliance_scan_response import (
    ModelComplianceScanResponse,
)
from omnibase_core.nodes.node_compliance_evidence_effect.handler import (
    NodeComplianceEvidenceEffect,
)
from omnibase_core.nodes.node_compliance_report_reducer.handler import (
    NodeComplianceReportReducer,
)
from omnibase_core.nodes.node_compliance_scan_compute.handler import (
    NodeComplianceScanCompute,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_callable_target import (
    ProtocolLocalRuntimeCallableTarget,
)
from omnibase_core.runtime.runtime_local_adapter import LocalRuntimeBusAdapter

pytestmark = pytest.mark.unit


class _FakeBus:
    """Records ``publish`` calls; the adapter needs only ``publish`` here."""

    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []

    async def start(self) -> None:  # pragma: no cover - unused
        return None

    async def close(self) -> None:  # pragma: no cover - unused
        return None

    async def publish(self, topic: str, key: object, value: bytes) -> object:
        self.published.append((topic, value))
        return None

    async def subscribe(
        self, topic: str, *, on_message: object, group_id: str
    ) -> object:  # pragma: no cover - unused
        return None


class _FakeMsg:
    """Stand-in for a real deserialized bus message — bytes in, like Kafka."""

    def __init__(self, value: bytes) -> None:
        self.value = value


def _adapter(
    *,
    handler: object,
    input_model_cls: type,
    output_topic: str,
) -> tuple[LocalRuntimeBusAdapter, _FakeBus]:
    bus = _FakeBus()
    adapter = LocalRuntimeBusAdapter(
        handler=cast(ProtocolLocalRuntimeCallableTarget, handler),
        handler_name=type(handler).__name__,
        input_model_cls=input_model_cls,
        output_topic=output_topic,
        bus=cast(ProtocolLocalRuntimeBus, bus),
    )
    return adapter, bus


@pytest.mark.asyncio
async def test_compliance_scan_dispatches_through_real_adapter(
    tmp_path: Path,
) -> None:
    """The new handle(request) composite shape adapts through the runtime boundary."""
    node_dir = tmp_path / "nodes" / "node_probe"
    node_dir.mkdir(parents=True)
    (node_dir / "contract.yaml").write_text(
        "node_id: node_probe\n"
        "node_kind: COMPUTE\n"
        "handler_routing:\n"
        "  default_handler: os.path:join\n"
    )

    handler = NodeComplianceScanCompute()
    adapter, bus = _adapter(
        handler=handler,
        input_model_cls=ModelComplianceScanRequest,
        output_topic="onex.evt.core.compliance-scan-batch-completed.v1",
    )
    payload = ModelComplianceScanRequest(repo_root=str(tmp_path)).model_dump(
        mode="json"
    )

    await adapter.on_message(_FakeMsg(json.dumps(payload).encode("utf-8")))

    assert len(bus.published) == 1
    topic, raw = bus.published[0]
    assert topic == "onex.evt.core.compliance-scan-batch-completed.v1"
    output = ModelComplianceScanResponse.model_validate_json(raw)
    assert len(output.results) == 1
    assert output.results[0].node_id == "node_probe"
    assert output.results[0].passed is True


@pytest.mark.asyncio
async def test_compliance_report_reducer_dispatches_through_real_adapter() -> None:
    """The composite request/response reducer shape adapts through the runtime boundary."""
    node = NodeComplianceReportReducer()
    adapter, bus = _adapter(
        handler=node,
        input_model_cls=ModelComplianceReportReduceRequest,
        output_topic="onex.evt.core.compliance-report-updated.v1",
    )
    state = ModelComplianceReportState(
        total=1,
        passed=1,
        failed=0,
        results=[ModelComplianceCheckResult(node_id="node_existing", passed=True)],
    )
    check_result = ModelComplianceCheckResult(node_id="node_new", passed=False)
    payload = ModelComplianceReportReduceRequest(
        state=state, check_result=check_result
    ).model_dump(mode="json")

    await adapter.on_message(_FakeMsg(json.dumps(payload).encode("utf-8")))

    assert len(bus.published) == 1
    topic, raw = bus.published[0]
    assert topic == "onex.evt.core.compliance-report-updated.v1"
    output = ModelComplianceReportReduceResponse.model_validate_json(raw)
    assert output.state.total == 2
    assert output.state.passed == 1
    assert output.state.failed == 1
    assert {r.node_id for r in output.state.results} == {
        "node_existing",
        "node_new",
    }
    assert output.intents == []


@pytest.mark.asyncio
async def test_compliance_evidence_effect_dispatches_through_real_adapter() -> None:
    """The new handle(request) EFFECT shape adapts through the runtime boundary
    AND performs the real durable write (not just returns a response)."""
    state_root = Path(tempfile.mkdtemp())
    published_events: list[tuple[str, object]] = []

    class _RecordingEventBus:
        def publish(self, topic: str, payload: object) -> None:
            published_events.append((topic, payload))

    handler = NodeComplianceEvidenceEffect(
        state_root,
        _RecordingEventBus(),
        "onex.evt.core.compliance-scan-completed.v1",
    )
    adapter, bus = _adapter(
        handler=handler,
        input_model_cls=ModelEvidenceReportState,
        output_topic="onex.evt.core.compliance-scan-completed.v1",
    )
    report = ModelEvidenceReportState(
        total=2,
        passed=1,
        failed=1,
        run_id="cross-boundary-run",
        results=[
            ModelEvidenceCheckDetail(
                node_id="node_x",
                passed=True,
                checks=[ModelComplianceCheckEntry(name="contract_parse", passed=True)],
            ),
            ModelEvidenceCheckDetail(
                node_id="node_y",
                passed=False,
                checks=[
                    ModelComplianceCheckEntry(name="handler_resolution", passed=False)
                ],
            ),
        ],
    )
    payload = report.model_dump(mode="json")

    await adapter.on_message(_FakeMsg(json.dumps(payload).encode("utf-8")))

    # The runtime-bus publish leg.
    assert len(bus.published) == 1
    topic, raw = bus.published[0]
    assert topic == "onex.evt.core.compliance-scan-completed.v1"
    output = ModelComplianceEvidenceOutput.model_validate_json(raw)
    assert output.run_id == "cross-boundary-run"
    assert output.total == 2
    assert output.passed == 1
    assert output.failed == 1

    # The real disk write + the handler's OWN completion-event leg (distinct
    # from the runtime bus publish above — proves handle() still performs its
    # EFFECT-node side effects, not just returns a value the adapter forwards).
    run_path = state_root / "compliance" / "runs" / "cross-boundary-run.yaml"
    assert run_path.exists()
    assert len(published_events) == 1
    assert published_events[0][0] == "onex.evt.core.compliance-scan-completed.v1"
