# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""In-memory implementations are obtained from the container, never built by callers (OMN-21788)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.container.container_auto_config import (
    local_event_bus,
    local_trace_store,
)
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore
from omnibase_core.protocols.storage.protocol_trace_store import ProtocolTraceStore
from omnibase_core.services.diff.service_diff_in_memory_store import (
    ServiceDiffInMemoryStore,
)
from omnibase_core.services.trace.service_trace_in_memory_store import (
    ServiceTraceInMemoryStore,
)
from omnibase_core.validation.validator_contracts_and_di import (
    ValidatorContractsAndDi,
)

pytestmark = pytest.mark.unit

_SRC = Path(__file__).resolve().parents[3] / "src/omnibase_core"
_SLICE = (
    "event_bus/testing/fixture_event_bus_substrate.py",
    "mixins/mixin_trace_capture.py",
    "nodes/node_source_file_gather_effect/runtime_shared_token_policy.py",
    "runtime/harness/harness_dispatch.py",
    "runtime/runtime_local.py",
    "services/diff/service_diff_in_memory_store.py",
    "services/trace/service_trace_in_memory_store.py",
    "validation/doc_content_scan/runtime_doc_content_scan.py",
    "validation/localhost_url/runtime_localhost_url.py",
    "validation/no_faked_boundary/runtime_no_faked_boundary.py",
    "validation/pin_hygiene/runtime_pin_hygiene.py",
    "validation/todo_marker/runtime_todo_marker.py",
)


def test_provider_passes_bus_options_through() -> None:
    bus = local_event_bus(environment="staging", group="g")
    assert isinstance(bus, EventBusInmemory)
    assert bus.environment == "staging"
    assert bus.group == "g"


def test_provider_returns_a_fresh_trace_store_conforming_to_its_protocol() -> None:
    first, second = local_trace_store(), local_trace_store()
    assert isinstance(first, ServiceTraceInMemoryStore)
    assert isinstance(first, ProtocolTraceStore)
    assert first is not second


def test_diff_store_conforms_to_its_protocol() -> None:
    assert isinstance(ServiceDiffInMemoryStore(), ProtocolDiffStore)


@pytest.mark.parametrize("relative", _SLICE)
def test_slice_module_has_no_inmemory_outside_injection_finding(relative: str) -> None:
    issues = ValidatorContractsAndDi().validate([_SRC / relative]).issues
    assert [
        i.rule_name for i in issues if i.rule_name == "inmemory_outside_injection"
    ] == []


def test_checker_still_flags_a_hand_built_bus(tmp_path: Path) -> None:
    """Positive control: the zero above is not a checker that sees nothing."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    module = repo / "src/omnibase_core/runtime/runtime_probe.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        "from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory\n\n"
        "bus = EventBusInmemory()\n"
    )
    issues = ValidatorContractsAndDi().validate([module]).issues
    assert [i.rule_name for i in issues] == ["inmemory_outside_injection"]
