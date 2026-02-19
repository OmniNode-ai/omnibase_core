# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Fixtures for manifest model tests."""

from datetime import UTC, datetime

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
    ModelHookTrace,
    ModelManifestFailure,
    ModelMetricsSummary,
    ModelNodeIdentity,
    ModelOrderingSummary,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.fixture
def sample_semver() -> ModelSemVer:
    """Create a sample semantic version."""
    return ModelSemVer(major=1, minor=2, patch=3)


@pytest.fixture
def sample_node_identity(sample_semver: ModelSemVer) -> ModelNodeIdentity:
    """Create a sample node identity."""
    return ModelNodeIdentity(
        node_id="compute-text-transform-001",
        node_kind=EnumNodeKind.COMPUTE,
        node_version=sample_semver,
        namespace="onex.text",
        display_name="Text Transformer",
    )


@pytest.fixture
def sample_contract_identity(sample_semver: ModelSemVer) -> ModelContractIdentity:
    """Create a sample contract identity."""
    return ModelContractIdentity(
        contract_id="text-transform-contract",
        contract_path="contracts/text/transform.yaml",
        contract_version=sample_semver,
        profile_name="orchestrator_safe",
    )


@pytest.fixture
def sample_capability_activation_activated() -> ModelCapabilityActivation:
    """Create a sample activated capability."""
    return ModelCapabilityActivation(
        capability_name="onex:caching",
        activated=True,
        reason=EnumActivationReason.PREDICATE_TRUE,
        predicate_expression="env.cache_enabled == true",
        predicate_result=True,
    )


@pytest.fixture
def sample_capability_activation_skipped() -> ModelCapabilityActivation:
    """Create a sample skipped capability."""
    return ModelCapabilityActivation(
        capability_name="onex:logging",
        activated=False,
        reason=EnumActivationReason.PREDICATE_FALSE,
        predicate_expression="env.logging_enabled == true",
        predicate_result=False,
    )


@pytest.fixture
def sample_activation_summary(
    sample_capability_activation_activated: ModelCapabilityActivation,
    sample_capability_activation_skipped: ModelCapabilityActivation,
) -> ModelActivationSummary:
    """Create a sample activation summary."""
    return ModelActivationSummary(
        activated_capabilities=[sample_capability_activation_activated],
        skipped_capabilities=[sample_capability_activation_skipped],
        total_evaluated=2,
    )


@pytest.fixture
def sample_dependency_edge() -> ModelDependencyEdge:
    """Create a sample dependency edge."""
    return ModelDependencyEdge(
        from_handler_id="handler_transform",
        to_handler_id="handler_validate",
        dependency_type="requires",
        satisfied=True,
    )


@pytest.fixture
def sample_ordering_summary(
    sample_dependency_edge: ModelDependencyEdge,
) -> ModelOrderingSummary:
    """Create a sample ordering summary."""
    return ModelOrderingSummary(
        phases=["preflight", "before", "execute", "after", "emit", "finalize"],
        resolved_order=["handler_validate", "handler_transform", "handler_save"],
        dependency_edges=[sample_dependency_edge],
        ordering_policy="topological_sort",
    )


@pytest.fixture
def sample_hook_trace_success() -> ModelHookTrace:
    """Create a sample successful hook trace."""
    from datetime import timedelta

    duration_ms = 45.2
    started = datetime.now(UTC)
    ended = started + timedelta(milliseconds=duration_ms)
    return ModelHookTrace(
        hook_id="hook-001",
        handler_id="handler_transform",
        phase=EnumHandlerExecutionPhase.EXECUTE,
        status=EnumExecutionStatus.SUCCESS,
        started_at=started,
        ended_at=ended,
        duration_ms=duration_ms,
    )


@pytest.fixture
def sample_hook_trace_failed() -> ModelHookTrace:
    """Create a sample failed hook trace."""
    from datetime import timedelta

    duration_ms = 10.0
    started = datetime.now(UTC)
    ended = started + timedelta(milliseconds=duration_ms)
    return ModelHookTrace(
        hook_id="hook-002",
        handler_id="handler_save",
        phase=EnumHandlerExecutionPhase.EXECUTE,
        status=EnumExecutionStatus.FAILED,
        started_at=started,
        ended_at=ended,
        duration_ms=duration_ms,
        error_message="Connection timeout",
        error_code="CONN_TIMEOUT",
    )


@pytest.fixture
def sample_emissions_summary() -> ModelEmissionsSummary:
    """Create a sample emissions summary."""
    return ModelEmissionsSummary(
        events_count=5,
        event_types=["UserCreated", "UserUpdated"],
        intents_count=2,
        intent_types=["SendWelcomeEmail"],
    )


@pytest.fixture
def sample_metrics_summary() -> ModelMetricsSummary:
    """Create a sample metrics summary."""
    return ModelMetricsSummary(
        total_duration_ms=1234.5,
        phase_durations_ms={"execute": 1000.0, "finalize": 234.5},
        handler_durations_ms={"handler_transform": 800.0, "handler_save": 200.0},
    )


@pytest.fixture
def sample_manifest_failure() -> ModelManifestFailure:
    """Create a sample manifest failure."""
    return ModelManifestFailure(
        failed_at=datetime.now(UTC),
        error_code="HANDLER_TIMEOUT",
        error_message="Handler exceeded timeout of 30 seconds",
        handler_id="handler_transform",
        phase=EnumHandlerExecutionPhase.EXECUTE,
        recoverable=True,
    )
