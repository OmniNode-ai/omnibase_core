# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelExecutionManifest and related manifest models.

Tests all aspects of the execution manifest including:
- Model creation and validation
- Field types and constraints
- Utility methods
- Serialization/deserialization
- Pydantic compatibility
- Edge cases

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_activation_reason import EnumActivationReason
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.manifest import (
    ModelActivationSummary,
    ModelCapabilityActivation,
    ModelContractIdentity,
    ModelDependencyEdge,
    ModelEmissionsSummary,
    ModelExecutionManifest,
    ModelHookTrace,
    ModelManifestFailure,
    ModelMetricsSummary,
    ModelNodeIdentity,
    ModelOrderingSummary,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelNodeIdentity:
    """Test cases for ModelNodeIdentity."""

    def test_create_minimal(self) -> None:
        """Test creating node identity with required fields only."""
        identity = ModelNodeIdentity(
            node_id="test-node",
            node_kind=EnumNodeKind.COMPUTE,
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert identity.node_id == "test-node"
        assert identity.node_kind == EnumNodeKind.COMPUTE
        assert identity.namespace is None

    def test_create_full(self, sample_node_identity: ModelNodeIdentity) -> None:
        """Test creating node identity with all fields."""
        assert sample_node_identity.node_id == "compute-text-transform-001"
        assert sample_node_identity.namespace == "onex.text"
        assert sample_node_identity.display_name == "Text Transformer"

    def test_get_qualified_id_with_namespace(
        self, sample_node_identity: ModelNodeIdentity
    ) -> None:
        """Test get_qualified_id includes namespace."""
        assert (
            sample_node_identity.get_qualified_id()
            == "onex.text/compute-text-transform-001"
        )

    def test_get_qualified_id_without_namespace(self) -> None:
        """Test get_qualified_id returns node_id when no namespace."""
        identity = ModelNodeIdentity(
            node_id="test-node",
            node_kind=EnumNodeKind.COMPUTE,
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert identity.get_qualified_id() == "test-node"

    def test_get_display_name_fallback(self) -> None:
        """Test get_display_name falls back to node_id."""
        identity = ModelNodeIdentity(
            node_id="test-node",
            node_kind=EnumNodeKind.COMPUTE,
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert identity.get_display_name() == "test-node"

    def test_get_version_string(self, sample_node_identity: ModelNodeIdentity) -> None:
        """Test version string formatting."""
        assert sample_node_identity.get_version_string() == "1.2.3"

    def test_frozen(self, sample_node_identity: ModelNodeIdentity) -> None:
        """Test that model is frozen."""
        with pytest.raises(Exception):  # ValidationError or AttributeError
            sample_node_identity.node_id = "new-id"  # type: ignore[misc]


@pytest.mark.unit
class TestModelContractIdentity:
    """Test cases for ModelContractIdentity."""

    def test_create_minimal(self) -> None:
        """Test creating contract identity with required fields only."""
        identity = ModelContractIdentity(contract_id="test-contract")
        assert identity.contract_id == "test-contract"
        assert identity.contract_path is None
        assert identity.profile_name is None

    def test_create_full(self, sample_contract_identity: ModelContractIdentity) -> None:
        """Test creating contract identity with all fields."""
        assert sample_contract_identity.contract_id == "text-transform-contract"
        assert sample_contract_identity.contract_path == "contracts/text/transform.yaml"
        assert sample_contract_identity.profile_name == "orchestrator_safe"

    def test_has_version(self, sample_contract_identity: ModelContractIdentity) -> None:
        """Test has_version method."""
        assert sample_contract_identity.has_version() is True
        minimal = ModelContractIdentity(contract_id="test")
        assert minimal.has_version() is False

    def test_get_version_string(
        self, sample_contract_identity: ModelContractIdentity
    ) -> None:
        """Test version string formatting."""
        assert sample_contract_identity.get_version_string() == "1.2.3"


@pytest.mark.unit
class TestModelCapabilityActivation:
    """Test cases for ModelCapabilityActivation."""

    def test_activated_capability(
        self, sample_capability_activation_activated: ModelCapabilityActivation
    ) -> None:
        """Test activated capability."""
        cap = sample_capability_activation_activated
        assert cap.is_activated() is True
        assert cap.is_skipped() is False
        assert cap.reason == EnumActivationReason.PREDICATE_TRUE
        assert cap.predicate_result is True

    def test_skipped_capability(
        self, sample_capability_activation_skipped: ModelCapabilityActivation
    ) -> None:
        """Test skipped capability."""
        cap = sample_capability_activation_skipped
        assert cap.is_activated() is False
        assert cap.is_skipped() is True
        assert cap.reason == EnumActivationReason.PREDICATE_FALSE

    def test_has_predicate(
        self, sample_capability_activation_activated: ModelCapabilityActivation
    ) -> None:
        """Test has_predicate method."""
        assert sample_capability_activation_activated.has_predicate() is True

    def test_has_conflicts(self) -> None:
        """Test has_conflicts method."""
        cap = ModelCapabilityActivation(
            capability_name="test",
            activated=False,
            reason=EnumActivationReason.CONFLICT_DETECTED,
            conflict_with=["other_capability"],
        )
        assert cap.has_conflicts() is True


@pytest.mark.unit
class TestModelActivationSummary:
    """Test cases for ModelActivationSummary."""

    def test_counts(self, sample_activation_summary: ModelActivationSummary) -> None:
        """Test count methods."""
        assert sample_activation_summary.get_activated_count() == 1
        assert sample_activation_summary.get_skipped_count() == 1
        assert sample_activation_summary.total_evaluated == 2

    def test_activation_rate(
        self, sample_activation_summary: ModelActivationSummary
    ) -> None:
        """Test activation rate calculation."""
        assert sample_activation_summary.get_activation_rate() == 50.0

    def test_empty_summary(self) -> None:
        """Test empty summary."""
        summary = ModelActivationSummary()
        assert summary.is_empty() is True
        assert summary.get_activation_rate() == 0.0

    def test_get_capability_names(
        self, sample_activation_summary: ModelActivationSummary
    ) -> None:
        """Test getting capability names."""
        names = sample_activation_summary.get_capability_names()
        assert "onex:caching" in names
        assert "onex:logging" in names

    def test_was_activated(
        self, sample_activation_summary: ModelActivationSummary
    ) -> None:
        """Test was_activated method."""
        assert sample_activation_summary.was_activated("onex:caching") is True
        assert sample_activation_summary.was_activated("onex:logging") is False


@pytest.mark.unit
class TestModelDependencyEdge:
    """Test cases for ModelDependencyEdge."""

    def test_create(self, sample_dependency_edge: ModelDependencyEdge) -> None:
        """Test creating dependency edge."""
        edge = sample_dependency_edge
        assert edge.from_handler_id == "handler_transform"
        assert edge.to_handler_id == "handler_validate"
        assert edge.dependency_type == "requires"
        assert edge.satisfied is True

    def test_involves_handler(
        self, sample_dependency_edge: ModelDependencyEdge
    ) -> None:
        """Test involves_handler method."""
        edge = sample_dependency_edge
        assert edge.involves_handler("handler_transform") is True
        assert edge.involves_handler("handler_validate") is True
        assert edge.involves_handler("handler_unknown") is False


@pytest.mark.unit
class TestModelOrderingSummary:
    """Test cases for ModelOrderingSummary."""

    def test_counts(self, sample_ordering_summary: ModelOrderingSummary) -> None:
        """Test count methods."""
        assert sample_ordering_summary.get_phase_count() == 6
        assert sample_ordering_summary.get_handler_count() == 3
        assert sample_ordering_summary.get_dependency_count() == 1

    def test_has_handler(self, sample_ordering_summary: ModelOrderingSummary) -> None:
        """Test has_handler method."""
        assert sample_ordering_summary.has_handler("handler_validate") is True
        assert sample_ordering_summary.has_handler("unknown") is False

    def test_get_handler_index(
        self, sample_ordering_summary: ModelOrderingSummary
    ) -> None:
        """Test get_handler_index method."""
        assert sample_ordering_summary.get_handler_index("handler_validate") == 0
        assert sample_ordering_summary.get_handler_index("handler_transform") == 1
        assert sample_ordering_summary.get_handler_index("unknown") is None

    def test_get_dependencies_for(
        self, sample_ordering_summary: ModelOrderingSummary
    ) -> None:
        """Test get_dependencies_for method."""
        deps = sample_ordering_summary.get_dependencies_for("handler_transform")
        assert "handler_validate" in deps


@pytest.mark.unit
class TestModelHookTrace:
    """Test cases for ModelHookTrace."""

    def test_successful_trace(self, sample_hook_trace_success: ModelHookTrace) -> None:
        """Test successful hook trace."""
        trace = sample_hook_trace_success
        assert trace.is_success() is True
        assert trace.is_failure() is False
        assert trace.is_skipped() is False
        assert trace.has_error() is False

    def test_failed_trace(self, sample_hook_trace_failed: ModelHookTrace) -> None:
        """Test failed hook trace."""
        trace = sample_hook_trace_failed
        assert trace.is_success() is False
        assert trace.is_failure() is True
        assert trace.has_error() is True
        assert trace.error_message == "Connection timeout"

    def test_skipped_trace(self) -> None:
        """Test skipped hook trace."""
        trace = ModelHookTrace(
            hook_id="hook-003",
            handler_id="handler_optional",
            phase=EnumHandlerExecutionPhase.EXECUTE,
            status=EnumExecutionStatus.SKIPPED,
            started_at=datetime.now(UTC),
            skip_reason="Optional handler not enabled",
        )
        assert trace.is_skipped() is True


@pytest.mark.unit
class TestModelEmissionsSummary:
    """Test cases for ModelEmissionsSummary."""

    def test_total_emissions(
        self, sample_emissions_summary: ModelEmissionsSummary
    ) -> None:
        """Test total emissions calculation."""
        assert sample_emissions_summary.total_emissions() == 7  # 5 events + 2 intents

    def test_has_methods(self, sample_emissions_summary: ModelEmissionsSummary) -> None:
        """Test has_* methods."""
        assert sample_emissions_summary.has_events() is True
        assert sample_emissions_summary.has_intents() is True
        assert sample_emissions_summary.has_projections() is False
        assert sample_emissions_summary.has_actions() is False

    def test_empty_summary(self) -> None:
        """Test empty emissions summary."""
        summary = ModelEmissionsSummary()
        assert summary.is_empty() is True
        assert summary.total_emissions() == 0


@pytest.mark.unit
class TestModelMetricsSummary:
    """Test cases for ModelMetricsSummary."""

    def test_duration_conversion(
        self, sample_metrics_summary: ModelMetricsSummary
    ) -> None:
        """Test duration conversion to seconds."""
        assert sample_metrics_summary.get_total_duration_seconds() == pytest.approx(
            1.2345
        )

    def test_get_slowest_phase(
        self, sample_metrics_summary: ModelMetricsSummary
    ) -> None:
        """Test get_slowest_phase method."""
        slowest = sample_metrics_summary.get_slowest_phase()
        assert slowest is not None
        assert slowest[0] == "execute"
        assert slowest[1] == 1000.0

    def test_get_slowest_handler(
        self, sample_metrics_summary: ModelMetricsSummary
    ) -> None:
        """Test get_slowest_handler method."""
        slowest = sample_metrics_summary.get_slowest_handler()
        assert slowest is not None
        assert slowest[0] == "handler_transform"


@pytest.mark.unit
class TestModelManifestFailure:
    """Test cases for ModelManifestFailure."""

    def test_create(self, sample_manifest_failure: ModelManifestFailure) -> None:
        """Test creating manifest failure."""
        failure = sample_manifest_failure
        assert failure.error_code == "HANDLER_TIMEOUT"
        assert failure.is_recoverable() is True
        assert failure.has_handler() is True
        assert failure.has_phase() is True

    def test_get_summary(self, sample_manifest_failure: ModelManifestFailure) -> None:
        """Test get_summary method."""
        summary = sample_manifest_failure.get_summary()
        assert "[HANDLER_TIMEOUT]" in summary
        assert "30 seconds" in summary


@pytest.mark.unit
class TestModelExecutionManifest:
    """Test cases for ModelExecutionManifest."""

    def test_create_minimal(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test creating manifest with required fields only."""
        manifest = ModelExecutionManifest(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )
        assert manifest.manifest_id is not None
        assert manifest.created_at is not None
        assert manifest.is_successful() is True
        assert manifest.get_hook_count() == 0

    def test_create_with_hooks(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
        sample_hook_trace_success: ModelHookTrace,
    ) -> None:
        """Test creating manifest with hook traces."""
        manifest = ModelExecutionManifest(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            hook_traces=[sample_hook_trace_success],
        )
        assert manifest.get_hook_count() == 1
        assert manifest.is_successful() is True

    def test_failed_manifest(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
        sample_manifest_failure: ModelManifestFailure,
    ) -> None:
        """Test manifest with failures."""
        manifest = ModelExecutionManifest(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            failures=[sample_manifest_failure],
        )
        assert manifest.is_successful() is False
        assert manifest.has_failures() is True
        assert manifest.get_failure_count() == 1

    def test_manifest_with_failed_hook(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
        sample_hook_trace_failed: ModelHookTrace,
    ) -> None:
        """Test manifest with failed hook trace."""
        manifest = ModelExecutionManifest(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            hook_traces=[sample_hook_trace_failed],
        )
        assert manifest.is_successful() is False
        assert len(manifest.get_failed_hooks()) == 1

    def test_get_phases_executed(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
        sample_hook_trace_success: ModelHookTrace,
    ) -> None:
        """Test get_phases_executed method."""
        manifest = ModelExecutionManifest(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            hook_traces=[sample_hook_trace_success],
        )
        phases = manifest.get_phases_executed()
        assert "execute" in phases

    def test_json_serialization(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
        sample_hook_trace_success: ModelHookTrace,
    ) -> None:
        """Test JSON serialization roundtrip."""
        manifest = ModelExecutionManifest(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            hook_traces=[sample_hook_trace_success],
        )
        json_str = manifest.model_dump_json()
        data = json.loads(json_str)

        # Verify key fields are serialized
        assert "manifest_id" in data
        assert "node_identity" in data
        assert "contract_identity" in data
        assert "hook_traces" in data

        # Verify roundtrip
        restored = ModelExecutionManifest.model_validate_json(json_str)
        assert restored.manifest_id == manifest.manifest_id

    def test_correlation_id(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test correlation ID."""
        correlation = uuid4()
        manifest = ModelExecutionManifest(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            correlation_id=correlation,
        )
        assert manifest.correlation_id == correlation

    def test_nested_manifest(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test nested manifest with parent ID."""
        parent_id = uuid4()
        manifest = ModelExecutionManifest(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            parent_manifest_id=parent_id,
        )
        assert manifest.is_nested() is True
        assert manifest.parent_manifest_id == parent_id

    def test_manifest_version_string(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test manifest version string."""
        manifest = ModelExecutionManifest(
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )
        assert manifest.get_manifest_version_string() == "1.0.0"


@pytest.mark.unit
class TestModelFrozenBehavior:
    """Test that all models are frozen (immutable)."""

    def test_node_identity_frozen(
        self, sample_node_identity: ModelNodeIdentity
    ) -> None:
        """Test ModelNodeIdentity is frozen."""
        with pytest.raises(Exception):
            sample_node_identity.node_id = "new"  # type: ignore[misc]

    def test_contract_identity_frozen(
        self, sample_contract_identity: ModelContractIdentity
    ) -> None:
        """Test ModelContractIdentity is frozen."""
        with pytest.raises(Exception):
            sample_contract_identity.contract_id = "new"  # type: ignore[misc]

    def test_capability_activation_frozen(
        self, sample_capability_activation_activated: ModelCapabilityActivation
    ) -> None:
        """Test ModelCapabilityActivation is frozen."""
        with pytest.raises(Exception):
            sample_capability_activation_activated.activated = False  # type: ignore[misc]

    def test_hook_trace_frozen(self, sample_hook_trace_success: ModelHookTrace) -> None:
        """Test ModelHookTrace is frozen."""
        with pytest.raises(Exception):
            sample_hook_trace_success.status = EnumExecutionStatus.FAILED  # type: ignore[misc]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
