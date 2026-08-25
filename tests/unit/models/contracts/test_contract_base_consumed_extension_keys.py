# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContractBase declares exactly the top-level keys the runtime consumes (OMN-16451).

``event_bus``, ``mcp`` and ``intent_consumption`` are read from contract YAML
by the runtime (subscription wiring, the MCP adapter, the intent routing
loader) and must therefore be declared, typed fields. Keys with no runtime
reader stay undeclared and are rejected by ``extra="forbid"``.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts import (
    ModelAlgorithmConfig,
    ModelAlgorithmFactorConfig,
    ModelContractCompute,
    ModelPerformanceRequirements,
)
from omnibase_core.models.contracts.model_contract_intent_consumption import (
    ModelContractIntentConsumption,
)
from omnibase_core.models.contracts.model_contract_mcp_config import (
    ModelContractMcpConfig,
)
from omnibase_core.models.contracts.subcontracts.model_event_bus_subcontract import (
    ModelEventBusSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _create_minimal_compute(**overrides: object) -> ModelContractCompute:
    defaults: dict[str, object] = {
        "name": "test_node",
        "contract_version": ModelSemVer(major=1, minor=0, patch=0),
        "description": "Test compute contract",
        "node_type": EnumNodeType.COMPUTE_GENERIC,
        "input_model": "omnibase_core.models.ModelTestInput",
        "output_model": "omnibase_core.models.ModelTestOutput",
        "algorithm": ModelAlgorithmConfig(
            algorithm_type="test",
            factors={
                "f1": ModelAlgorithmFactorConfig(
                    weight=1.0,
                    calculation_method="default",
                ),
            },
        ),
        "performance": ModelPerformanceRequirements(single_operation_max_ms=1000),
    }
    defaults.update(overrides)
    return ModelContractCompute(**defaults)  # type: ignore[arg-type]


_EVENT_BUS_YAML: dict[str, object] = {
    "version": {"major": 1, "minor": 0, "patch": 0},
    "subscribe_topics": ["onex.evt.platform.node-introspection.v1"],
    "publish_topics": ["onex.evt.platform.node-registration-result.v1"],
    "dlq_topics": ["onex.dlq.omnibase-infra.platform.v1"],
}


@pytest.mark.unit
class TestContractBaseConsumedExtensionKeys:
    def test_extension_keys_default_to_none(self) -> None:
        contract = _create_minimal_compute()
        assert contract.event_bus is None
        assert contract.mcp is None
        assert contract.intent_consumption is None

    def test_event_bus_parses_as_subcontract_from_yaml_shape(self) -> None:
        contract = _create_minimal_compute(event_bus=_EVENT_BUS_YAML)
        assert isinstance(contract.event_bus, ModelEventBusSubcontract)
        assert contract.event_bus.subscribe_topics == [
            "onex.evt.platform.node-introspection.v1"
        ]
        assert contract.event_bus.dlq_topics == ["onex.dlq.omnibase-infra.platform.v1"]

    def test_mcp_parses_as_typed_config(self) -> None:
        contract = _create_minimal_compute(
            mcp={
                "expose": True,
                "tool_name": "register_node",
                "description": "Register a node.",
                "timeout_seconds": 30,
            }
        )
        assert isinstance(contract.mcp, ModelContractMcpConfig)
        assert contract.mcp.tool_name == "register_node"

    def test_intent_consumption_parses_as_typed_config(self) -> None:
        contract = _create_minimal_compute(
            intent_consumption={
                "intent_routing_table": {
                    "postgres.upsert_registration": "node_registry_effect"
                }
            }
        )
        assert isinstance(contract.intent_consumption, ModelContractIntentConsumption)
        assert contract.intent_consumption.intent_routing_table == {
            "postgres.upsert_registration": "node_registry_effect"
        }

    @pytest.mark.parametrize(
        "undeclared_key",
        [
            "time_injection",
            "projection_reader",
            "error_handling",
            "health_check",
            "metadata",
        ],
    )
    def test_keys_without_a_runtime_reader_stay_forbidden(
        self, undeclared_key: str
    ) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _create_minimal_compute(**{undeclared_key: {"enabled": True}})
        assert any(
            e["type"] == "extra_forbidden" and e["loc"] == (undeclared_key,)
            for e in exc_info.value.errors()
        )

    def test_malformed_event_bus_is_rejected_not_dropped(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            _create_minimal_compute(event_bus={**_EVENT_BUS_YAML, "not_a_field": True})
        assert any(
            e["type"] == "extra_forbidden" and e["loc"] == ("event_bus", "not_a_field")
            for e in exc_info.value.errors()
        )
