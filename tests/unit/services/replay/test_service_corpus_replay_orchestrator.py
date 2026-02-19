# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ServiceCorpusReplayOrchestrator (OMN-1204)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.manifest.model_contract_identity import ModelContractIdentity
from omnibase_core.models.manifest.model_execution_manifest import (
    ModelExecutionManifest,
)
from omnibase_core.models.manifest.model_node_identity import ModelNodeIdentity
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.replay import (
    ModelCorpusReplayConfig,
    ModelCorpusReplayProgress,
    ModelExecutionCorpus,
    ModelSubsetFilter,
)
from omnibase_core.pipeline.replay.runner_replay_executor import ExecutorReplay
from omnibase_core.services.replay.service_corpus_replay_orchestrator import (
    ServiceCorpusReplayOrchestrator,
)


def _create_test_manifest(handler_id: str = "test-handler") -> ModelExecutionManifest:
    """Create a test execution manifest."""
    return ModelExecutionManifest(
        manifest_id=uuid4(),
        node_identity=ModelNodeIdentity(
            node_id="test-node",
            node_kind=EnumNodeKind.COMPUTE,
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_descriptor_id=handler_id,
        ),
        contract_identity=ModelContractIdentity(
            contract_id="test-contract",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        created_at=datetime.now(UTC),
    )


def _create_test_corpus(
    n_executions: int = 5,
    name: str = "test-corpus",
) -> ModelExecutionCorpus:
    """Create a test corpus with n executions."""
    manifests = [_create_test_manifest() for _ in range(n_executions)]
    return ModelExecutionCorpus(
        name=name,
        version="1.0.0",
        source="test",
    ).with_executions(manifests)


@pytest.mark.unit
class TestServiceCorpusReplayOrchestrator:
    """Tests for ServiceCorpusReplayOrchestrator."""

    @pytest.fixture
    def executor(self) -> ExecutorReplay:
        """Create ExecutorReplay for testing."""
        return ExecutorReplay()

    @pytest.fixture
    def orchestrator(self, executor: ExecutorReplay) -> ServiceCorpusReplayOrchestrator:
        """Create orchestrator for testing."""
        return ServiceCorpusReplayOrchestrator(executor)

    @pytest.mark.asyncio
    async def test_replay_empty_corpus(
        self, orchestrator: ServiceCorpusReplayOrchestrator
    ) -> None:
        """Replaying empty corpus should return empty result."""
        corpus = ModelExecutionCorpus(
            name="empty",
            version="1.0.0",
            source="test",
        )
        config = ModelCorpusReplayConfig()

        # Empty corpus should raise validation error
        with pytest.raises(ModelOnexError):
            await orchestrator.replay(corpus, config)

    @pytest.mark.asyncio
    async def test_replay_sequential(
        self, orchestrator: ServiceCorpusReplayOrchestrator
    ) -> None:
        """Sequential replay should process executions one by one."""
        corpus = _create_test_corpus(n_executions=3)
        config = ModelCorpusReplayConfig(concurrency=1)

        result = await orchestrator.replay(corpus, config)

        assert result.total_executions == 3
        assert result.corpus_name == "test-corpus"
        assert result.duration_ms > 0
        # All should succeed since we're using a mock replay
        assert result.successful == 3
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_replay_parallel(
        self, orchestrator: ServiceCorpusReplayOrchestrator
    ) -> None:
        """Parallel replay should process with concurrency."""
        corpus = _create_test_corpus(n_executions=5)
        config = ModelCorpusReplayConfig(concurrency=3)

        result = await orchestrator.replay(corpus, config)

        assert result.total_executions == 5
        assert result.successful == 5

    @pytest.mark.asyncio
    async def test_subset_filter_by_index(
        self, orchestrator: ServiceCorpusReplayOrchestrator
    ) -> None:
        """Subset filter should limit executions by index range."""
        corpus = _create_test_corpus(n_executions=10)
        config = ModelCorpusReplayConfig(
            subset_filter=ModelSubsetFilter(index_start=2, index_end=5)
        )

        result = await orchestrator.replay(corpus, config)

        # Should only replay indices 2, 3, 4 (3 executions)
        assert result.total_executions == 3
        # Filtered items don't count as skipped - they're just not in total_executions
        assert result.skipped == 0
        assert result.successful == 3

    @pytest.mark.asyncio
    async def test_subset_filter_by_handler(
        self, orchestrator: ServiceCorpusReplayOrchestrator
    ) -> None:
        """Subset filter should limit executions by handler name."""
        # Create corpus with mixed handlers
        corpus = ModelExecutionCorpus(
            name="mixed",
            version="1.0.0",
            source="test",
        ).with_executions(
            [
                _create_test_manifest(handler_id="handler-a"),
                _create_test_manifest(handler_id="handler-b"),
                _create_test_manifest(handler_id="handler-a"),
                _create_test_manifest(handler_id="handler-c"),
            ]
        )
        config = ModelCorpusReplayConfig(
            subset_filter=ModelSubsetFilter(handler_names=("handler-a",))
        )

        result = await orchestrator.replay(corpus, config)

        # Should only replay handler-a (2 executions)
        assert result.total_executions == 2
        # Filtered items don't count as skipped
        assert result.skipped == 0
        assert result.successful == 2

    @pytest.mark.asyncio
    async def test_progress_callback(
        self, orchestrator: ServiceCorpusReplayOrchestrator
    ) -> None:
        """Progress callback should be called during replay."""
        corpus = _create_test_corpus(n_executions=3)
        progress_updates: list[ModelCorpusReplayProgress] = []

        def callback(progress: ModelCorpusReplayProgress) -> None:
            progress_updates.append(progress)

        config = ModelCorpusReplayConfig(
            concurrency=1,
            progress_callback=callback,
        )

        await orchestrator.replay(corpus, config)

        # Should have received progress updates
        assert len(progress_updates) >= 3
        # Last update should show all completed
        last_progress = progress_updates[-1]
        assert last_progress.total == 3

    @pytest.mark.asyncio
    async def test_last_progress_property(
        self, orchestrator: ServiceCorpusReplayOrchestrator
    ) -> None:
        """last_progress property should return most recent progress."""
        corpus = _create_test_corpus(n_executions=2)
        config = ModelCorpusReplayConfig()

        await orchestrator.replay(corpus, config)

        assert orchestrator.last_progress is not None
        assert orchestrator.last_progress.total == 2

    def test_cancel_flag(self, orchestrator: ServiceCorpusReplayOrchestrator) -> None:
        """Cancel flag should be set correctly."""
        # Test that cancel() sets the cancelled flag
        assert not orchestrator.is_cancelled
        orchestrator.cancel()
        assert orchestrator.is_cancelled

        # And reset() clears it
        orchestrator.reset()
        assert not orchestrator.is_cancelled

    def test_reset(self, orchestrator: ServiceCorpusReplayOrchestrator) -> None:
        """Reset should clear state."""
        # Use public cancel() method instead of setting _cancelled directly
        orchestrator.cancel()
        # Note: Direct access to _last_progress is required for testing reset() because
        # there's no public setter - _last_progress is only set internally during replay.
        # This is intentional design: tests need to verify reset() clears internal state.
        orchestrator._last_progress = MagicMock()

        orchestrator.reset()

        assert not orchestrator.is_cancelled
        assert orchestrator.last_progress is None

    @pytest.mark.asyncio
    async def test_aggregate_metrics(
        self, orchestrator: ServiceCorpusReplayOrchestrator
    ) -> None:
        """Result should include aggregate metrics."""
        corpus = _create_test_corpus(n_executions=5)
        config = ModelCorpusReplayConfig()

        result = await orchestrator.replay(corpus, config)

        assert result.aggregate_metrics is not None
        assert result.aggregate_metrics.success_rate == 1.0
        assert result.aggregate_metrics.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_config_overrides_stored(
        self, orchestrator: ServiceCorpusReplayOrchestrator
    ) -> None:
        """Config overrides should be stored in result."""
        corpus = _create_test_corpus(n_executions=2)
        config = ModelCorpusReplayConfig(
            config_overrides={"timeout_ms": 5000, "debug": True}
        )

        result = await orchestrator.replay(corpus, config)

        assert result.config_overrides == {"timeout_ms": 5000, "debug": True}
