# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ManifestGenerator.

Tests all aspects of the manifest generator including:
- Generator creation and initialization
- Capability activation recording
- Ordering recording
- Hook execution tracing
- Emission recording
- Failure recording
- Manifest building

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

import time
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_activation_reason import EnumActivationReason
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.manifest import (
    ModelContractIdentity,
    ModelNodeIdentity,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.pipeline import ManifestGenerator


@pytest.fixture
def sample_node_identity() -> ModelNodeIdentity:
    """Create a sample node identity."""
    return ModelNodeIdentity(
        node_id="test-compute-node",
        node_kind=EnumNodeKind.COMPUTE,
        node_version=ModelSemVer(major=1, minor=0, patch=0),
    )


@pytest.fixture
def sample_contract_identity() -> ModelContractIdentity:
    """Create a sample contract identity."""
    return ModelContractIdentity(
        contract_id="test-contract",
        profile_name="default",
    )


@pytest.fixture
def generator(
    sample_node_identity: ModelNodeIdentity,
    sample_contract_identity: ModelContractIdentity,
) -> ManifestGenerator:
    """Create a sample generator."""
    return ManifestGenerator(
        node_identity=sample_node_identity,
        contract_identity=sample_contract_identity,
    )


@pytest.mark.unit
class TestManifestGeneratorCreation:
    """Test ManifestGenerator creation."""

    def test_create_minimal(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test creating generator with required arguments only."""
        generator = ManifestGenerator(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )
        assert generator.manifest_id is not None
        assert generator.started_at is not None

    def test_create_with_correlation_id(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test creating generator with correlation ID."""
        correlation_id = uuid4()
        generator = ManifestGenerator(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            correlation_id=correlation_id,
        )
        manifest = generator.build()
        assert manifest.correlation_id == correlation_id

    def test_create_with_parent_manifest_id(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test creating generator for nested execution."""
        parent_id = uuid4()
        generator = ManifestGenerator(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            parent_manifest_id=parent_id,
        )
        manifest = generator.build()
        assert manifest.parent_manifest_id == parent_id
        assert manifest.is_nested()


@pytest.mark.unit
class TestManifestGeneratorCapabilityActivation:
    """Test capability activation recording."""

    def test_record_activated_capability(self, generator: ManifestGenerator) -> None:
        """Test recording an activated capability."""
        generator.record_capability_activation(
            capability_name="onex:caching",
            activated=True,
            reason=EnumActivationReason.PREDICATE_TRUE,
            predicate_expression="env.cache_enabled == true",
            predicate_result=True,
        )
        manifest = generator.build()

        assert manifest.activation_summary.get_activated_count() == 1
        assert manifest.activation_summary.get_skipped_count() == 0
        assert manifest.activation_summary.was_activated("onex:caching")

    def test_record_skipped_capability(self, generator: ManifestGenerator) -> None:
        """Test recording a skipped capability."""
        generator.record_capability_activation(
            capability_name="onex:logging",
            activated=False,
            reason=EnumActivationReason.PREDICATE_FALSE,
        )
        manifest = generator.build()

        assert manifest.activation_summary.get_activated_count() == 0
        assert manifest.activation_summary.get_skipped_count() == 1
        assert not manifest.activation_summary.was_activated("onex:logging")

    def test_record_multiple_capabilities(self, generator: ManifestGenerator) -> None:
        """Test recording multiple capabilities."""
        generator.record_capability_activation(
            capability_name="onex:caching",
            activated=True,
            reason=EnumActivationReason.ALWAYS_ACTIVE,
        )
        generator.record_capability_activation(
            capability_name="onex:logging",
            activated=False,
            reason=EnumActivationReason.EXPLICITLY_DISABLED,
        )
        generator.record_capability_activation(
            capability_name="onex:metrics",
            activated=True,
            reason=EnumActivationReason.PREDICATE_TRUE,
        )

        manifest = generator.build()
        assert manifest.activation_summary.total_evaluated == 3
        assert manifest.activation_summary.get_activated_count() == 2
        assert manifest.activation_summary.get_skipped_count() == 1


@pytest.mark.unit
class TestManifestGeneratorOrdering:
    """Test execution ordering recording."""

    def test_record_ordering(self, generator: ManifestGenerator) -> None:
        """Test recording execution ordering."""
        generator.record_ordering(
            phases=["preflight", "execute", "finalize"],
            resolved_order=["handler_a", "handler_b", "handler_c"],
            ordering_policy="topological_sort",
        )
        manifest = generator.build()

        assert manifest.ordering_summary.get_phase_count() == 3
        assert manifest.ordering_summary.get_handler_count() == 3
        assert manifest.ordering_summary.ordering_policy == "topological_sort"

    def test_add_dependency_edge(self, generator: ManifestGenerator) -> None:
        """Test adding dependency edges."""
        generator.add_dependency_edge(
            from_handler_id="handler_b",
            to_handler_id="handler_a",
            dependency_type="requires",
            satisfied=True,
        )
        manifest = generator.build()

        assert manifest.ordering_summary.get_dependency_count() == 1
        deps = manifest.ordering_summary.get_dependencies_for("handler_b")
        assert "handler_a" in deps


@pytest.mark.unit
class TestManifestGeneratorHookExecution:
    """Test hook execution recording."""

    def test_start_and_complete_hook(self, generator: ManifestGenerator) -> None:
        """Test starting and completing a hook."""
        generator.start_hook(
            hook_id="hook-1",
            handler_id="handler_test",
            phase=EnumHandlerExecutionPhase.EXECUTE,
        )
        generator.complete_hook(
            hook_id="hook-1",
            status=EnumExecutionStatus.SUCCESS,
        )
        manifest = generator.build()

        assert manifest.get_hook_count() == 1
        assert manifest.hook_traces[0].is_success()
        assert manifest.hook_traces[0].duration_ms >= 0

    def test_hook_with_error(self, generator: ManifestGenerator) -> None:
        """Test recording hook failure."""
        generator.start_hook(
            hook_id="hook-1",
            handler_id="handler_test",
            phase=EnumHandlerExecutionPhase.EXECUTE,
        )
        generator.complete_hook(
            hook_id="hook-1",
            status=EnumExecutionStatus.FAILED,
            error_message="Connection timeout",
            error_code="CONN_TIMEOUT",
        )
        manifest = generator.build()

        assert manifest.get_hook_count() == 1
        assert manifest.hook_traces[0].is_failure()
        assert manifest.hook_traces[0].error_message == "Connection timeout"

    def test_hook_timing(self, generator: ManifestGenerator) -> None:
        """Test hook timing is captured."""
        generator.start_hook(
            hook_id="hook-1",
            handler_id="handler_test",
            phase=EnumHandlerExecutionPhase.EXECUTE,
        )
        time.sleep(0.01)  # 10ms
        generator.complete_hook(
            hook_id="hook-1",
            status=EnumExecutionStatus.SUCCESS,
        )
        manifest = generator.build()

        # Duration should be at least 10ms
        assert manifest.hook_traces[0].duration_ms >= 10

    def test_complete_unknown_hook(self, generator: ManifestGenerator) -> None:
        """Test completing a hook that wasn't started emits a warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            generator.complete_hook(
                hook_id="unknown-hook",
                status=EnumExecutionStatus.SUCCESS,
            )
            manifest = generator.build()

            # Should emit a warning about the unexpected hook completion
            assert len(w) == 1
            assert "unknown-hook" in str(w[0].message)
            assert "never started" in str(w[0].message)

        # Should still create a trace
        assert manifest.get_hook_count() == 1
        assert manifest.hook_traces[0].handler_id == "unknown"

    def test_pending_hooks_cancelled_on_build(
        self, generator: ManifestGenerator
    ) -> None:
        """Test that pending hooks are cancelled when building manifest."""
        generator.start_hook(
            hook_id="hook-1",
            handler_id="handler_test",
            phase=EnumHandlerExecutionPhase.EXECUTE,
        )
        # Don't complete the hook
        manifest = generator.build()

        assert manifest.get_hook_count() == 1
        assert manifest.hook_traces[0].status == EnumExecutionStatus.CANCELLED

    def test_handler_durations_aggregate_multiple_phases(
        self, generator: ManifestGenerator
    ) -> None:
        """Test that handler durations are summed when a handler has multiple hook traces.

        When a handler executes across multiple phases (e.g., PREPARE, EXECUTE, CLEANUP),
        each phase creates a separate hook trace. The metrics summary should aggregate
        (sum) all durations for the same handler_id rather than keeping only the last one.
        """
        # Record three hooks for the same handler (different phases)
        generator.start_hook(
            hook_id="hook-prepare",
            handler_id="handler_test",
            phase=EnumHandlerExecutionPhase.PREFLIGHT,
        )
        time.sleep(0.01)  # 10ms
        generator.complete_hook("hook-prepare", EnumExecutionStatus.SUCCESS)

        generator.start_hook(
            hook_id="hook-execute",
            handler_id="handler_test",
            phase=EnumHandlerExecutionPhase.EXECUTE,
        )
        time.sleep(0.02)  # 20ms
        generator.complete_hook("hook-execute", EnumExecutionStatus.SUCCESS)

        generator.start_hook(
            hook_id="hook-cleanup",
            handler_id="handler_test",
            phase=EnumHandlerExecutionPhase.FINALIZE,
        )
        time.sleep(0.01)  # 10ms
        generator.complete_hook("hook-cleanup", EnumExecutionStatus.SUCCESS)

        manifest = generator.build()

        # Should have 3 hook traces
        assert manifest.get_hook_count() == 3

        # Handler duration should be the SUM of all three phases (at least 40ms)
        handler_duration = manifest.metrics_summary.handler_durations_ms.get(
            "handler_test"
        )
        assert handler_duration is not None
        assert handler_duration >= 40  # Sum of 10 + 20 + 10 = 40ms minimum

    def test_handler_durations_separate_handlers(
        self, generator: ManifestGenerator
    ) -> None:
        """Test that different handlers maintain separate duration totals."""
        # Handler A
        generator.start_hook(
            hook_id="hook-a1",
            handler_id="handler_a",
            phase=EnumHandlerExecutionPhase.EXECUTE,
        )
        time.sleep(0.01)  # 10ms
        generator.complete_hook("hook-a1", EnumExecutionStatus.SUCCESS)

        # Handler B
        generator.start_hook(
            hook_id="hook-b1",
            handler_id="handler_b",
            phase=EnumHandlerExecutionPhase.EXECUTE,
        )
        time.sleep(0.02)  # 20ms
        generator.complete_hook("hook-b1", EnumExecutionStatus.SUCCESS)

        # Handler A second phase
        generator.start_hook(
            hook_id="hook-a2",
            handler_id="handler_a",
            phase=EnumHandlerExecutionPhase.FINALIZE,
        )
        time.sleep(0.01)  # 10ms
        generator.complete_hook("hook-a2", EnumExecutionStatus.SUCCESS)

        manifest = generator.build()

        # Should have 3 hook traces
        assert manifest.get_hook_count() == 3

        # Handler A should have sum of its two phases (at least 20ms)
        handler_a_duration = manifest.metrics_summary.handler_durations_ms.get(
            "handler_a"
        )
        assert handler_a_duration is not None
        assert handler_a_duration >= 20

        # Handler B should have only its single phase (at least 20ms)
        handler_b_duration = manifest.metrics_summary.handler_durations_ms.get(
            "handler_b"
        )
        assert handler_b_duration is not None
        assert handler_b_duration >= 20


@pytest.mark.unit
class TestManifestGeneratorEmissions:
    """Test emission recording."""

    def test_record_event(self, generator: ManifestGenerator) -> None:
        """Test recording event emission."""
        generator.record_event("UserCreated")
        generator.record_event("UserUpdated")
        manifest = generator.build()

        assert manifest.emissions_summary.events_count == 2
        assert "UserCreated" in manifest.emissions_summary.event_types

    def test_record_intent(self, generator: ManifestGenerator) -> None:
        """Test recording intent emission."""
        generator.record_intent("SendEmail")
        manifest = generator.build()

        assert manifest.emissions_summary.intents_count == 1
        assert "SendEmail" in manifest.emissions_summary.intent_types

    def test_record_projection(self, generator: ManifestGenerator) -> None:
        """Test recording projection update."""
        generator.record_projection("UserStats")
        manifest = generator.build()

        assert manifest.emissions_summary.projections_count == 1

    def test_record_action(self, generator: ManifestGenerator) -> None:
        """Test recording action emission."""
        generator.record_action("ProcessPayment")
        manifest = generator.build()

        assert manifest.emissions_summary.actions_count == 1

    def test_duplicate_types_deduplicated(self, generator: ManifestGenerator) -> None:
        """Test that duplicate emission types are deduplicated."""
        generator.record_event("UserCreated")
        generator.record_event("UserCreated")
        generator.record_event("UserCreated")
        manifest = generator.build()

        assert manifest.emissions_summary.events_count == 3
        # Types should be deduplicated
        assert len(manifest.emissions_summary.event_types) == 1


@pytest.mark.unit
class TestManifestGeneratorFailures:
    """Test failure recording."""

    def test_record_failure(self, generator: ManifestGenerator) -> None:
        """Test recording a failure."""
        generator.record_failure(
            error_code="HANDLER_ERROR",
            error_message="Handler failed to process",
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_id="handler_test",
        )
        manifest = generator.build()

        assert manifest.has_failures()
        assert manifest.get_failure_count() == 1
        assert not manifest.is_successful()

    def test_record_recoverable_failure(self, generator: ManifestGenerator) -> None:
        """Test recording a recoverable failure."""
        generator.record_failure(
            error_code="RETRY_NEEDED",
            error_message="Temporary failure",
            recoverable=True,
        )
        manifest = generator.build()

        assert manifest.failures[0].is_recoverable()


@pytest.mark.unit
class TestManifestGeneratorBuild:
    """Test manifest building."""

    def test_build_empty_manifest(self, generator: ManifestGenerator) -> None:
        """Test building manifest with no recorded data."""
        manifest = generator.build()

        assert manifest.is_successful()
        assert manifest.get_hook_count() == 0
        assert manifest.activation_summary.is_empty()
        assert manifest.emissions_summary.is_empty()

    def test_build_multiple_times(self, generator: ManifestGenerator) -> None:
        """Test that build can be called multiple times."""
        generator.record_event("Event1")
        manifest1 = generator.build()

        generator.record_event("Event2")
        manifest2 = generator.build()

        # Both manifests should have same ID
        assert manifest1.manifest_id == manifest2.manifest_id
        # But second should have more events
        assert manifest2.emissions_summary.events_count == 2

    def test_build_includes_metrics(self, generator: ManifestGenerator) -> None:
        """Test that build includes metrics summary."""
        generator.start_hook("hook-1", "handler", EnumHandlerExecutionPhase.EXECUTE)
        generator.complete_hook("hook-1", EnumExecutionStatus.SUCCESS)
        manifest = generator.build()

        assert manifest.has_metrics()
        assert manifest.metrics_summary is not None
        assert manifest.metrics_summary.total_duration_ms > 0

    def test_build_preserves_node_identity(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test that build preserves node identity."""
        generator = ManifestGenerator(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )
        manifest = generator.build()

        assert manifest.node_identity.node_id == sample_node_identity.node_id
        assert manifest.node_identity.node_kind == sample_node_identity.node_kind


@pytest.mark.unit
class TestManifestGeneratorSizeEstimation:
    """Test ManifestGenerator size estimation."""

    def test_estimate_empty_manifest(
        self,
        generator: ManifestGenerator,
    ) -> None:
        """Test size estimation for empty manifest."""
        size = generator.estimate_json_size_bytes()
        # Empty manifest has base overhead for structure, identities, etc.
        assert size > 0
        assert size < 2000  # Should be small for empty manifest

    def test_estimate_with_hook_traces(
        self,
        generator: ManifestGenerator,
    ) -> None:
        """Test size estimation increases with hook traces."""
        base_size = generator.estimate_json_size_bytes()

        # Add some hook traces
        for i in range(10):
            generator.start_hook(
                f"hook-{i}", f"handler-{i}", EnumHandlerExecutionPhase.EXECUTE
            )
            generator.complete_hook(f"hook-{i}", EnumExecutionStatus.SUCCESS)

        new_size = generator.estimate_json_size_bytes()
        # Size should have increased significantly (10 hooks * ~500 bytes each)
        assert new_size > base_size
        assert new_size > base_size + 4000  # At least 400 bytes per hook

    def test_estimate_with_capabilities(
        self,
        generator: ManifestGenerator,
    ) -> None:
        """Test size estimation increases with capabilities."""
        base_size = generator.estimate_json_size_bytes()

        # Add some capability activations
        for i in range(5):
            generator.record_capability_activation(
                capability_name=f"cap-{i}",
                activated=True,
                reason=EnumActivationReason.PREDICATE_TRUE,
            )
            generator.record_capability_activation(
                capability_name=f"skip-{i}",
                activated=False,
                reason=EnumActivationReason.PREDICATE_FALSE,
            )

        new_size = generator.estimate_json_size_bytes()
        assert new_size > base_size

    def test_estimate_with_emissions(
        self,
        generator: ManifestGenerator,
    ) -> None:
        """Test size estimation increases with emissions."""
        base_size = generator.estimate_json_size_bytes()

        # Add emissions
        for i in range(20):
            generator.record_event(f"EventType{i}")
            generator.record_intent(f"IntentType{i}")

        new_size = generator.estimate_json_size_bytes()
        assert new_size > base_size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
