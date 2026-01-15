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

import json
import warnings as warn_module
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.manifest.model_contract_identity import ModelContractIdentity
from omnibase_core.models.manifest.model_execution_manifest import (
    ModelExecutionManifest,
)
from omnibase_core.models.manifest.model_manifest_failure import ModelManifestFailure
from omnibase_core.models.manifest.model_metrics_summary import ModelMetricsSummary
from omnibase_core.models.manifest.model_node_identity import ModelNodeIdentity
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.replay.model_execution_corpus import (
    ModelCorpusCaptureWindow,
    ModelCorpusStatistics,
    ModelCorpusTimeRange,
    ModelExecutionCorpus,
)

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
        # Build hook traces based on success
        hook_traces = []
        failures = []

        if not success:
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
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus.corpus_id is not None
        assert isinstance(corpus.corpus_id, UUID)

    def test_unique_corpus_ids_for_different_instances(self) -> None:
        """Each corpus instance gets a unique corpus_id."""
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
        corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus.executions == ()
        assert isinstance(corpus.executions, tuple)

    def test_created_at_auto_generated(self) -> None:
        """Created_at timestamp is auto-generated."""
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
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionCorpus(
                version="1.0.0",
                source="tests",
            )  # type: ignore[call-arg]

        assert "name" in str(exc_info.value)

    def test_version_is_required(self) -> None:
        """Version field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionCorpus(
                name="test-corpus",
                source="tests",
            )  # type: ignore[call-arg]

        assert "version" in str(exc_info.value)

    def test_source_is_required(self) -> None:
        """Source field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionCorpus(
                name="test-corpus",
                version="1.0.0",
            )  # type: ignore[call-arg]

        assert "source" in str(exc_info.value)

    def test_name_cannot_be_empty(self) -> None:
        """Name cannot be an empty string."""
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
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        with pytest.raises(ValidationError):
            corpus.name = "modified-name"

    def test_cannot_modify_version(self) -> None:
        """Version field cannot be reassigned."""
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        with pytest.raises(ValidationError):
            corpus.version = "2.0.0"

    def test_cannot_modify_executions(self) -> None:
        """Executions field cannot be reassigned."""
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        with pytest.raises(ValidationError):
            corpus.executions = ()

    def test_cannot_add_new_attribute(self) -> None:
        """Cannot add new attributes to frozen model."""
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
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        new_corpus = corpus.with_execution_refs([uuid4()])

        assert new_corpus is not corpus

    def test_with_execution_refs_preserves_metadata(self) -> None:
        """with_execution_refs preserves corpus metadata."""
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
        restored = ModelExecutionCorpus.model_validate_json(json_str)

        assert restored.name == corpus.name
        assert restored.version == corpus.version
        assert len(restored.executions) == 3

    def test_serialized_corpus_id_is_string(self) -> None:
        """corpus_id serializes to string in JSON."""
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
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
        )

        assert corpus.is_materialized is True
        assert corpus.is_reference is False

    def test_reference_mode_with_manifest_ids(self) -> None:
        """Corpus can be created in reference mode with manifest IDs."""
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
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="2.1.3",
            source="tests",
        )

        assert corpus.version == "2.1.3"

    def test_corpus_can_have_description(self) -> None:
        """Corpus can include optional description."""
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="production",
            description="Production requests from Q4 2024",
        )

        assert corpus.description == "Production requests from Q4 2024"

    def test_corpus_can_have_tags(self) -> None:
        """Corpus can include optional tags for categorization."""
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
class TestModelExecutionCorpusSizeValidation:
    """Test corpus size validation methods."""

    def test_validate_size_under_limit_returns_none(
        self, create_corpus_with_executions
    ) -> None:
        """validate_size returns None when corpus is under limit."""
        corpus = create_corpus_with_executions(count=30)

        result = corpus.validate_size()

        assert result is None

    def test_validate_size_at_limit_returns_none(self, create_test_manifest) -> None:
        """validate_size returns None when corpus is exactly at limit (edge case)."""
        # Create corpus with exactly RECOMMENDED_MAX_EXECUTIONS
        manifests = tuple(
            create_test_manifest(node_id=f"node-{i}")
            for i in range(ModelExecutionCorpus.RECOMMENDED_MAX_EXECUTIONS)
        )

        corpus = ModelExecutionCorpus(
            name="exact-limit-corpus",
            version="1.0.0",
            source="tests",
            executions=manifests,
        )

        result = corpus.validate_size()

        assert result is None
        assert corpus.execution_count == 50

    def test_validate_size_over_limit_returns_warning(
        self, create_test_manifest
    ) -> None:
        """validate_size returns warning message when corpus exceeds limit."""
        # Create corpus over the default limit
        manifests = tuple(create_test_manifest(node_id=f"node-{i}") for i in range(60))

        corpus = ModelExecutionCorpus(
            name="oversized-corpus",
            version="1.0.0",
            source="tests",
            executions=manifests,
        )

        result = corpus.validate_size()

        assert result is not None
        assert "oversized-corpus" in result
        assert "60" in result
        assert "50" in result
        assert "exceeding" in result.lower()

    def test_validate_size_custom_limit_under(
        self, create_corpus_with_executions
    ) -> None:
        """validate_size with custom limit returns None when under."""
        corpus = create_corpus_with_executions(count=30)

        # Custom limit of 40
        result = corpus.validate_size(limit=40)

        assert result is None

    def test_validate_size_custom_limit_over(
        self, create_corpus_with_executions
    ) -> None:
        """validate_size with custom limit returns warning when over."""
        corpus = create_corpus_with_executions(count=30)

        # Custom limit of 20 (corpus has 30)
        result = corpus.validate_size(limit=20)

        assert result is not None
        assert "30" in result
        assert "20" in result

    def test_validate_size_empty_corpus(self) -> None:
        """validate_size returns None for empty corpus."""
        corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        result = corpus.validate_size()

        assert result is None

    def test_validate_size_reference_mode_counts_refs(self) -> None:
        """validate_size counts execution_ids in reference mode."""
        # Create reference-mode corpus with 60 refs (over limit)
        ref_ids = tuple(uuid4() for _ in range(60))

        corpus = ModelExecutionCorpus(
            name="reference-corpus",
            version="1.0.0",
            source="tests",
            execution_ids=ref_ids,
            is_reference=True,
        )

        result = corpus.validate_size()

        assert result is not None
        assert "60" in result

    def test_warn_if_large_triggers_warning(self, create_test_manifest) -> None:
        """warn_if_large triggers UserWarning when corpus is over limit."""
        manifests = tuple(create_test_manifest(node_id=f"node-{i}") for i in range(60))

        corpus = ModelExecutionCorpus(
            name="oversized-corpus",
            version="1.0.0",
            source="tests",
            executions=manifests,
        )

        with pytest.warns(UserWarning, match=r"oversized-corpus.*60.*exceeding.*50"):
            corpus.warn_if_large()

    def test_warn_if_large_no_warning_under_limit(
        self, create_corpus_with_executions
    ) -> None:
        """warn_if_large does not trigger warning when under limit."""
        corpus = create_corpus_with_executions(count=30)

        # This should NOT raise any warnings
        with warn_module.catch_warnings(record=True) as w:
            warn_module.simplefilter("always")
            corpus.warn_if_large()
            # Filter for UserWarning only
            user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
            assert len(user_warnings) == 0

    def test_warn_if_large_returns_self_for_chaining(
        self, create_corpus_with_executions
    ) -> None:
        """warn_if_large returns self for method chaining."""
        corpus = create_corpus_with_executions(count=30)

        result = corpus.warn_if_large()

        assert result is corpus

    def test_warn_if_large_returns_self_even_when_warning(
        self, create_test_manifest
    ) -> None:
        """warn_if_large returns self for chaining even when warning is emitted."""
        manifests = tuple(create_test_manifest(node_id=f"node-{i}") for i in range(60))

        corpus = ModelExecutionCorpus(
            name="chained-corpus",
            version="1.0.0",
            source="tests",
            executions=manifests,
        )

        with pytest.warns(UserWarning, match=r"exceeding recommended limit"):
            result = corpus.warn_if_large()

        assert result is corpus

    def test_warn_if_large_custom_limit(self, create_corpus_with_executions) -> None:
        """warn_if_large respects custom limit parameter."""
        corpus = create_corpus_with_executions(count=30)

        # Custom limit of 20 should trigger warning
        with pytest.warns(UserWarning, match=r"30.*exceeding.*20"):
            corpus.warn_if_large(limit=20)

    def test_recommended_max_executions_constant_exists(self) -> None:
        """RECOMMENDED_MAX_EXECUTIONS class constant exists and has correct value."""
        assert hasattr(ModelExecutionCorpus, "RECOMMENDED_MAX_EXECUTIONS")
        assert ModelExecutionCorpus.RECOMMENDED_MAX_EXECUTIONS == 50
        assert isinstance(ModelExecutionCorpus.RECOMMENDED_MAX_EXECUTIONS, int)


@pytest.mark.unit
class TestModelExecutionCorpusEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_execution_corpus(
        self, sample_manifest: ModelExecutionManifest
    ) -> None:
        """Single execution corpus works correctly."""
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
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 8, 0, 0, 0, tzinfo=UTC)

        window = ModelCorpusCaptureWindow(
            start_time=start,
            end_time=end,
        )

        assert window.duration == timedelta(days=7)

    def test_capture_window_equal_times_allowed(self) -> None:
        """ModelCorpusCaptureWindow allows equal start and end times."""
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
        corpus = ModelExecutionCorpus(
            name="debug-corpus",
            version="1.0.0",
            source="tests",
        )

        repr_str = repr(corpus)

        assert "ModelExecutionCorpus" in repr_str
        assert "debug-corpus" in repr_str


# =============================================================================
# Test Classes - to_reference() Method
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusToReference:
    """Test to_reference() method for converting materialized corpus to reference mode."""

    def test_to_reference_converts_materialized_corpus(
        self, create_test_manifest
    ) -> None:
        """to_reference() converts materialized corpus to reference mode."""
        m1 = create_test_manifest(node_id="node-1")
        m2 = create_test_manifest(node_id="node-2")
        m3 = create_test_manifest(node_id="node-3")

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            executions=(m1, m2, m3),
        )

        ref_corpus = corpus.to_reference()

        assert ref_corpus.is_reference is True
        assert ref_corpus.is_materialized is False
        assert len(ref_corpus.executions) == 0
        assert len(ref_corpus.execution_ids) == 3

    def test_to_reference_extracts_manifest_ids_correctly(
        self, create_test_manifest
    ) -> None:
        """to_reference() extracts correct manifest_id from each execution."""
        m1 = create_test_manifest(node_id="node-1")
        m2 = create_test_manifest(node_id="node-2")

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            executions=(m1, m2),
        )

        ref_corpus = corpus.to_reference()

        # Verify the IDs match the original manifest IDs
        assert ref_corpus.execution_ids[0] == m1.manifest_id
        assert ref_corpus.execution_ids[1] == m2.manifest_id

    def test_to_reference_preserves_metadata(self, create_test_manifest) -> None:
        """to_reference() preserves all corpus metadata."""
        capture_window = ModelCorpusCaptureWindow(
            start_time=datetime(2024, 1, 1, tzinfo=UTC),
            end_time=datetime(2024, 1, 31, tzinfo=UTC),
        )

        corpus = ModelExecutionCorpus(
            name="production-corpus",
            version="2.1.0",
            source="production",
            description="Production requests from January",
            tags=("regression", "api-v2"),
            capture_window=capture_window,
            executions=(create_test_manifest(node_id="node-1"),),
        )

        ref_corpus = corpus.to_reference()

        # Verify all metadata is preserved
        assert ref_corpus.name == corpus.name
        assert ref_corpus.version == corpus.version
        assert ref_corpus.source == corpus.source
        assert ref_corpus.description == corpus.description
        assert ref_corpus.tags == corpus.tags
        assert ref_corpus.capture_window == corpus.capture_window
        assert ref_corpus.corpus_id == corpus.corpus_id
        assert ref_corpus.created_at == corpus.created_at

    def test_to_reference_returns_new_instance(self, create_test_manifest) -> None:
        """to_reference() returns a new corpus instance (immutable)."""
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            executions=(create_test_manifest(node_id="node-1"),),
        )

        ref_corpus = corpus.to_reference()

        assert ref_corpus is not corpus
        # Original corpus should be unchanged
        assert len(corpus.executions) == 1
        assert corpus.is_reference is False

    def test_to_reference_on_already_reference_corpus_is_idempotent(self) -> None:
        """to_reference() on an already-reference corpus returns a copy."""
        ref_corpus = ModelExecutionCorpus(
            name="reference-corpus",
            version="1.0.0",
            source="tests",
            execution_ids=(uuid4(), uuid4()),
            is_reference=True,
        )

        result = ref_corpus.to_reference()

        # Should still be in reference mode
        assert result.is_reference is True
        assert len(result.executions) == 0
        # Should preserve existing execution_ids
        assert len(result.execution_ids) == 2
        assert result.execution_ids == ref_corpus.execution_ids
        # Should be a new instance
        assert result is not ref_corpus

    def test_to_reference_on_empty_corpus(self) -> None:
        """to_reference() on empty corpus returns empty reference corpus."""
        empty_corpus = ModelExecutionCorpus(
            name="empty-corpus",
            version="1.0.0",
            source="tests",
        )

        ref_corpus = empty_corpus.to_reference()

        assert ref_corpus.is_reference is True
        assert len(ref_corpus.executions) == 0
        assert len(ref_corpus.execution_ids) == 0
        # Metadata preserved
        assert ref_corpus.name == "empty-corpus"
        assert ref_corpus.version == "1.0.0"

    def test_to_reference_preserves_existing_execution_ids(
        self, create_test_manifest
    ) -> None:
        """to_reference() preserves existing execution_ids and appends new ones."""
        # Create corpus with both executions and existing execution_ids (mixed mode)
        existing_id = uuid4()
        manifest = create_test_manifest(node_id="node-1")

        corpus = ModelExecutionCorpus(
            name="mixed-corpus",
            version="1.0.0",
            source="tests",
            executions=(manifest,),
            execution_ids=(existing_id,),
            is_reference=False,
        )

        ref_corpus = corpus.to_reference()

        # Should have both the existing ID and the extracted ID
        assert len(ref_corpus.execution_ids) == 2
        assert ref_corpus.execution_ids[0] == existing_id  # Existing preserved first
        assert ref_corpus.execution_ids[1] == manifest.manifest_id  # New appended

    def test_to_reference_with_large_corpus(self, create_test_manifest) -> None:
        """to_reference() works correctly with large corpus (50+ executions)."""
        manifests = tuple(create_test_manifest(node_id=f"node-{i}") for i in range(50))
        expected_ids = tuple(m.manifest_id for m in manifests)

        corpus = ModelExecutionCorpus(
            name="large-corpus",
            version="1.0.0",
            source="tests",
            executions=manifests,
        )

        ref_corpus = corpus.to_reference()

        assert ref_corpus.is_reference is True
        assert len(ref_corpus.execution_ids) == 50
        assert ref_corpus.execution_ids == expected_ids

    def test_to_reference_execution_count_unchanged(self, create_test_manifest) -> None:
        """to_reference() preserves execution_count (just in different mode)."""
        manifests = tuple(create_test_manifest(node_id=f"node-{i}") for i in range(5))

        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            executions=manifests,
        )

        ref_corpus = corpus.to_reference()

        # Total count should be the same
        assert corpus.execution_count == 5
        assert ref_corpus.execution_count == 5

    def test_to_reference_is_valid_for_replay(self, create_test_manifest) -> None:
        """to_reference() result is still valid for replay."""
        corpus = ModelExecutionCorpus(
            name="test-corpus",
            version="1.0.0",
            source="tests",
            executions=(create_test_manifest(node_id="node-1"),),
        )

        ref_corpus = corpus.to_reference()

        # Should still be valid for replay (has at least one execution ID)
        assert ref_corpus.is_valid_for_replay is True
        # Should pass validation
        ref_corpus.validate_for_replay()  # Should not raise


# =============================================================================
# Test Classes - merge() Method
# =============================================================================


@pytest.mark.unit
class TestModelExecutionCorpusMerge:
    """Test merge() method for combining multiple corpora."""

    def test_merge_two_materialized_corpora(self, create_test_manifest) -> None:
        """Merging two materialized corpora combines their executions."""
        manifest1 = create_test_manifest(node_id="node-1")
        manifest2 = create_test_manifest(node_id="node-2")

        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="production",
            executions=(manifest1,),
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="2.0.0",
            source="staging",
            executions=(manifest2,),
        )

        merged = corpus_a.merge(corpus_b)

        assert len(merged.executions) == 2
        assert merged.executions[0].node_identity.node_id == "node-1"
        assert merged.executions[1].node_identity.node_id == "node-2"
        # Primary metadata preserved
        assert merged.name == "corpus-a"
        assert merged.version == "1.0.0"
        assert merged.source == "production"

    def test_merge_two_reference_corpora(self) -> None:
        """Merging two reference corpora combines their execution_ids."""
        id1, id2, id3 = uuid4(), uuid4(), uuid4()

        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
            execution_ids=(id1,),
            is_reference=True,
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="1.0.0",
            source="tests",
            execution_ids=(id2, id3),
            is_reference=True,
        )

        merged = corpus_a.merge(corpus_b)

        assert len(merged.execution_ids) == 3
        assert merged.execution_ids == (id1, id2, id3)
        assert merged.is_reference is True
        assert len(merged.executions) == 0

    def test_merge_materialized_with_reference(self, create_test_manifest) -> None:
        """Merging materialized with reference corpus produces mixed mode."""
        manifest = create_test_manifest(node_id="node-1")
        ref_id = uuid4()

        materialized = ModelExecutionCorpus(
            name="materialized",
            version="1.0.0",
            source="production",
            executions=(manifest,),
        )
        reference = ModelExecutionCorpus(
            name="reference",
            version="1.0.0",
            source="tests",
            execution_ids=(ref_id,),
            is_reference=True,
        )

        merged = materialized.merge(reference)

        assert len(merged.executions) == 1
        assert len(merged.execution_ids) == 1
        # Has executions, so it's materialized mode
        assert merged.is_reference is False
        assert merged.is_materialized is True

    def test_merge_multiple_corpora_variadic(self, create_test_manifest) -> None:
        """Merging multiple corpora via variadic args works correctly."""
        manifests = [create_test_manifest(node_id=f"node-{i}") for i in range(4)]

        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
            executions=(manifests[0],),
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="1.0.0",
            source="tests",
            executions=(manifests[1],),
        )
        corpus_c = ModelExecutionCorpus(
            name="corpus-c",
            version="1.0.0",
            source="tests",
            executions=(manifests[2],),
        )
        corpus_d = ModelExecutionCorpus(
            name="corpus-d",
            version="1.0.0",
            source="tests",
            executions=(manifests[3],),
        )

        merged = corpus_a.merge(corpus_b, corpus_c, corpus_d)

        assert len(merged.executions) == 4
        for i, exec_manifest in enumerate(merged.executions):
            assert exec_manifest.node_identity.node_id == f"node-{i}"

    def test_merge_tags_deduplicated(self, create_test_manifest) -> None:
        """Tags are deduplicated when merging corpora."""
        manifest1 = create_test_manifest(node_id="node-1")
        manifest2 = create_test_manifest(node_id="node-2")

        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
            executions=(manifest1,),
            tags=("api", "beta", "v2"),
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="1.0.0",
            source="tests",
            executions=(manifest2,),
            tags=("api", "production", "v2"),  # "api" and "v2" are duplicates
        )

        merged = corpus_a.merge(corpus_b)

        # Should have unique tags in order: api, beta, v2, production
        assert "api" in merged.tags
        assert "beta" in merged.tags
        assert "v2" in merged.tags
        assert "production" in merged.tags
        # Count each tag appears exactly once
        assert merged.tags.count("api") == 1
        assert merged.tags.count("v2") == 1
        # Order preserved: corpus_a tags first, then new ones from corpus_b
        assert merged.tags == ("api", "beta", "v2", "production")

    def test_merge_with_empty_corpus(self, create_test_manifest) -> None:
        """Merging with an empty corpus works correctly."""
        manifest = create_test_manifest(node_id="node-1")

        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
            executions=(manifest,),
            tags=("tag1",),
        )
        empty_corpus = ModelExecutionCorpus(
            name="empty",
            version="1.0.0",
            source="tests",
        )

        merged = corpus_a.merge(empty_corpus)

        assert len(merged.executions) == 1
        assert merged.tags == ("tag1",)
        assert merged.name == "corpus-a"

    def test_merge_execution_ids_deduplicated(self) -> None:
        """Duplicate execution_ids are deduplicated when merging."""
        shared_id = uuid4()
        unique_id1 = uuid4()
        unique_id2 = uuid4()

        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
            execution_ids=(shared_id, unique_id1),
            is_reference=True,
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="1.0.0",
            source="tests",
            execution_ids=(shared_id, unique_id2),  # shared_id is duplicate
            is_reference=True,
        )

        merged = corpus_a.merge(corpus_b)

        # shared_id should appear only once
        assert len(merged.execution_ids) == 3
        assert merged.execution_ids.count(shared_id) == 1
        assert shared_id in merged.execution_ids
        assert unique_id1 in merged.execution_ids
        assert unique_id2 in merged.execution_ids
        # Order preserved: corpus_a ids first
        assert merged.execution_ids[0] == shared_id
        assert merged.execution_ids[1] == unique_id1
        assert merged.execution_ids[2] == unique_id2

    def test_merge_no_args_returns_copy(self, create_test_manifest) -> None:
        """Calling merge with no arguments returns a copy of self."""
        manifest = create_test_manifest(node_id="node-1")

        corpus = ModelExecutionCorpus(
            name="original",
            version="1.0.0",
            source="tests",
            executions=(manifest,),
            tags=("tag1",),
        )

        merged = corpus.merge()

        assert merged is not corpus  # New instance
        assert merged.name == corpus.name
        assert merged.version == corpus.version
        assert len(merged.executions) == 1
        assert merged.tags == ("tag1",)

    def test_merge_preserves_corpus_id(self, create_test_manifest) -> None:
        """Merging preserves the primary corpus's corpus_id."""
        manifest1 = create_test_manifest(node_id="node-1")
        manifest2 = create_test_manifest(node_id="node-2")

        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
            executions=(manifest1,),
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="1.0.0",
            source="tests",
            executions=(manifest2,),
        )

        merged = corpus_a.merge(corpus_b)

        assert merged.corpus_id == corpus_a.corpus_id

    def test_merge_preserves_description(self, create_test_manifest) -> None:
        """Merging preserves the primary corpus's description."""
        manifest1 = create_test_manifest(node_id="node-1")
        manifest2 = create_test_manifest(node_id="node-2")

        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
            description="Primary corpus description",
            executions=(manifest1,),
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="1.0.0",
            source="tests",
            description="Secondary corpus description",
            executions=(manifest2,),
        )

        merged = corpus_a.merge(corpus_b)

        assert merged.description == "Primary corpus description"

    def test_merge_returns_new_instance(self, create_test_manifest) -> None:
        """Merging returns a new corpus instance (immutable pattern)."""
        manifest1 = create_test_manifest(node_id="node-1")
        manifest2 = create_test_manifest(node_id="node-2")

        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
            executions=(manifest1,),
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="1.0.0",
            source="tests",
            executions=(manifest2,),
        )

        merged = corpus_a.merge(corpus_b)

        assert merged is not corpus_a
        assert merged is not corpus_b
        # Originals unchanged
        assert len(corpus_a.executions) == 1
        assert len(corpus_b.executions) == 1

    def test_merge_reference_only_result_is_reference_mode(self) -> None:
        """Merging only reference corpora results in reference mode."""
        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
            execution_ids=(uuid4(),),
            is_reference=True,
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="1.0.0",
            source="tests",
            execution_ids=(uuid4(),),
            is_reference=True,
        )

        merged = corpus_a.merge(corpus_b)

        assert merged.is_reference is True
        assert len(merged.executions) == 0
        assert len(merged.execution_ids) == 2

    def test_merge_empty_corpora(self) -> None:
        """Merging two empty corpora results in an empty corpus."""
        corpus_a = ModelExecutionCorpus(
            name="corpus-a",
            version="1.0.0",
            source="tests",
        )
        corpus_b = ModelExecutionCorpus(
            name="corpus-b",
            version="1.0.0",
            source="tests",
        )

        merged = corpus_a.merge(corpus_b)

        assert len(merged.executions) == 0
        assert len(merged.execution_ids) == 0
        assert merged.is_reference is False  # No refs, so materialized mode
        assert merged.execution_count == 0
