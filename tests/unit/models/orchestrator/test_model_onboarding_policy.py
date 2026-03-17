# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelOnboardingPolicy."""

from uuid import uuid4

from omnibase_core.models.orchestrator import ModelOnboardingPolicy

POLICY_ID_1 = uuid4()
POLICY_ID_2 = uuid4()
POLICY_ID_3 = uuid4()


class TestModelOnboardingPolicy:
    """Tests for ModelOnboardingPolicy construction, serialization, and validation."""

    def test_construct_minimal(self) -> None:
        policy = ModelOnboardingPolicy(
            policy_id=POLICY_ID_1,
            policy_name="standalone_quickstart",
            description="Minimal path to running a standalone node",
        )
        assert policy.policy_id == POLICY_ID_1
        assert policy.policy_name == "standalone_quickstart"
        assert policy.description == "Minimal path to running a standalone node"
        assert policy.required_entry_capabilities == []
        assert policy.target_capabilities == []
        assert policy.skip_steps == []
        assert policy.max_estimated_minutes is None
        assert policy.allow_simulation is False
        assert policy.allow_deferral is False

    def test_construct_full(self) -> None:
        policy = ModelOnboardingPolicy(
            policy_id=POLICY_ID_2,
            policy_name="contributor_local",
            description="Full local development setup",
            required_entry_capabilities=["python_installed"],
            target_capabilities=["event_bus_connected", "secrets_configured"],
            skip_steps=["start_omnidash"],
            max_estimated_minutes=20,
            allow_simulation=True,
            allow_deferral=True,
        )
        assert policy.policy_name == "contributor_local"
        assert policy.required_entry_capabilities == ["python_installed"]
        assert policy.target_capabilities == [
            "event_bus_connected",
            "secrets_configured",
        ]
        assert policy.skip_steps == ["start_omnidash"]
        assert policy.max_estimated_minutes == 20
        assert policy.allow_simulation is True
        assert policy.allow_deferral is True

    def test_serialize_round_trip(self) -> None:
        policy = ModelOnboardingPolicy(
            policy_id=POLICY_ID_1,
            policy_name="full_platform",
            description="Full platform setup",
            target_capabilities=["omnidash_running"],
            max_estimated_minutes=45,
        )
        data = policy.model_dump()
        policy2 = ModelOnboardingPolicy.model_validate(data)
        assert policy == policy2

    def test_json_round_trip(self) -> None:
        policy = ModelOnboardingPolicy(
            policy_id=POLICY_ID_2,
            policy_name="standalone_quickstart",
            description="Quick start",
            target_capabilities=["first_node_running"],
        )
        json_str = policy.model_dump_json()
        policy2 = ModelOnboardingPolicy.model_validate_json(json_str)
        assert policy == policy2

    def test_defaults_are_empty_lists(self) -> None:
        policy = ModelOnboardingPolicy(
            policy_id=POLICY_ID_1,
            policy_name="test",
            description="test policy",
        )
        # Verify list defaults are independent instances
        policy2 = ModelOnboardingPolicy(
            policy_id=POLICY_ID_2,
            policy_name="test2",
            description="test policy 2",
        )
        policy.target_capabilities.append("x")
        assert policy2.target_capabilities == []

    def test_re_exported_from_orchestrator_init(self) -> None:
        """Verify ModelOnboardingPolicy is accessible from the orchestrator package."""
        from omnibase_core.models.orchestrator import (
            ModelOnboardingPolicy as Imported,
        )

        assert Imported is ModelOnboardingPolicy
