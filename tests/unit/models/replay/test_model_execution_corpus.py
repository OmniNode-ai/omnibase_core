# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
TDD tests for ModelExecutionCorpus - Execution Corpus Model for Beta Demo.

A corpus is a curated collection of 20-50+ real production requests used for
systematic testing and comparison. Tests define expected behavior for:

- Corpus creation with metadata (name, version, source)
- Execution manifest collection management
- Statistics calculation (total, success rate, duration, handler distribution)
- Query methods (filter by handler, time range)
- Serialization/deserialization (JSON, YAML)
- Validation for replay (non-empty requirement)
- Reference mode vs materialized mode
- Corpus versioning

This test file follows TDD - tests are written BEFORE implementation.

Related:
    - OMN-1202: Execution Corpus Model for Beta Demo
    - ModelExecutionManifest: Individual execution manifest model
    - ModelEffectRecord: Effect record for replay
    - ModelReplayContext: Replay context model

.. versionadded:: 0.4.0
    Added as part of Execution Corpus Model (OMN-1202)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.errors import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.replay import ModelExecutionCorpus


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_node_identity_data() -> dict[str, Any]:
    """Create sample node identity data."""
    return {
        "node_id": "compute-text-transform-001",
        "node_kind": "compute",
        "node_version": {"major": 1, "minor": 0, "patch": 0},
        "namespace": "onex.text",
    }


@pytest.fixture
def sample_contract_identity_data() -> dict[str, Any]:
    """Create sample contract identity data."""
    return {
        "contract_id": "contract-001",
        "contract_path": "contracts/text/transform.yaml",
    }


@pytest.fixture
def create_test_manifest():
    """Factory fixture for creating test execution manifests."""
    from omnibase_core.enums.enum_node_kind import EnumNodeKind
    from omnibase_core.models.manifest.model_contract_identity import (
        ModelContractIdentity,
    )
    from omnibase_core.models.manifest.model_execution_manifest import (
        ModelExecutionManifest,
    )
    from omnibase_core.models.manifest.model_node_identity import ModelNodeIdentity
    from omnibase_core.models.primitives.model_semver import ModelSemVer

    def _create(
        node_id: str = "compute-001",
        handler_name: str = "text_handler",
        success: bool = True,
        created_at: datetime | None = None,
        duration_ms: float = 100.0,
    ) -> ModelExecutionManifest:
        """Create a test manifest with configurable properties.

        Args:
            node_id: Unique identifier for the node
            handler_name: Handler name for filtering/grouping
            success: Whether execution was successful
            created_at: Timestamp for the manifest (defaults to now)
            duration_ms: Execution duration in milliseconds

        Returns:
            A configured ModelExecutionManifest instance
        """
        from omnibase_core.models.manifest.model_manifest_failure import (
            ModelManifestFailure,
        )
        from omnibase_core.models.manifest.model_metrics_summary import (
            ModelMetricsSummary,
        )

        # Build hook traces based on success
        hook_traces = []
        failures = []

        if not success:
            from omnibase_core.enums.enum_handler_execution_phase import (
                EnumHandlerExecutionPhase,
            )

            failures.append(
                ModelManifestFailure(
                    failed_at=created_at or datetime.now(UTC),
                    error_code="EXECUTION_ERROR",
                    error_message="Test failure",
                    phase=EnumHandlerExecutionPhase.EXECUTE,
                )
            )

        return ModelExecutionManifest(
            manifest_id=uuid4(),
            created_at=created_at or datetime.now(UTC),
            node_identity=ModelNodeIdentity(
                node_id=node_id,
                node_kind=EnumNodeKind.COMPUTE,
                node_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_descriptor_id=handler_name,
            ),
            contract_identity=ModelContractIdentity(
                contract_id=f"contract-{node_id}",
            ),
            hook_traces=hook_traces,
            failures=failures,
            metrics_summary=ModelMetricsSummary(total_duration_ms=duration_ms),
        )

    return _create


@pytest.fixture
def sample_manifest(create_test_manifest) -> ModelExecutionManifest:
    """Create a single sample execution manifest."""
    return create_test_manifest()


@pytest.fixture
def create_corpus_with_executions(create_test_manifest):
    """Factory fixture for creating corpus with N executions."""

    def _create(
        count: int = 5,
        name: str = "test-corpus",
        version: str = "1.0.0",
        source: str = "unit-tests",
    ) -> ModelExecutionCorpus:
        """Create a corpus with the specified number of executions.

        Args:
            count: Number of execution manifests to create
            name: Corpus name
            version: Corpus version
            source: Corpus source identifier

        Returns:
            A configured ModelExecutionCorpus instance
        """
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        manifests = []
        for i in range(count):
            manifest = create_test_manifest(
                node_id=f"compute-{i:03d}",
                handler_name=f"handler_{i % 3}",  # Cycle through 3 handlers
                created_at=datetime.now(UTC) + timedelta(seconds=i),
                duration_ms=100.0 + (i * 10),
            )
            manifests.append(manifest)

        return ModelExecutionCorpus(
            name=name,
            version=version,
            source=source,
            executions=tuple(manifests),
        )

    return _create


@pytest.fixture
def create_corpus_with_mixed_results(create_test_manifest):
    """Factory fixture for creating corpus with mixed success/failure results."""

    def _create(
        success_count: int = 7,
        failure_count: int = 3,
        name: str = "mixed-corpus",
    ) -> ModelExecutionCorpus:
        """Create a corpus with specified success/failure mix.

        Args:
            success_count: Number of successful executions
            failure_count: Number of failed executions
            name: Corpus name

        Returns:
            A configured ModelExecutionCorpus instance
        """
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        manifests = []

        # Add successful executions
        for i in range(success_count):
            manifest = create_test_manifest(
                node_id=f"success-{i:03d}",
                handler_name="success_handler",
                success=True,
                duration_ms=50.0 + (i * 5),
            )
            manifests.append(manifest)

        # Add failed executions
        for i in range(failure_count):
            manifest = create_test_manifest(
                node_id=f"failure-{i:03d}",
                handler_name="failure_handler",
                success=False,
                duration_ms=200.0 + (i * 10),
            )
            manifests.append(manifest)

        return ModelExecutionCorpus(
            name=name,
            version="1.0.0",
            source="mixed-tests",
            executions=tuple(manifests),
        )

    return _create


# =============================================================================
# Test Classes - Creation and Metadata
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusCreation:
    """Test ModelExecutionCorpus creation with required metadata."""

    def test_corpus_creation_with_required_metadata(self) -> None:
        """Corpus can be created with required metadata (name, version, source)."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="production-corpus-v1",
            version="1.0.0",
            source="production",
        )

        assert corpus.name == "production-corpus-v1"
        assert corpus.version == "1.0.0"
        assert corpus.source == "production"

    def test_corpus_id_auto_generated(self) -> None:
        """Corpus ID is auto-generated as UUID."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus.corpus_id is not None
        assert isinstance(corpus.corpus_id, UUID)

    def test_unique_corpus_ids_for_different_instances(self) -> None:
        """Each corpus instance gets a unique corpus_id."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus1 = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )
        corpus2 = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus1.corpus_id != corpus2.corpus_id

    def test_executions_defaults_to_empty_tuple(self) -> None:
        """Executions defaults to empty tuple when not provided."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus.executions == ()
        assert isinstance(corpus.executions, tuple)

    def test_created_at_auto_generated(self) -> None:
        """Created_at timestamp is auto-generated."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        before = datetime.now(UTC)
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )
        after = datetime.now(UTC)

        assert corpus.created_at is not None
        assert isinstance(corpus.created_at, datetime)
        assert before <= corpus.created_at <= after

    def test_corpus_with_custom_corpus_id(self) -> None:
        """Corpus can be created with custom corpus_id."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        custom_id = uuid4()
        corpus = ModelExecutionCorpus(
            corpus_id=custom_id,
            name="custom-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus.corpus_id == custom_id


@pytest.mark.unit
class TestModelExecutionCorpusRequiredFields:
    """Test ModelExecutionCorpus required field validation."""

    def test_name_is_required(self) -> None:
        """Name field is required."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionCorpus(
                version="1.0.0",
                source="tests",
            )  # type: ignore[call-arg]

        assert "name" in str(exc_info.value)

    def test_version_is_required(self) -> None:
        """Version field is required."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionCorpus(
                name="test-corpus",
                source="tests",
            )  # type: ignore[call-arg]

        assert "version" in str(exc_info.value)

    def test_source_is_required(self) -> None:
        """Source field is required."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionCorpus(
                name="test-corpus",
                version="1.0.0",
            )  # type: ignore[call-arg]

        assert "source" in str(exc_info.value)

    def test_name_cannot_be_empty(self) -> None:
        """Name cannot be an empty string."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        with pytest.raises(ValidationError):
            ModelExecutionCorpus(
                name="",
                version="1.0.0",
                source="tests",
            )


# =============================================================================
# Test Classes - Immutability
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusImmutability:
    """Test ModelExecutionCorpus immutability (frozen model)."""

    def test_model_is_frozen(self) -> None:
        """Corpus model is frozen (immutable)."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        with pytest.raises(ValidationError):
            corpus.name = "modified-name"

    def test_cannot_modify_version(self) -> None:
        """Version field cannot be reassigned."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        with pytest.raises(ValidationError):
            corpus.version = "2.0.0"

    def test_cannot_modify_executions(self) -> None:
        """Executions field cannot be reassigned."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        with pytest.raises(ValidationError):
            corpus.executions = ()

    def test_cannot_add_new_attribute(self) -> None:
        """Cannot add new attributes to frozen model."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        with pytest.raises(ValidationError):
            corpus.new_attr = "value"


# =============================================================================
# Test Classes - Adding Executions
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusAddExecution:
    """Test adding execution manifests to corpus."""

    def test_add_single_execution_to_corpus(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Can add a single execution manifest to corpus."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            executions=(sample_manifest,),
        )

        assert len(corpus.executions) == 1
        assert corpus.executions[0] == sample_manifest

    def test_add_multiple_executions_to_corpus(self, create_test_manifest) -> None:
        """Can add multiple execution manifests to corpus."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        manifests = tuple(create_test_manifest(node_id=f"node-{i}") for i in range(5))

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            executions=manifests,
        )

        assert len(corpus.executions) == 5

    def test_with_execution_returns_new_corpus(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """with_execution returns a new corpus instance (immutable update)."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        new_corpus = corpus.with_execution(sample_manifest)

        assert new_corpus is not corpus
        assert len(new_corpus.executions) == 1
        assert len(corpus.executions) == 0

    def test_with_execution_preserves_metadata(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """with_execution preserves corpus metadata."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        new_corpus = corpus.with_execution(sample_manifest)

        assert new_corpus.name == corpus.name
        assert new_corpus.version == corpus.version
        assert new_corpus.source == corpus.source
        assert new_corpus.corpus_id == corpus.corpus_id

    def test_with_execution_accumulates(self, create_test_manifest) -> None:
        """with_execution accumulates multiple manifests."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        m1 = create_test_manifest(node_id="node-1")
        m2 = create_test_manifest(node_id="node-2")
        m3 = create_test_manifest(node_id="node-3")

        corpus = corpus.with_execution(m1)
        corpus = corpus.with_execution(m2)
        corpus = corpus.with_execution(m3)

        assert len(corpus.executions) == 3


# =============================================================================
# Test Classes - Bulk Operations
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusBulkOperations:
    """Test bulk operations for adding multiple executions/refs at once."""

    def test_with_executions_adds_multiple_manifests(
        self, create_test_manifest
    ) -> None:
        """with_executions adds multiple manifests in one call."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        manifests = [
            create_test_manifest(node_id="node-1"),
            create_test_manifest(node_id="node-2"),
            create_test_manifest(node_id="node-3"),
        ]

        new_corpus = corpus.with_executions(manifests)

        assert len(new_corpus.executions) == 3
        assert len(corpus.executions) == 0  # Original unchanged

    def test_with_executions_returns_new_corpus(self, create_test_manifest) -> None:
        """with_executions returns a new corpus instance (immutable update)."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        manifests = [create_test_manifest(node_id="node-1")]
        new_corpus = corpus.with_executions(manifests)

        assert new_corpus is not corpus

    def test_with_executions_preserves_metadata(self, create_test_manifest) -> None:
        """with_executions preserves corpus metadata."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        manifests = [create_test_manifest(node_id="node-1")]
        new_corpus = corpus.with_executions(manifests)

        assert new_corpus.name == corpus.name
        assert new_corpus.version == corpus.version
        assert new_corpus.source == corpus.source
        assert new_corpus.corpus_id == corpus.corpus_id

    def test_with_executions_appends_to_existing(self, create_test_manifest) -> None:
        """with_executions appends to existing executions."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        initial_manifest = create_test_manifest(node_id="initial")
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            executions=(initial_manifest,),
        )

        new_manifests = [
            create_test_manifest(node_id="new-1"),
            create_test_manifest(node_id="new-2"),
        ]

        new_corpus = corpus.with_executions(new_manifests)

        assert len(new_corpus.executions) == 3
        assert new_corpus.executions[0].node_identity.node_id == "initial"
        assert new_corpus.executions[1].node_identity.node_id == "new-1"
        assert new_corpus.executions[2].node_identity.node_id == "new-2"

    def test_with_executions_with_tuple(self, create_test_manifest) -> None:
        """with_executions works with tuple input."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        manifests = (
            create_test_manifest(node_id="node-1"),
            create_test_manifest(node_id="node-2"),
        )

        new_corpus = corpus.with_executions(manifests)

        assert len(new_corpus.executions) == 2

    def test_with_executions_empty_list(self) -> None:
        """with_executions with empty list returns equivalent corpus."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        new_corpus = corpus.with_executions([])

        assert len(new_corpus.executions) == 0
        assert new_corpus is not corpus  # Still a new instance

    def test_with_execution_refs_adds_multiple_ids(self) -> None:
        """with_execution_refs adds multiple UUIDs in one call."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        ids = [uuid4(), uuid4(), uuid4()]
        new_corpus = corpus.with_execution_refs(ids)

        assert len(new_corpus.execution_ids) == 3
        assert len(corpus.execution_ids) == 0  # Original unchanged

    def test_with_execution_refs_returns_new_corpus(self) -> None:
        """with_execution_refs returns a new corpus instance (immutable update)."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        new_corpus = corpus.with_execution_refs([uuid4()])

        assert new_corpus is not corpus

    def test_with_execution_refs_preserves_metadata(self) -> None:
        """with_execution_refs preserves corpus metadata."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        new_corpus = corpus.with_execution_refs([uuid4()])

        assert new_corpus.name == corpus.name
        assert new_corpus.version == corpus.version
        assert new_corpus.source == corpus.source
        assert new_corpus.corpus_id == corpus.corpus_id

    def test_with_execution_refs_appends_to_existing(self) -> None:
        """with_execution_refs appends to existing execution_ids."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        initial_id = uuid4()
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            execution_ids=(initial_id,),
            is_reference=True,  # Required for corpus with only execution_ids
        )

        new_ids = [uuid4(), uuid4()]
        new_corpus = corpus.with_execution_refs(new_ids)

        assert len(new_corpus.execution_ids) == 3
        assert new_corpus.execution_ids[0] == initial_id

    def test_with_execution_refs_with_tuple(self) -> None:
        """with_execution_refs works with tuple input."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        ids = (uuid4(), uuid4())
        new_corpus = corpus.with_execution_refs(ids)

        assert len(new_corpus.execution_ids) == 2

    def test_with_execution_refs_empty_list(self) -> None:
        """with_execution_refs with empty list returns equivalent corpus."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        new_corpus = corpus.with_execution_refs([])

        assert len(new_corpus.execution_ids) == 0
        assert new_corpus is not corpus  # Still a new instance


# =============================================================================
# Test Classes - Validation for Replay
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusValidationForReplay:
    """Test corpus validation for replay mode."""

    def test_empty_corpus_invalid_for_replay(self) -> None:
        """Empty corpus raises ValidationError on validate_for_replay()."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        with pytest.raises(ModelOnexError, match=r"non-empty|empty|at least one"):
            corpus.validate_for_replay()

    def test_non_empty_corpus_valid_for_replay(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Non-empty corpus passes validate_for_replay()."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            executions=(sample_manifest,),
        )

        # Should not raise
        corpus.validate_for_replay()

    def test_is_valid_for_replay_property(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """is_valid_for_replay property returns correct boolean."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        empty_corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        non_empty_corpus = ModelExecutionCorpus(
            name="non-empty-corpus",
            version="1.0.0",
            source="tests",
            executions=(sample_manifest,),
        )

        assert empty_corpus.is_valid_for_replay is False
        assert non_empty_corpus.is_valid_for_replay is True

    def test_is_valid_for_replay_reference_only_corpus(self) -> None:
        """is_valid_for_replay returns True for reference-only corpus."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        # Create corpus with only execution_ids (reference mode)
        reference_corpus = ModelExecutionCorpus(
            name="reference-corpus",
            version="1.0.0",
            source="tests",
            execution_ids=(uuid4(), uuid4()),
            is_reference=True,
        )

        # Should be valid even though executions tuple is empty
        assert reference_corpus.is_valid_for_replay is True
        assert len(reference_corpus.executions) == 0
        assert len(reference_corpus.execution_ids) == 2

    def test_validate_for_replay_catches_nil_uuid_in_execution_ids(self) -> None:
        """validate_for_replay raises error for nil UUID in execution_ids."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        nil_uuid = UUID(int=0)
        valid_uuid = uuid4()

        # Create corpus with a nil UUID in execution_ids
        corpus = ModelExecutionCorpus(
            name="corpus-with-nil-uuid",
            version="1.0.0",
            source="tests",
            execution_ids=(valid_uuid, nil_uuid),
            is_reference=True,
        )

        with pytest.raises(ModelOnexError, match=r"nil UUID"):
            corpus.validate_for_replay()

    def test_validate_for_replay_passes_with_valid_execution_ids(self) -> None:
        """validate_for_replay passes when all execution_ids are valid UUIDs."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        # Create corpus with valid UUIDs only
        corpus = ModelExecutionCorpus(
            name="corpus-with-valid-uuids",
            version="1.0.0",
            source="tests",
            execution_ids=(uuid4(), uuid4(), uuid4()),
            is_reference=True,
        )

        # Should not raise
        corpus.validate_for_replay()


# =============================================================================
# Test Classes - Serialization
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusJsonSerialization:
    """Test ModelExecutionCorpus JSON serialization."""

    def test_serialization_roundtrip_empty_corpus(self) -> None:
        """Empty corpus serializes to JSON and back correctly."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        # Serialize to dict
        data = corpus.model_dump()

        # Deserialize back
        restored = ModelExecutionCorpus.model_validate(data)

        assert restored.name == corpus.name
        assert restored.version == corpus.version
        assert restored.source == corpus.source
        assert restored.corpus_id == corpus.corpus_id

    def test_json_serialization_roundtrip(self, create_corpus_with_executions) -> None:
        """Corpus serializes to JSON string and back correctly."""
        corpus = create_corpus_with_executions(count=3)

        # Serialize to JSON
        json_str = corpus.model_dump_json()

        # Deserialize back
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        restored = ModelExecutionCorpus.model_validate_json(json_str)

        assert restored.name == corpus.name
        assert restored.version == corpus.version
        assert len(restored.executions) == 3

    def test_serialized_corpus_id_is_string(self) -> None:
        """corpus_id serializes to string in JSON."""
        import json

        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        json_str = corpus.model_dump_json()
        data = json.loads(json_str)

        assert isinstance(data["corpus_id"], str)

    def test_serialized_created_at_is_iso_format(self) -> None:
        """created_at serializes to ISO format string."""
        import json

        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        json_str = corpus.model_dump_json()
        data = json.loads(json_str)

        assert isinstance(data["created_at"], str)
        # Should be parseable back to datetime
        datetime.fromisoformat(data["created_at"])

    def test_serialization_preserves_executions(
        self, create_corpus_with_executions
    ) -> None:
        """Serialization preserves all executions with their data."""
        corpus = create_corpus_with_executions(count=5)

        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        data = corpus.model_dump()
        restored = ModelExecutionCorpus.model_validate(data)

        assert len(restored.executions) == len(corpus.executions)
        for i, (original, restored_exec) in enumerate(
            zip(corpus.executions, restored.executions, strict=True)
        ):
            assert restored_exec.node_identity.node_id == original.node_identity.node_id


# =============================================================================
# Test Classes - Statistics Calculation
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusStatistics:
    """Test ModelExecutionCorpus statistics calculation."""

    def test_empty_corpus_statistics(self) -> None:
        """Empty corpus returns zero statistics."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        stats = corpus.get_statistics()

        assert stats.total_executions == 0
        assert stats.success_count == 0
        assert stats.failure_count == 0
        assert stats.success_rate == 0.0

    def test_total_executions_count(self, create_corpus_with_executions) -> None:
        """Statistics correctly counts total executions."""
        corpus = create_corpus_with_executions(count=10)

        stats = corpus.get_statistics()

        assert stats.total_executions == 10

    def test_success_rate_calculation(self, create_corpus_with_mixed_results) -> None:
        """Success rate is calculated correctly."""
        corpus = create_corpus_with_mixed_results(success_count=7, failure_count=3)

        stats = corpus.get_statistics()

        assert stats.total_executions == 10
        assert stats.success_count == 7
        assert stats.failure_count == 3
        assert stats.success_rate == 0.7

    def test_success_rate_all_successful(
        self, create_corpus_with_mixed_results
    ) -> None:
        """Success rate is 1.0 when all executions succeed."""
        corpus = create_corpus_with_mixed_results(success_count=5, failure_count=0)

        stats = corpus.get_statistics()

        assert stats.success_rate == 1.0

    def test_success_rate_all_failed(self, create_corpus_with_mixed_results) -> None:
        """Success rate is 0.0 when all executions fail."""
        corpus = create_corpus_with_mixed_results(success_count=0, failure_count=5)

        stats = corpus.get_statistics()

        assert stats.success_rate == 0.0

    def test_avg_duration_ms_calculation(self, create_corpus_with_executions) -> None:
        """Average duration is calculated correctly."""
        corpus = create_corpus_with_executions(count=5)
        # Durations are 100, 110, 120, 130, 140

        stats = corpus.get_statistics()

        # Average should be (100+110+120+130+140) / 5 = 120.0
        assert stats.avg_duration_ms == 120.0

    def test_handler_distribution_calculation(
        self, create_corpus_with_executions
    ) -> None:
        """Handler distribution is calculated correctly."""
        corpus = create_corpus_with_executions(count=6)
        # With count=6 and i % 3 cycling, we get:
        # handler_0: 2, handler_1: 2, handler_2: 2

        stats = corpus.get_statistics()

        assert len(stats.handler_distribution) == 3
        assert stats.handler_distribution.get("handler_0", 0) == 2
        assert stats.handler_distribution.get("handler_1", 0) == 2
        assert stats.handler_distribution.get("handler_2", 0) == 2


@pytest.mark.unit
class TestModelCorpusStatisticsModel:
    """Test ModelCorpusStatistics model."""

    def test_statistics_model_creation(self) -> None:
        """ModelCorpusStatistics can be created with valid data."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelCorpusStatistics,
        )

        stats = ModelCorpusStatistics(
            total_executions=100,
            success_count=85,
            failure_count=15,
            success_rate=0.85,
            avg_duration_ms=150.5,
            handler_distribution={"handler_a": 50, "handler_b": 50},
        )

        assert stats.total_executions == 100
        assert stats.success_count == 85
        assert stats.success_rate == 0.85

    def test_statistics_model_is_frozen(self) -> None:
        """ModelCorpusStatistics is frozen (immutable)."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelCorpusStatistics,
        )

        stats = ModelCorpusStatistics(
            total_executions=100,
            success_count=85,
            failure_count=15,
            success_rate=0.85,
        )

        with pytest.raises(ValidationError):
            stats.total_executions = 200


# =============================================================================
# Test Classes - Query Methods
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusQueryByHandler:
    """Test querying corpus executions by handler name."""

    def test_get_executions_by_handler(self, create_corpus_with_executions) -> None:
        """Can filter executions by handler name."""
        corpus = create_corpus_with_executions(count=9)
        # With count=9 and i % 3 cycling: handler_0: 3, handler_1: 3, handler_2: 3

        result = corpus.get_executions_by_handler("handler_0")

        assert len(result) == 3
        for manifest in result:
            assert manifest.node_identity.handler_descriptor_id == "handler_0"

    def test_get_executions_by_handler_not_found(
        self, create_corpus_with_executions
    ) -> None:
        """Returns empty tuple when handler not found."""
        corpus = create_corpus_with_executions(count=5)

        result = corpus.get_executions_by_handler("nonexistent_handler")

        assert result == ()

    def test_get_executions_by_handler_empty_corpus(self) -> None:
        """Returns empty tuple for empty corpus."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        result = corpus.get_executions_by_handler("any_handler")

        assert result == ()


# =============================================================================
# Test Classes - Time Range
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusTimeRange:
    """Test corpus time range calculations."""

    def test_time_range_calculation(self, create_corpus_with_executions) -> None:
        """Time range min/max is calculated correctly."""
        corpus = create_corpus_with_executions(count=5)
        # Each manifest is 1 second apart

        time_range = corpus.get_time_range()

        assert time_range is not None
        assert time_range.min_time is not None
        assert time_range.max_time is not None
        assert time_range.min_time < time_range.max_time

    def test_time_range_empty_corpus(self) -> None:
        """Empty corpus returns None time range."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        time_range = corpus.get_time_range()

        assert time_range is None

    def test_time_range_single_execution(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Single execution corpus has equal min/max time."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="single-corpus",
            version="1.0.0",
            source="tests",
            executions=(sample_manifest,),
        )

        time_range = corpus.get_time_range()

        assert time_range is not None
        assert time_range.min_time == time_range.max_time


@pytest.mark.unit
class TestModelCorpusTimeRange:
    """Test ModelCorpusTimeRange model."""

    def test_time_range_model_creation(self) -> None:
        """ModelCorpusTimeRange can be created with valid data."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelCorpusTimeRange,
        )

        min_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        max_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC)

        time_range = ModelCorpusTimeRange(
            min_time=min_time,
            max_time=max_time,
        )

        assert time_range.min_time == min_time
        assert time_range.max_time == max_time

    def test_time_range_duration_property(self) -> None:
        """ModelCorpusTimeRange has duration property."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelCorpusTimeRange,
        )

        min_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        max_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC)

        time_range = ModelCorpusTimeRange(
            min_time=min_time,
            max_time=max_time,
        )

        assert time_range.duration == timedelta(hours=1)


# =============================================================================
# Test Classes - Reference vs Materialized Mode
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusModes:
    """Test corpus reference mode vs materialized mode."""

    def test_default_mode_is_materialized(self) -> None:
        """Default corpus mode is materialized."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus.is_materialized is True
        assert corpus.is_reference is False

    def test_reference_mode_with_manifest_ids(self) -> None:
        """Corpus can be created in reference mode with manifest IDs."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        manifest_ids = (uuid4(), uuid4(), uuid4())

        corpus = ModelExecutionCorpus(
            name="reference-corpus",
            version="1.0.0",
            source="tests",
            execution_ids=manifest_ids,
            is_reference=True,
        )

        assert corpus.is_reference is True
        assert corpus.is_materialized is False
        assert len(corpus.execution_ids) == 3

    def test_reference_mode_has_empty_executions(self) -> None:
        """Reference mode corpus has empty executions tuple."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        manifest_ids = (uuid4(), uuid4())

        corpus = ModelExecutionCorpus(
            name="reference-corpus",
            version="1.0.0",
            source="tests",
            execution_ids=manifest_ids,
            is_reference=True,
        )

        assert corpus.executions == ()
        assert len(corpus.execution_ids) == 2


# =============================================================================
# Test Classes - Mode Consistency Validation
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusModeConsistencyValidation:
    """Test mode consistency validation between is_reference flag and data state."""

    def test_reference_mode_with_executions_raises_error(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Reference mode corpus cannot have materialized executions."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        with pytest.raises(
            ModelOnexError,
            match=r"Reference mode corpus should not have materialized executions",
        ):
            ModelExecutionCorpus(
                name="inconsistent-corpus",
                version="1.0.0",
                source="tests",
                executions=(sample_manifest,),
                is_reference=True,
            )

    def test_refs_only_without_is_reference_raises_error(self) -> None:
        """Corpus with only execution_ids must have is_reference=True."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        with pytest.raises(
            ModelOnexError,
            match=r"Corpus with only execution_ids should have is_reference=True",
        ):
            ModelExecutionCorpus(
                name="inconsistent-corpus",
                version="1.0.0",
                source="tests",
                execution_ids=(uuid4(), uuid4()),
                is_reference=False,  # Explicit False to show intent
            )

    def test_empty_corpus_with_is_reference_false_is_valid(self) -> None:
        """Empty corpus (no executions, no refs) with is_reference=False is valid."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
            is_reference=False,
        )

        assert len(corpus.executions) == 0
        assert len(corpus.execution_ids) == 0
        assert corpus.is_reference is False

    def test_empty_corpus_with_is_reference_true_is_valid(self) -> None:
        """Empty corpus with is_reference=True is valid (awaiting refs)."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="empty-reference-corpus",
            version="1.0.0",
            source="tests",
            is_reference=True,
        )

        assert len(corpus.executions) == 0
        assert len(corpus.execution_ids) == 0
        assert corpus.is_reference is True

    def test_materialized_mode_with_executions_is_valid(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Materialized corpus with executions is valid."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="materialized-corpus",
            version="1.0.0",
            source="tests",
            executions=(sample_manifest,),
            is_reference=False,
        )

        assert len(corpus.executions) == 1
        assert corpus.is_reference is False

    def test_mixed_mode_corpus_is_valid(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Corpus with both executions and refs (mixed mode) is valid."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="mixed-corpus",
            version="1.0.0",
            source="tests",
            executions=(sample_manifest,),
            execution_ids=(uuid4(),),
            is_reference=False,
        )

        assert len(corpus.executions) == 1
        assert len(corpus.execution_ids) == 1
        assert corpus.is_reference is False

    def test_reference_mode_with_refs_only_is_valid(self) -> None:
        """Reference mode corpus with only refs is valid."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="reference-corpus",
            version="1.0.0",
            source="tests",
            execution_ids=(uuid4(), uuid4()),
            is_reference=True,
        )

        assert len(corpus.executions) == 0
        assert len(corpus.execution_ids) == 2
        assert corpus.is_reference is True


# =============================================================================
# Test Classes - Versioning
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusVersioning:
    """Test corpus versioning capabilities."""

    def test_version_string_format(self) -> None:
        """Version is stored as string in expected format."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="2.1.3",
            source="tests",
        )

        assert corpus.version == "2.1.3"

    def test_corpus_can_have_description(self) -> None:
        """Corpus can include optional description."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="production",
            description="Production requests from Q4 2024",
        )

        assert corpus.description == "Production requests from Q4 2024"

    def test_corpus_can_have_tags(self) -> None:
        """Corpus can include optional tags for categorization."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="production",
            tags=("regression", "api-v2", "high-traffic"),
        )

        assert "regression" in corpus.tags
        assert "api-v2" in corpus.tags
        assert len(corpus.tags) == 3


# =============================================================================
# Test Classes - Edge Cases
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_execution_corpus(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Single execution corpus works correctly."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="single-corpus",
            version="1.0.0",
            source="tests",
            executions=(sample_manifest,),
        )

        assert len(corpus.executions) == 1
        stats = corpus.get_statistics()
        assert stats.total_executions == 1

    def test_large_corpus_count(self, create_test_manifest) -> None:
        """Large corpus (50+ executions) works correctly."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        manifests = tuple(create_test_manifest(node_id=f"node-{i}") for i in range(50))

        corpus = ModelExecutionCorpus(
            name="large-corpus",
            version="1.0.0",
            source="tests",
            executions=manifests,
        )

        assert len(corpus.executions) == 50
        stats = corpus.get_statistics()
        assert stats.total_executions == 50

    def test_corpus_execution_count_property(
        self, create_corpus_with_executions
    ) -> None:
        """execution_count property returns correct count."""
        corpus = create_corpus_with_executions(count=7)

        assert corpus.execution_count == 7

    def test_empty_corpus_execution_count(self) -> None:
        """Empty corpus has execution_count of 0."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus.execution_count == 0


# =============================================================================
# Test Classes - Extra Fields Rejected
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusExtraFieldsRejected:
    """Test that extra fields are rejected (extra='forbid')."""

    def test_extra_fields_rejected_at_construction(self) -> None:
        """Extra fields are rejected during construction."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionCorpus(
                name="test-corpus",
                version="1.0.0",
                source="tests",
                extra_field="should_be_rejected",
            )

        error_str = str(exc_info.value)
        assert "extra_field" in error_str.lower() or "extra" in error_str.lower()


# =============================================================================
# Test Classes - Capture Window
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusCaptureWindow:
    """Test capture window time range for corpus creation."""

    def test_capture_window_can_be_specified(self) -> None:
        """Capture window can be specified during corpus creation."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelCorpusCaptureWindow,
            ModelExecutionCorpus,
        )

        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 7, 23, 59, 59, tzinfo=UTC)

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="production",
            capture_window=ModelCorpusCaptureWindow(
                start_time=start,
                end_time=end,
            ),
        )

        assert corpus.capture_window is not None
        assert corpus.capture_window.start_time == start
        assert corpus.capture_window.end_time == end

    def test_capture_window_optional(self) -> None:
        """Capture window is optional."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus.capture_window is None


@pytest.mark.unit
class TestModelCorpusCaptureWindow:
    """Test ModelCorpusCaptureWindow model."""

    def test_capture_window_creation(self) -> None:
        """ModelCorpusCaptureWindow can be created with valid data."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelCorpusCaptureWindow,
        )

        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 7, 23, 59, 59, tzinfo=UTC)

        window = ModelCorpusCaptureWindow(
            start_time=start,
            end_time=end,
        )

        assert window.start_time == start
        assert window.end_time == end

    def test_capture_window_duration(self) -> None:
        """ModelCorpusCaptureWindow has duration property."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelCorpusCaptureWindow,
        )

        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 8, 0, 0, 0, tzinfo=UTC)

        window = ModelCorpusCaptureWindow(
            start_time=start,
            end_time=end,
        )

        assert window.duration == timedelta(days=7)

    def test_capture_window_equal_times_allowed(self) -> None:
        """ModelCorpusCaptureWindow allows equal start and end times."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelCorpusCaptureWindow,
        )

        same_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        window = ModelCorpusCaptureWindow(
            start_time=same_time,
            end_time=same_time,
        )

        assert window.start_time == same_time
        assert window.end_time == same_time
        assert window.duration == timedelta(0)

    def test_capture_window_start_after_end_raises_error(self) -> None:
        """ModelCorpusCaptureWindow raises error if start_time > end_time."""
        from omnibase_core.errors import ModelOnexError
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelCorpusCaptureWindow,
        )

        start = datetime(2024, 1, 8, 0, 0, 0, tzinfo=UTC)  # Later time
        end = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)  # Earlier time

        with pytest.raises(ModelOnexError) as exc_info:
            ModelCorpusCaptureWindow(
                start_time=start,
                end_time=end,
            )

        assert "start_time must be <= end_time" in str(exc_info.value)


# =============================================================================
# Test Classes - String Representation
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusStringRepresentation:
    """Test string representation methods."""

    def test_str_representation(self, create_corpus_with_executions) -> None:
        """__str__ returns human-readable representation."""
        corpus = create_corpus_with_executions(count=5)

        str_repr = str(corpus)

        assert "test-corpus" in str_repr
        assert "5" in str_repr or "executions" in str_repr.lower()

    def test_repr_representation(self) -> None:
        """__repr__ returns detailed representation for debugging."""
        from omnibase_core.models.replay.model_execution_corpus import (
            ModelExecutionCorpus,
        )

        corpus = ModelExecutionCorpus(
            name="debug-corpus",
            version="1.0.0",
            source="tests",
        )

        repr_str = repr(corpus)

        assert "ModelExecutionCorpus" in repr_str
        assert "debug-corpus" in repr_str
