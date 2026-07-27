# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Cross-boundary regression: the 3 canon-shape-rank1 def-B flips (OMN-14629)
dispatch correctly through the REAL runtime_local_adapter, not a hand-built
envelope.

Each flipped node's ``handle(request) -> response`` signature is exercised via
``LocalRuntimeBusAdapter.on_message`` — the actual bus-message deserialization
+ typed-dispatch + result-publish path the deployed runtime uses — proving the
adapter's coercion (``_invoke_handle_method`` / magic-param recognition) still
adapts the new signature after the OMN-14355 def-B flip. A hand-built
``ModelEventEnvelope`` would only prove the OLD async-envelope path (removed by
this change) still exists; it would not prove the runtime boundary.
"""

from __future__ import annotations

import json
from typing import cast

import pytest

from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import (
    ModelProfileReference,
)
from omnibase_core.models.nodes.contract_resolve import (
    ModelContractResolveInput,
    ModelContractResolveOutput,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_backend_secret_discipline_input import (
    ModelBackendSecretDisciplineInput,
)
from omnibase_core.models.validation.model_backend_secret_discipline_output import (
    ModelBackendSecretDisciplineOutput,
)
from omnibase_core.models.validation.model_routing_authority_check_input import (
    ModelRoutingAuthorityCheckInput,
)
from omnibase_core.models.validation.model_routing_authority_check_output import (
    ModelRoutingAuthorityCheckOutput,
)
from omnibase_core.models.validation.model_routing_contract_entry import (
    ModelRoutingContractEntry,
)
from omnibase_core.nodes.node_contract_resolve_compute import NodeContractResolveCompute
from omnibase_core.nodes.node_routing_authority_check_compute.handler import (
    NodeRoutingAuthorityCheckCompute,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_callable_target import (
    ProtocolLocalRuntimeCallableTarget,
)
from omnibase_core.runtime.runtime_local_adapter import LocalRuntimeBusAdapter
from omnibase_core.validation.validator_backend_secret_discipline import (
    HandlerBackendSecretDisciplineCompute,
)

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
async def test_backend_secret_discipline_dispatches_through_real_adapter() -> None:
    """A real bus message (bytes) drives handle() and the result is published."""
    handler = HandlerBackendSecretDisciplineCompute()
    adapter, bus = _adapter(
        handler=handler,
        input_model_cls=ModelBackendSecretDisciplineInput,
        output_topic="onex.evt.core.backend-secret-discipline-result.v1",
    )
    payload = {
        "config_contents": {
            "bifrost.yaml": (
                "backends:\n"
                "  - backend_id: cloud-gemini\n"
                "    tier: cheap_cloud\n"
                "    secret_ref: llm.gemini.api_key\n"
            )
        },
    }
    await adapter.on_message(_FakeMsg(json.dumps(payload).encode("utf-8")))

    assert len(bus.published) == 1
    topic, raw = bus.published[0]
    assert topic == "onex.evt.core.backend-secret-discipline-result.v1"
    output = ModelBackendSecretDisciplineOutput.model_validate_json(raw)
    assert output.passed is True
    assert output.literal_credential_violations == []


@pytest.mark.asyncio
async def test_backend_secret_discipline_leak_dispatches_and_fails_closed() -> None:
    """A leaked credential in the bus payload produces a failed verdict on the bus."""
    handler = HandlerBackendSecretDisciplineCompute()
    adapter, bus = _adapter(
        handler=handler,
        input_model_cls=ModelBackendSecretDisciplineInput,
        output_topic="onex.evt.core.backend-secret-discipline-result.v1",
    )
    payload = {
        "config_contents": {
            "routing.yaml": 'api_key: "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrst"\n'  # pragma: allowlist secret
        },
    }
    await adapter.on_message(_FakeMsg(json.dumps(payload).encode("utf-8")))

    output = ModelBackendSecretDisciplineOutput.model_validate_json(bus.published[0][1])
    assert output.passed is False
    assert len(output.literal_credential_violations) >= 1


@pytest.mark.asyncio
async def test_contract_resolve_dispatches_through_real_adapter() -> None:
    """The renamed resolve()->handle() still adapts through the runtime boundary."""
    node = NodeContractResolveCompute()
    adapter, bus = _adapter(
        handler=node,
        input_model_cls=ModelContractResolveInput,
        output_topic="onex.evt.core.contract-resolve-completed.v1",
    )
    base_profile_ref = ModelProfileReference(profile="compute_pure", version="1.0.0")
    patch = ModelContractPatch(
        extends=base_profile_ref,
        name="cross_boundary_fixture",
        node_version=ModelSemVer(major=1, minor=0, patch=0),
    )
    payload = ModelContractResolveInput(
        base_profile_ref=base_profile_ref,
        patches=[patch],
    ).model_dump(mode="json")

    await adapter.on_message(_FakeMsg(json.dumps(payload).encode("utf-8")))

    assert len(bus.published) == 1
    topic, raw = bus.published[0]
    assert topic == "onex.evt.core.contract-resolve-completed.v1"
    output = ModelContractResolveOutput.model_validate_json(raw)
    assert len(output.resolved_hash) == 64
    assert len(output.patch_hashes) == 1


@pytest.mark.asyncio
async def test_routing_authority_check_dispatches_through_real_adapter() -> None:
    """The new handle(request) shape adapts through the runtime boundary."""
    node = NodeRoutingAuthorityCheckCompute()
    adapter, bus = _adapter(
        handler=node,
        input_model_cls=ModelRoutingAuthorityCheckInput,
        output_topic="onex.evt.core.routing-authority-check-completed.v1",
    )
    contract_yaml = (
        "name: node_generation_consumer\n"
        "node_type: compute\n"
        "model_routing:\n"
        '  provider: "google"\n'
        '  served_model_id: "gemini-1.5-pro"\n'
        '  endpoint_ref: "gemini_pro"\n'
        '  routing_source: "bifrost_delegation.yaml"\n'
    )
    bifrost_yaml = (
        "backends:\n"
        '  - backend_id: "gemini_pro"\n'
        '    tier: "cloud"\n'
        '    endpoint_url_env: "GEMINI_PRO_URL"\n'
        "    endpoint_url: null\n"
    )
    source_content = (
        "def handle(payload):\n    return payload\n"  # clean demo-path source
    )
    payload = ModelRoutingAuthorityCheckInput(
        demo_path_contracts=(ModelRoutingContractEntry(contract_rel="contract.yaml"),),
        contract_contents={"contract.yaml": contract_yaml},
        bifrost_config_rel="bifrost.yaml",
        bifrost_config_content=bifrost_yaml,
        demo_path_sources=("handler.py",),
        source_contents={"handler.py": source_content},
        residue_entries=(),
        residue_contents={},
    ).model_dump(mode="json")

    await adapter.on_message(_FakeMsg(json.dumps(payload).encode("utf-8")))

    assert len(bus.published) == 1
    topic, raw = bus.published[0]
    assert topic == "onex.evt.core.routing-authority-check-completed.v1"
    output = ModelRoutingAuthorityCheckOutput.model_validate_json(raw)
    assert output.positive_ok is True
    assert output.negative_ok is True
    assert output.passed is True
