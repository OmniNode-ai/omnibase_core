"""
Unit tests for contract profile factory.

TDD tests for the contract profile factory system. These tests define
the expected behavior before implementation.
"""

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.errors import OnexError
from omnibase_core.models.contracts import (
    ModelContractBase,
    ModelContractCompute,
    ModelContractEffect,
    ModelContractOrchestrator,
    ModelContractReducer,
    ModelExecutionOrderingPolicy,
    ModelExecutionProfile,
)


class TestModelExecutionOrderingPolicy:
    """Tests for ModelExecutionOrderingPolicy model."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        policy = ModelExecutionOrderingPolicy()
        assert policy.strategy == "topological_sort"
        assert policy.tie_breakers == ["priority", "alphabetical"]
        assert policy.deterministic_seed is True

    def test_immutable(self) -> None:
        """Test policy is immutable (frozen)."""
        policy = ModelExecutionOrderingPolicy()
        with pytest.raises(Exception):  # ValidationError from Pydantic
            policy.strategy = "other"  # type: ignore[misc]


class TestModelExecutionProfile:
    """Tests for ModelExecutionProfile model."""

    def test_default_phases(self) -> None:
        """Test default execution phases."""
        profile = ModelExecutionProfile()
        expected_phases = [
            "preflight",
            "before",
            "execute",
            "after",
            "emit",
            "finalize",
        ]
        assert profile.phases == expected_phases

    def test_default_ordering_policy(self) -> None:
        """Test default ordering policy is created."""
        profile = ModelExecutionProfile()
        assert isinstance(profile.ordering_policy, ModelExecutionOrderingPolicy)
        assert profile.ordering_policy.strategy == "topological_sort"

    def test_custom_phases(self) -> None:
        """Test custom phases can be set."""
        custom_phases = ["init", "execute", "cleanup"]
        profile = ModelExecutionProfile(phases=custom_phases)
        assert profile.phases == custom_phases


class TestContractProfileFactory:
    """Tests for the contract profile factory functions."""

    def test_get_default_contract_profile_orchestrator(self) -> None:
        """Test generic factory returns valid orchestrator contract."""
        from omnibase_core.factories import get_default_contract_profile

        contract = get_default_contract_profile(
            node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
            profile="orchestrator_safe",
        )
        assert isinstance(contract, ModelContractBase)
        assert isinstance(contract, ModelContractOrchestrator)

    def test_get_default_contract_profile_reducer(self) -> None:
        """Test generic factory returns valid reducer contract."""
        from omnibase_core.factories import get_default_contract_profile

        contract = get_default_contract_profile(
            node_type=EnumNodeType.REDUCER_GENERIC,
            profile="reducer_fsm_basic",
        )
        assert isinstance(contract, ModelContractBase)
        assert isinstance(contract, ModelContractReducer)

    def test_get_default_contract_profile_effect(self) -> None:
        """Test generic factory returns valid effect contract."""
        from omnibase_core.factories import get_default_contract_profile

        contract = get_default_contract_profile(
            node_type=EnumNodeType.EFFECT_GENERIC,
            profile="effect_idempotent",
        )
        assert isinstance(contract, ModelContractBase)
        assert isinstance(contract, ModelContractEffect)

    def test_get_default_contract_profile_compute(self) -> None:
        """Test generic factory returns valid compute contract."""
        from omnibase_core.factories import get_default_contract_profile

        contract = get_default_contract_profile(
            node_type=EnumNodeType.COMPUTE_GENERIC,
            profile="compute_pure",
        )
        assert isinstance(contract, ModelContractBase)
        assert isinstance(contract, ModelContractCompute)

    def test_get_default_contract_profile_unknown_profile_raises(self) -> None:
        """Test unknown profile raises error."""
        from omnibase_core.factories import get_default_contract_profile

        with pytest.raises(OnexError, match="Unknown profile"):
            get_default_contract_profile(
                node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
                profile="unknown_profile",
            )

    def test_get_default_contract_profile_with_version(self) -> None:
        """Test version is applied to returned contract."""
        from omnibase_core.factories import get_default_contract_profile

        contract = get_default_contract_profile(
            node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
            profile="orchestrator_safe",
            version="2.0.0",
        )
        assert contract.version.major == 2
        assert contract.version.minor == 0
        assert contract.version.patch == 0


class TestOrchestratorProfiles:
    """Tests for orchestrator profile factory."""

    def test_get_default_orchestrator_profile_safe(self) -> None:
        """Test orchestrator_safe profile returns valid contract."""
        from omnibase_core.factories import get_default_orchestrator_profile

        contract = get_default_orchestrator_profile(
            profile="orchestrator_safe",
            version="1.0.0",
        )
        assert isinstance(contract, ModelContractOrchestrator)
        # Safe profile should have conservative settings
        assert contract.workflow_coordination.execution_mode == "serial"

    def test_get_default_orchestrator_profile_parallel(self) -> None:
        """Test orchestrator_parallel profile returns valid contract."""
        from omnibase_core.factories import get_default_orchestrator_profile

        contract = get_default_orchestrator_profile(
            profile="orchestrator_parallel",
            version="1.0.0",
        )
        assert isinstance(contract, ModelContractOrchestrator)
        # Parallel profile should allow parallel execution
        assert contract.workflow_coordination.execution_mode == "parallel"

    def test_get_default_orchestrator_profile_resilient(self) -> None:
        """Test orchestrator_resilient profile returns valid contract."""
        from omnibase_core.factories import get_default_orchestrator_profile

        contract = get_default_orchestrator_profile(
            profile="orchestrator_resilient",
            version="1.0.0",
        )
        assert isinstance(contract, ModelContractOrchestrator)
        # Resilient profile should have checkpointing enabled
        assert contract.workflow_coordination.checkpoint_enabled is True

    def test_orchestrator_profile_has_execution_profile(self) -> None:
        """Test orchestrator profile includes execution configuration."""
        from omnibase_core.factories import get_default_orchestrator_profile

        contract = get_default_orchestrator_profile(
            profile="orchestrator_safe",
            version="1.0.0",
        )
        # Execution profile should be embedded in the contract
        assert hasattr(contract, "execution")
        assert isinstance(contract.execution, ModelExecutionProfile)


class TestReducerProfiles:
    """Tests for reducer profile factory."""

    def test_get_default_reducer_profile_fsm_basic(self) -> None:
        """Test reducer_fsm_basic profile returns valid contract."""
        from omnibase_core.factories import get_default_reducer_profile

        contract = get_default_reducer_profile(
            profile="reducer_fsm_basic",
            version="1.0.0",
        )
        assert isinstance(contract, ModelContractReducer)
        # FSM basic should have state machine configured
        assert contract.state_machine is not None


class TestEffectProfiles:
    """Tests for effect profile factory."""

    def test_get_default_effect_profile_idempotent(self) -> None:
        """Test effect_idempotent profile returns valid contract."""
        from omnibase_core.factories import get_default_effect_profile

        contract = get_default_effect_profile(
            profile="effect_idempotent",
            version="1.0.0",
        )
        assert isinstance(contract, ModelContractEffect)
        # Idempotent profile should have idempotent operations enabled
        assert contract.idempotent_operations is True
        # Should have at least one IO operation
        assert len(contract.io_operations) >= 1


class TestComputeProfiles:
    """Tests for compute profile factory."""

    def test_get_default_compute_profile_pure(self) -> None:
        """Test compute_pure profile returns valid contract."""
        from omnibase_core.factories import get_default_compute_profile

        contract = get_default_compute_profile(
            profile="compute_pure",
            version="1.0.0",
        )
        assert isinstance(contract, ModelContractCompute)
        # Pure compute should have deterministic execution
        assert contract.deterministic_execution is True
        # Should have algorithm configured
        assert contract.algorithm is not None


class TestAvailableProfiles:
    """Tests for available_profiles functionality."""

    def test_available_orchestrator_profiles(self) -> None:
        """Test listing available orchestrator profiles."""
        from omnibase_core.factories import available_profiles

        profiles = available_profiles(EnumNodeType.ORCHESTRATOR_GENERIC)
        assert "orchestrator_safe" in profiles
        assert "orchestrator_parallel" in profiles
        assert "orchestrator_resilient" in profiles

    def test_available_reducer_profiles(self) -> None:
        """Test listing available reducer profiles."""
        from omnibase_core.factories import available_profiles

        profiles = available_profiles(EnumNodeType.REDUCER_GENERIC)
        assert "reducer_fsm_basic" in profiles

    def test_available_effect_profiles(self) -> None:
        """Test listing available effect profiles."""
        from omnibase_core.factories import available_profiles

        profiles = available_profiles(EnumNodeType.EFFECT_GENERIC)
        assert "effect_idempotent" in profiles

    def test_available_compute_profiles(self) -> None:
        """Test listing available compute profiles."""
        from omnibase_core.factories import available_profiles

        profiles = available_profiles(EnumNodeType.COMPUTE_GENERIC)
        assert "compute_pure" in profiles


class TestProtocolContractProfileFactory:
    """Tests for ProtocolContractProfileFactory interface."""

    def test_factory_implements_protocol(self) -> None:
        """Test factory class implements the protocol."""
        from omnibase_core.factories import (
            ContractProfileFactory,
            ProtocolContractProfileFactory,
        )

        factory = ContractProfileFactory()
        # Should be compatible with the protocol
        assert isinstance(factory, ProtocolContractProfileFactory)

    def test_factory_get_profile(self) -> None:
        """Test factory get_profile method."""
        from omnibase_core.factories import ContractProfileFactory

        factory = ContractProfileFactory()
        contract = factory.get_profile(
            node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
            profile="orchestrator_safe",
        )
        assert isinstance(contract, ModelContractBase)

    def test_factory_available_profiles(self) -> None:
        """Test factory available_profiles method."""
        from omnibase_core.factories import ContractProfileFactory

        factory = ContractProfileFactory()
        profiles = factory.available_profiles(EnumNodeType.ORCHESTRATOR_GENERIC)
        assert isinstance(profiles, list)
        assert len(profiles) > 0
