# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for ModelTaskClassContract and sub-models (OMN-10614)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_cloud_routing_policy import EnumCloudRoutingPolicy
from omnibase_core.models.delegation.model_definition_of_done import (
    ModelDefinitionOfDone,
)
from omnibase_core.models.delegation.model_escalation_policy import (
    ModelEscalationPolicy,
)
from omnibase_core.models.delegation.model_task_class_contract import (
    ModelTaskClassContract,
)
from omnibase_core.models.delegation.model_task_class_entry import ModelTaskClassEntry

_VALID_ENTRY_DATA: dict = {
    "required_capabilities": ["code", "tool_use"],
    "pricing_ceiling_per_1k_tokens": 0.01,
    "latency_sla_p99_ms": 5000,
    "cloud_routing_policy": "opt_in",
    "definition_of_done": {
        "deterministic": ["output_parses", "signature_preserved"],
        "heuristic": ["no_refusal", "min_length_chars_50"],
    },
    "escalation_policy": {
        "max_escalations": 2,
        "tier_order": ["local_mlx", "cheap_cloud", "claude_sonnet"],
    },
}

_VALID_CONTRACT_DATA: dict = {
    "version": "1",
    "task_classes": {
        "code_generation": _VALID_ENTRY_DATA,
        "documentation": {
            "required_capabilities": ["text"],
            "pricing_ceiling_per_1k_tokens": 0.005,
            "latency_sla_p99_ms": 10000,
            "cloud_routing_policy": "allowed",
            "definition_of_done": {
                "deterministic": ["output_parses"],
                "heuristic": ["no_refusal", "min_length_chars_100"],
            },
            "escalation_policy": {
                "max_escalations": 1,
                "tier_order": ["local_mlx", "cheap_cloud"],
            },
        },
        "research": {
            "required_capabilities": ["text", "reasoning"],
            "pricing_ceiling_per_1k_tokens": 0.008,
            "latency_sla_p99_ms": 15000,
            "cloud_routing_policy": "allowed",
            "definition_of_done": {
                "deterministic": ["output_parses"],
                "heuristic": ["no_refusal", "min_length_chars_200"],
            },
            "escalation_policy": {
                "max_escalations": 2,
                "tier_order": ["local_mlx", "cheap_cloud", "claude_sonnet"],
            },
        },
    },
}


@pytest.mark.unit
class TestModelDefinitionOfDone:
    def test_valid_with_both_lists(self) -> None:
        dod = ModelDefinitionOfDone(
            deterministic=["output_parses"],
            heuristic=["no_refusal"],
        )
        assert dod.deterministic == ["output_parses"]
        assert dod.heuristic == ["no_refusal"]

    def test_defaults_to_empty_lists(self) -> None:
        dod = ModelDefinitionOfDone()
        assert dod.deterministic == []
        assert dod.heuristic == []

    def test_frozen(self) -> None:
        dod = ModelDefinitionOfDone(deterministic=["output_parses"])
        with pytest.raises(Exception):
            dod.deterministic = ["changed"]  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelDefinitionOfDone.model_validate({"unknown_field": True})


@pytest.mark.unit
class TestModelEscalationPolicy:
    def test_valid_policy(self) -> None:
        policy = ModelEscalationPolicy(
            max_escalations=2,
            tier_order=["local_mlx", "cheap_cloud", "claude_sonnet"],
        )
        assert policy.max_escalations == 2
        assert len(policy.tier_order) == 3

    def test_zero_escalations_with_empty_tier_order(self) -> None:
        policy = ModelEscalationPolicy(max_escalations=0, tier_order=[])
        assert policy.max_escalations == 0

    def test_tier_order_shorter_than_max_escalations_raises(self) -> None:
        with pytest.raises(ValidationError, match="tier_order must have at least"):
            ModelEscalationPolicy(
                max_escalations=3,
                tier_order=["local_mlx", "cheap_cloud"],
            )

    def test_negative_max_escalations_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelEscalationPolicy(max_escalations=-1, tier_order=[])

    def test_frozen(self) -> None:
        policy = ModelEscalationPolicy(
            max_escalations=1, tier_order=["local_mlx", "cheap_cloud"]
        )
        with pytest.raises(Exception):
            policy.max_escalations = 5  # type: ignore[misc]


@pytest.mark.unit
class TestEnumCloudRoutingPolicy:
    def test_all_values_parse(self) -> None:
        assert EnumCloudRoutingPolicy("opt_in") is EnumCloudRoutingPolicy.OPT_IN
        assert EnumCloudRoutingPolicy("allowed") is EnumCloudRoutingPolicy.ALLOWED
        assert EnumCloudRoutingPolicy("blocked") is EnumCloudRoutingPolicy.BLOCKED

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EnumCloudRoutingPolicy("mandatory")


@pytest.mark.unit
class TestModelTaskClassEntry:
    def test_valid_entry(self) -> None:
        entry = ModelTaskClassEntry.model_validate(_VALID_ENTRY_DATA)
        assert entry.cloud_routing_policy is EnumCloudRoutingPolicy.OPT_IN
        assert entry.pricing_ceiling_per_1k_tokens == 0.01
        assert entry.latency_sla_p99_ms == 5000
        assert "output_parses" in entry.definition_of_done.deterministic

    def test_missing_pricing_ceiling_raises(self) -> None:
        data = {**_VALID_ENTRY_DATA}
        del data["pricing_ceiling_per_1k_tokens"]
        with pytest.raises(ValidationError):
            ModelTaskClassEntry.model_validate(data)

    def test_missing_latency_sla_raises(self) -> None:
        data = {**_VALID_ENTRY_DATA}
        del data["latency_sla_p99_ms"]
        with pytest.raises(ValidationError):
            ModelTaskClassEntry.model_validate(data)

    def test_invalid_cloud_routing_policy_raises(self) -> None:
        data = {**_VALID_ENTRY_DATA, "cloud_routing_policy": "mandatory"}
        with pytest.raises(ValidationError):
            ModelTaskClassEntry.model_validate(data)

    def test_negative_pricing_ceiling_raises(self) -> None:
        data = {**_VALID_ENTRY_DATA, "pricing_ceiling_per_1k_tokens": -0.001}
        with pytest.raises(ValidationError):
            ModelTaskClassEntry.model_validate(data)

    def test_zero_latency_sla_raises(self) -> None:
        data = {**_VALID_ENTRY_DATA, "latency_sla_p99_ms": 0}
        with pytest.raises(ValidationError):
            ModelTaskClassEntry.model_validate(data)

    def test_extra_fields_forbidden(self) -> None:
        data = {**_VALID_ENTRY_DATA, "surprise_field": "whoops"}
        with pytest.raises(ValidationError):
            ModelTaskClassEntry.model_validate(data)


@pytest.mark.unit
class TestModelTaskClassContract:
    def test_valid_contract_validates(self) -> None:
        contract = ModelTaskClassContract.model_validate(_VALID_CONTRACT_DATA)
        assert contract.version == "1"
        assert "code_generation" in contract.task_classes
        assert "documentation" in contract.task_classes
        assert "research" in contract.task_classes

    def test_missing_version_raises(self) -> None:
        data = {k: v for k, v in _VALID_CONTRACT_DATA.items() if k != "version"}
        with pytest.raises(ValidationError):
            ModelTaskClassContract.model_validate(data)

    def test_empty_task_classes_allowed(self) -> None:
        contract = ModelTaskClassContract(version="1")
        assert contract.task_classes == {}

    def test_serialization_round_trip(self) -> None:
        contract = ModelTaskClassContract.model_validate(_VALID_CONTRACT_DATA)
        dumped = contract.model_dump()
        restored = ModelTaskClassContract.model_validate(dumped)
        assert restored.version == contract.version
        assert set(restored.task_classes.keys()) == set(contract.task_classes.keys())

    def test_code_generation_class_entry(self) -> None:
        contract = ModelTaskClassContract.model_validate(_VALID_CONTRACT_DATA)
        cg = contract.task_classes["code_generation"]
        assert cg.cloud_routing_policy is EnumCloudRoutingPolicy.OPT_IN
        assert cg.escalation_policy.max_escalations == 2
        assert cg.escalation_policy.tier_order[0] == "local_mlx"

    def test_research_class_uses_allowed_policy(self) -> None:
        contract = ModelTaskClassContract.model_validate(_VALID_CONTRACT_DATA)
        research = contract.task_classes["research"]
        assert research.cloud_routing_policy is EnumCloudRoutingPolicy.ALLOWED

    def test_extra_fields_forbidden(self) -> None:
        data = {**_VALID_CONTRACT_DATA, "not_a_field": "extra"}
        with pytest.raises(ValidationError):
            ModelTaskClassContract.model_validate(data)

    def test_frozen(self) -> None:
        contract = ModelTaskClassContract.model_validate(_VALID_CONTRACT_DATA)
        with pytest.raises(Exception):
            contract.version = "2"  # type: ignore[misc]
