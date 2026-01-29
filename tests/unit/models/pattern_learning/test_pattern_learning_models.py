"""Unit tests for pattern learning contract models.

Tests all aspects of pattern learning models including:
- Model instantiation and validation
- Frozen (immutable) enforcement
- Extra field rejection (extra="forbid")
- Constraint validation (normalized scores, counts)
- Enum behavior and StrValueHelper integration
- Serialization and deserialization round-trips
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.pattern_learning import EnumPatternLifecycleState
from omnibase_core.models.pattern_learning import (
    ModelLearnedPattern,
    ModelPatternLearningMetadata,
    ModelPatternLearningMetrics,
    ModelPatternScoreComponents,
    ModelPatternSignature,
)
from omnibase_core.models.primitives import ModelSemVer

pytestmark = pytest.mark.unit


# =============================================================================
# EnumPatternLifecycleState Tests
# =============================================================================


@pytest.mark.unit
class TestEnumPatternLifecycleStateValues:
    """Tests for EnumPatternLifecycleState enum values."""

    def test_candidate_value(self) -> None:
        """CANDIDATE state should have value 'candidate'."""
        assert EnumPatternLifecycleState.CANDIDATE.value == "candidate"

    def test_provisional_value(self) -> None:
        """PROVISIONAL state should have value 'provisional'."""
        assert EnumPatternLifecycleState.PROVISIONAL.value == "provisional"

    def test_validated_value(self) -> None:
        """VALIDATED state should have value 'validated'."""
        assert EnumPatternLifecycleState.VALIDATED.value == "validated"

    def test_deprecated_value(self) -> None:
        """DEPRECATED state should have value 'deprecated'."""
        assert EnumPatternLifecycleState.DEPRECATED.value == "deprecated"

    def test_all_states_exist(self) -> None:
        """All expected lifecycle states should exist."""
        states = list(EnumPatternLifecycleState)
        assert len(states) == 4
        assert EnumPatternLifecycleState.CANDIDATE in states
        assert EnumPatternLifecycleState.PROVISIONAL in states
        assert EnumPatternLifecycleState.VALIDATED in states
        assert EnumPatternLifecycleState.DEPRECATED in states


@pytest.mark.unit
class TestEnumPatternLifecycleStateStrValueHelper:
    """Tests for StrValueHelper integration with EnumPatternLifecycleState."""

    def test_str_returns_value_candidate(self) -> None:
        """str() on CANDIDATE should return 'candidate'."""
        assert str(EnumPatternLifecycleState.CANDIDATE) == "candidate"

    def test_str_returns_value_provisional(self) -> None:
        """str() on PROVISIONAL should return 'provisional'."""
        assert str(EnumPatternLifecycleState.PROVISIONAL) == "provisional"

    def test_str_returns_value_validated(self) -> None:
        """str() on VALIDATED should return 'validated'."""
        assert str(EnumPatternLifecycleState.VALIDATED) == "validated"

    def test_str_returns_value_deprecated(self) -> None:
        """str() on DEPRECATED should return 'deprecated'."""
        assert str(EnumPatternLifecycleState.DEPRECATED) == "deprecated"

    def test_enum_is_str_subclass(self) -> None:
        """Enum should be a subclass of str for JSON serialization."""
        state = EnumPatternLifecycleState.VALIDATED
        assert isinstance(state, str)


# =============================================================================
# ModelPatternScoreComponents Tests
# =============================================================================


@pytest.mark.unit
class TestModelPatternScoreComponentsValidConstruction:
    """Tests for valid ModelPatternScoreComponents construction."""

    def test_construct_with_valid_scores(self) -> None:
        """Should construct with valid normalized scores."""
        model = ModelPatternScoreComponents(
            label_agreement=0.8,
            cluster_cohesion=0.7,
            frequency_factor=0.6,
            confidence=0.72,
        )
        assert model.label_agreement == 0.8
        assert model.cluster_cohesion == 0.7
        assert model.frequency_factor == 0.6
        assert model.confidence == 0.72

    def test_construct_with_boundary_values_zero(self) -> None:
        """Should accept 0.0 as valid boundary value."""
        model = ModelPatternScoreComponents(
            label_agreement=0.0,
            cluster_cohesion=0.0,
            frequency_factor=0.0,
            confidence=0.0,
        )
        assert model.label_agreement == 0.0
        assert model.cluster_cohesion == 0.0
        assert model.frequency_factor == 0.0
        assert model.confidence == 0.0

    def test_construct_with_boundary_values_one(self) -> None:
        """Should accept 1.0 as valid boundary value."""
        model = ModelPatternScoreComponents(
            label_agreement=1.0,
            cluster_cohesion=1.0,
            frequency_factor=1.0,
            confidence=1.0,
        )
        assert model.label_agreement == 1.0
        assert model.cluster_cohesion == 1.0
        assert model.frequency_factor == 1.0
        assert model.confidence == 1.0

    def test_construct_with_mid_range_values(self) -> None:
        """Should accept mid-range values."""
        model = ModelPatternScoreComponents(
            label_agreement=0.5,
            cluster_cohesion=0.333,
            frequency_factor=0.666,
            confidence=0.499,
        )
        assert model.label_agreement == 0.5
        assert model.cluster_cohesion == 0.333
        assert model.frequency_factor == 0.666
        assert model.confidence == 0.499


@pytest.mark.unit
class TestModelPatternScoreComponentsConstraintValidation:
    """Tests for constraint validation in ModelPatternScoreComponents."""

    def test_rejects_label_agreement_above_one(self) -> None:
        """Should reject label_agreement > 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternScoreComponents(
                label_agreement=1.5,
                cluster_cohesion=0.7,
                frequency_factor=0.6,
                confidence=0.72,
            )
        assert "label_agreement" in str(exc_info.value)

    def test_rejects_label_agreement_negative(self) -> None:
        """Should reject label_agreement < 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternScoreComponents(
                label_agreement=-0.1,
                cluster_cohesion=0.7,
                frequency_factor=0.6,
                confidence=0.72,
            )
        assert "label_agreement" in str(exc_info.value)

    def test_rejects_cluster_cohesion_above_one(self) -> None:
        """Should reject cluster_cohesion > 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternScoreComponents(
                label_agreement=0.8,
                cluster_cohesion=1.001,
                frequency_factor=0.6,
                confidence=0.72,
            )
        assert "cluster_cohesion" in str(exc_info.value)

    def test_rejects_cluster_cohesion_negative(self) -> None:
        """Should reject cluster_cohesion < 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternScoreComponents(
                label_agreement=0.8,
                cluster_cohesion=-0.5,
                frequency_factor=0.6,
                confidence=0.72,
            )
        assert "cluster_cohesion" in str(exc_info.value)

    def test_rejects_frequency_factor_above_one(self) -> None:
        """Should reject frequency_factor > 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternScoreComponents(
                label_agreement=0.8,
                cluster_cohesion=0.7,
                frequency_factor=2.0,
                confidence=0.72,
            )
        assert "frequency_factor" in str(exc_info.value)

    def test_rejects_frequency_factor_negative(self) -> None:
        """Should reject frequency_factor < 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternScoreComponents(
                label_agreement=0.8,
                cluster_cohesion=0.7,
                frequency_factor=-0.001,
                confidence=0.72,
            )
        assert "frequency_factor" in str(exc_info.value)

    def test_rejects_confidence_above_one(self) -> None:
        """Should reject confidence > 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternScoreComponents(
                label_agreement=0.8,
                cluster_cohesion=0.7,
                frequency_factor=0.6,
                confidence=1.1,
            )
        assert "confidence" in str(exc_info.value)

    def test_rejects_confidence_negative(self) -> None:
        """Should reject confidence < 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternScoreComponents(
                label_agreement=0.8,
                cluster_cohesion=0.7,
                frequency_factor=0.6,
                confidence=-0.01,
            )
        assert "confidence" in str(exc_info.value)


@pytest.mark.unit
class TestModelPatternScoreComponentsFrozen:
    """Tests for frozen (immutable) enforcement in ModelPatternScoreComponents."""

    def test_frozen_rejects_mutation_label_agreement(self) -> None:
        """Frozen model should reject label_agreement assignment."""
        model = ModelPatternScoreComponents(
            label_agreement=0.8,
            cluster_cohesion=0.7,
            frequency_factor=0.6,
            confidence=0.72,
        )
        with pytest.raises(ValidationError) as exc_info:
            model.label_agreement = 0.9
        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_rejects_mutation_cluster_cohesion(self) -> None:
        """Frozen model should reject cluster_cohesion assignment."""
        model = ModelPatternScoreComponents(
            label_agreement=0.8,
            cluster_cohesion=0.7,
            frequency_factor=0.6,
            confidence=0.72,
        )
        with pytest.raises(ValidationError) as exc_info:
            model.cluster_cohesion = 0.5
        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_rejects_mutation_confidence(self) -> None:
        """Frozen model should reject confidence assignment."""
        model = ModelPatternScoreComponents(
            label_agreement=0.8,
            cluster_cohesion=0.7,
            frequency_factor=0.6,
            confidence=0.72,
        )
        with pytest.raises(ValidationError) as exc_info:
            model.confidence = 1.0
        assert "frozen" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelPatternScoreComponentsExtraFields:
    """Tests for extra field rejection in ModelPatternScoreComponents."""

    def test_rejects_extra_fields(self) -> None:
        """Should reject extra fields not in the model."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternScoreComponents(
                label_agreement=0.8,
                cluster_cohesion=0.7,
                frequency_factor=0.6,
                confidence=0.72,
                extra_field="invalid",  # type: ignore[call-arg]
            )
        assert "extra_field" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelPatternScoreComponentsSerialization:
    """Tests for serialization of ModelPatternScoreComponents."""

    def test_model_dump(self) -> None:
        """model_dump() should return correct dict."""
        model = ModelPatternScoreComponents(
            label_agreement=0.8,
            cluster_cohesion=0.7,
            frequency_factor=0.6,
            confidence=0.72,
        )
        data = model.model_dump()
        assert data["label_agreement"] == 0.8
        assert data["cluster_cohesion"] == 0.7
        assert data["frequency_factor"] == 0.6
        assert data["confidence"] == 0.72

    def test_model_validate_round_trip(self) -> None:
        """model_validate() should correctly reconstruct from dict."""
        original = ModelPatternScoreComponents(
            label_agreement=0.8,
            cluster_cohesion=0.7,
            frequency_factor=0.6,
            confidence=0.72,
        )
        data = original.model_dump()
        reconstructed = ModelPatternScoreComponents.model_validate(data)
        assert reconstructed == original


# =============================================================================
# ModelPatternSignature Tests
# =============================================================================


@pytest.mark.unit
class TestModelPatternSignatureValidConstruction:
    """Tests for valid ModelPatternSignature construction."""

    def test_construct_with_required_fields(self) -> None:
        """Should construct with all required fields."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        model = ModelPatternSignature(
            signature="abc123def456",
            signature_version=version,
            signature_inputs=("input1", "input2", "input3"),
            normalization_applied="lowercase_sort_dedupe",
        )
        assert model.signature == "abc123def456"
        assert model.signature_version == version
        assert model.signature_inputs == ("input1", "input2", "input3")
        assert model.normalization_applied == "lowercase_sort_dedupe"

    def test_construct_with_empty_signature_inputs_tuple(self) -> None:
        """Should accept empty tuple for signature_inputs."""
        model = ModelPatternSignature(
            signature="abc123",
            signature_version=ModelSemVer(major=1, minor=0, patch=0),
            signature_inputs=(),
            normalization_applied="none",
        )
        assert model.signature_inputs == ()

    def test_construct_with_single_signature_input(self) -> None:
        """Should accept single-element tuple for signature_inputs."""
        model = ModelPatternSignature(
            signature="abc123",
            signature_version=ModelSemVer(major=1, minor=0, patch=0),
            signature_inputs=("single_input",),
            normalization_applied="lowercase",
        )
        assert model.signature_inputs == ("single_input",)


@pytest.mark.unit
class TestModelPatternSignatureTupleImmutability:
    """Tests for tuple immutability in ModelPatternSignature."""

    def test_signature_inputs_is_tuple(self) -> None:
        """signature_inputs should be a tuple, not a list."""
        model = ModelPatternSignature(
            signature="abc123",
            signature_version=ModelSemVer(major=1, minor=0, patch=0),
            signature_inputs=("a", "b", "c"),
            normalization_applied="sort",
        )
        assert isinstance(model.signature_inputs, tuple)

    def test_signature_inputs_accepts_list_converted_to_tuple(self) -> None:
        """Should accept list and convert to tuple."""
        model = ModelPatternSignature(
            signature="abc123",
            signature_version=ModelSemVer(major=1, minor=0, patch=0),
            signature_inputs=["a", "b", "c"],  # type: ignore[arg-type]
            normalization_applied="sort",
        )
        assert model.signature_inputs == ("a", "b", "c")
        assert isinstance(model.signature_inputs, tuple)


@pytest.mark.unit
class TestModelPatternSignatureFrozen:
    """Tests for frozen (immutable) enforcement in ModelPatternSignature."""

    def test_frozen_rejects_mutation_signature(self) -> None:
        """Frozen model should reject signature assignment."""
        model = ModelPatternSignature(
            signature="abc123",
            signature_version=ModelSemVer(major=1, minor=0, patch=0),
            signature_inputs=("a", "b"),
            normalization_applied="sort",
        )
        with pytest.raises(ValidationError) as exc_info:
            model.signature = "xyz789"
        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_rejects_mutation_signature_version(self) -> None:
        """Frozen model should reject signature_version assignment."""
        model = ModelPatternSignature(
            signature="abc123",
            signature_version=ModelSemVer(major=1, minor=0, patch=0),
            signature_inputs=("a", "b"),
            normalization_applied="sort",
        )
        with pytest.raises(ValidationError) as exc_info:
            model.signature_version = ModelSemVer(major=2, minor=0, patch=0)
        assert "frozen" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelPatternSignatureExtraFields:
    """Tests for extra field rejection in ModelPatternSignature."""

    def test_rejects_extra_fields(self) -> None:
        """Should reject extra fields not in the model."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternSignature(
                signature="abc123",
                signature_version=ModelSemVer(major=1, minor=0, patch=0),
                signature_inputs=("a",),
                normalization_applied="sort",
                unknown_field="invalid",  # type: ignore[call-arg]
            )
        assert "unknown_field" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelPatternSignatureSerialization:
    """Tests for serialization of ModelPatternSignature."""

    def test_model_dump(self) -> None:
        """model_dump() should return correct dict."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        model = ModelPatternSignature(
            signature="sha256hash",
            signature_version=version,
            signature_inputs=("field1", "field2"),
            normalization_applied="lowercase_sort",
        )
        data = model.model_dump()
        assert data["signature"] == "sha256hash"
        assert data["signature_version"] == version.model_dump()
        # Pydantic serializes tuples as lists by default
        assert data["signature_inputs"] == ("field1", "field2")
        assert data["normalization_applied"] == "lowercase_sort"

    def test_model_validate_round_trip(self) -> None:
        """model_validate() should correctly reconstruct from dict."""
        original = ModelPatternSignature(
            signature="sha256hash",
            signature_version=ModelSemVer(major=1, minor=0, patch=0),
            signature_inputs=("field1", "field2"),
            normalization_applied="lowercase_sort",
        )
        data = original.model_dump()
        reconstructed = ModelPatternSignature.model_validate(data)
        assert reconstructed == original


# =============================================================================
# ModelPatternLearningMetrics Tests
# =============================================================================


@pytest.mark.unit
class TestModelPatternLearningMetricsValidConstruction:
    """Tests for valid ModelPatternLearningMetrics construction."""

    def test_construct_with_valid_values(self) -> None:
        """Should construct with valid metric values."""
        model = ModelPatternLearningMetrics(
            input_count=1000,
            cluster_count=50,
            candidate_count=30,
            learned_count=25,
            discarded_count=5,
            merged_count=10,
            mean_confidence=0.85,
            mean_label_agreement=0.90,
            mean_cluster_cohesion=0.75,
            processing_time_ms=1500.5,
        )
        assert model.input_count == 1000
        assert model.cluster_count == 50
        assert model.candidate_count == 30
        assert model.learned_count == 25
        assert model.discarded_count == 5
        assert model.merged_count == 10
        assert model.mean_confidence == 0.85
        assert model.mean_label_agreement == 0.90
        assert model.mean_cluster_cohesion == 0.75
        assert model.processing_time_ms == 1500.5

    def test_construct_with_zero_counts(self) -> None:
        """Should accept zero for all count fields."""
        model = ModelPatternLearningMetrics(
            input_count=0,
            cluster_count=0,
            candidate_count=0,
            learned_count=0,
            discarded_count=0,
            merged_count=0,
            mean_confidence=0.0,
            mean_label_agreement=0.0,
            mean_cluster_cohesion=0.0,
            processing_time_ms=0.0,
        )
        assert model.input_count == 0
        assert model.cluster_count == 0
        assert model.learned_count == 0

    def test_construct_with_boundary_normalized_scores(self) -> None:
        """Should accept boundary values for normalized scores."""
        model = ModelPatternLearningMetrics(
            input_count=100,
            cluster_count=10,
            candidate_count=8,
            learned_count=5,
            discarded_count=2,
            merged_count=1,
            mean_confidence=1.0,
            mean_label_agreement=1.0,
            mean_cluster_cohesion=1.0,
            processing_time_ms=100.0,
        )
        assert model.mean_confidence == 1.0
        assert model.mean_label_agreement == 1.0
        assert model.mean_cluster_cohesion == 1.0


@pytest.mark.unit
class TestModelPatternLearningMetricsConstraintValidation:
    """Tests for constraint validation in ModelPatternLearningMetrics."""

    def test_rejects_negative_input_count(self) -> None:
        """Should reject negative input_count."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetrics(
                input_count=-1,
                cluster_count=10,
                candidate_count=5,
                learned_count=3,
                discarded_count=1,
                merged_count=1,
                mean_confidence=0.8,
                mean_label_agreement=0.9,
                mean_cluster_cohesion=0.7,
                processing_time_ms=100.0,
            )
        assert "input_count" in str(exc_info.value)

    def test_rejects_negative_cluster_count(self) -> None:
        """Should reject negative cluster_count."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetrics(
                input_count=100,
                cluster_count=-5,
                candidate_count=5,
                learned_count=3,
                discarded_count=1,
                merged_count=1,
                mean_confidence=0.8,
                mean_label_agreement=0.9,
                mean_cluster_cohesion=0.7,
                processing_time_ms=100.0,
            )
        assert "cluster_count" in str(exc_info.value)

    def test_rejects_negative_learned_count(self) -> None:
        """Should reject negative learned_count."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetrics(
                input_count=100,
                cluster_count=10,
                candidate_count=5,
                learned_count=-1,
                discarded_count=1,
                merged_count=1,
                mean_confidence=0.8,
                mean_label_agreement=0.9,
                mean_cluster_cohesion=0.7,
                processing_time_ms=100.0,
            )
        assert "learned_count" in str(exc_info.value)

    def test_rejects_mean_confidence_above_one(self) -> None:
        """Should reject mean_confidence > 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetrics(
                input_count=100,
                cluster_count=10,
                candidate_count=5,
                learned_count=3,
                discarded_count=1,
                merged_count=1,
                mean_confidence=1.5,
                mean_label_agreement=0.9,
                mean_cluster_cohesion=0.7,
                processing_time_ms=100.0,
            )
        assert "mean_confidence" in str(exc_info.value)

    def test_rejects_mean_confidence_negative(self) -> None:
        """Should reject mean_confidence < 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetrics(
                input_count=100,
                cluster_count=10,
                candidate_count=5,
                learned_count=3,
                discarded_count=1,
                merged_count=1,
                mean_confidence=-0.1,
                mean_label_agreement=0.9,
                mean_cluster_cohesion=0.7,
                processing_time_ms=100.0,
            )
        assert "mean_confidence" in str(exc_info.value)

    def test_rejects_negative_processing_time(self) -> None:
        """Should reject negative processing_time_ms."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetrics(
                input_count=100,
                cluster_count=10,
                candidate_count=5,
                learned_count=3,
                discarded_count=1,
                merged_count=1,
                mean_confidence=0.8,
                mean_label_agreement=0.9,
                mean_cluster_cohesion=0.7,
                processing_time_ms=-100.0,
            )
        assert "processing_time_ms" in str(exc_info.value)


@pytest.mark.unit
class TestModelPatternLearningMetricsFrozen:
    """Tests for frozen (immutable) enforcement in ModelPatternLearningMetrics."""

    def test_frozen_rejects_mutation(self) -> None:
        """Frozen model should reject attribute assignment."""
        model = ModelPatternLearningMetrics(
            input_count=100,
            cluster_count=10,
            candidate_count=5,
            learned_count=3,
            discarded_count=1,
            merged_count=1,
            mean_confidence=0.8,
            mean_label_agreement=0.9,
            mean_cluster_cohesion=0.7,
            processing_time_ms=100.0,
        )
        with pytest.raises(ValidationError) as exc_info:
            model.input_count = 200
        assert "frozen" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelPatternLearningMetricsExtraFields:
    """Tests for extra field rejection in ModelPatternLearningMetrics."""

    def test_rejects_extra_fields(self) -> None:
        """Should reject extra fields not in the model."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetrics(
                input_count=100,
                cluster_count=10,
                candidate_count=5,
                learned_count=3,
                discarded_count=1,
                merged_count=1,
                mean_confidence=0.8,
                mean_label_agreement=0.9,
                mean_cluster_cohesion=0.7,
                processing_time_ms=100.0,
                extra_metric="invalid",  # type: ignore[call-arg]
            )
        assert "extra_metric" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelPatternLearningMetricsSerialization:
    """Tests for serialization of ModelPatternLearningMetrics."""

    def test_model_dump(self) -> None:
        """model_dump() should return correct dict."""
        model = ModelPatternLearningMetrics(
            input_count=100,
            cluster_count=10,
            candidate_count=5,
            learned_count=3,
            discarded_count=1,
            merged_count=1,
            mean_confidence=0.8,
            mean_label_agreement=0.9,
            mean_cluster_cohesion=0.7,
            processing_time_ms=150.5,
        )
        data = model.model_dump()
        assert data["input_count"] == 100
        assert data["mean_confidence"] == 0.8
        assert data["processing_time_ms"] == 150.5

    def test_model_validate_round_trip(self) -> None:
        """model_validate() should correctly reconstruct from dict."""
        original = ModelPatternLearningMetrics(
            input_count=100,
            cluster_count=10,
            candidate_count=5,
            learned_count=3,
            discarded_count=1,
            merged_count=1,
            mean_confidence=0.8,
            mean_label_agreement=0.9,
            mean_cluster_cohesion=0.7,
            processing_time_ms=150.5,
        )
        data = original.model_dump()
        reconstructed = ModelPatternLearningMetrics.model_validate(data)
        assert reconstructed == original


# =============================================================================
# ModelPatternLearningMetadata Tests
# =============================================================================


@pytest.mark.unit
class TestModelPatternLearningMetadataValidConstruction:
    """Tests for valid ModelPatternLearningMetadata construction."""

    def test_construct_with_valid_values(self) -> None:
        """Should construct with valid metadata values."""
        now = datetime.now(UTC)
        model = ModelPatternLearningMetadata(
            status="completed",
            model_version=ModelSemVer(major=1, minor=0, patch=0),
            timestamp=now,
            deduplication_threshold_used=0.85,
            promotion_threshold_used=0.70,
            training_samples=10000,
            validation_samples=2000,
            convergence_achieved=True,
            early_stopped=False,
            final_epoch=50,
        )
        assert model.status == "completed"
        assert model.model_version == ModelSemVer(major=1, minor=0, patch=0)
        assert model.timestamp == now
        assert model.deduplication_threshold_used == 0.85
        assert model.promotion_threshold_used == 0.70
        assert model.training_samples == 10000
        assert model.validation_samples == 2000
        assert model.convergence_achieved is True
        assert model.early_stopped is False
        assert model.final_epoch == 50

    def test_construct_with_failed_status(self) -> None:
        """Should accept 'failed' status."""
        model = ModelPatternLearningMetadata(
            status="failed",
            model_version=ModelSemVer(major=1, minor=0, patch=0),
            timestamp=datetime.now(UTC),
            deduplication_threshold_used=0.85,
            promotion_threshold_used=0.70,
            training_samples=1000,
            validation_samples=200,
            convergence_achieved=False,
            early_stopped=True,
            final_epoch=10,
        )
        assert model.status == "failed"
        assert model.early_stopped is True
        assert model.convergence_achieved is False

    def test_construct_with_zero_samples(self) -> None:
        """Should accept zero for sample counts."""
        model = ModelPatternLearningMetadata(
            status="completed",
            model_version=ModelSemVer(major=1, minor=0, patch=0),
            timestamp=datetime.now(UTC),
            deduplication_threshold_used=0.5,
            promotion_threshold_used=0.5,
            training_samples=0,
            validation_samples=0,
            convergence_achieved=False,
            early_stopped=False,
            final_epoch=0,
        )
        assert model.training_samples == 0
        assert model.validation_samples == 0
        assert model.final_epoch == 0


@pytest.mark.unit
class TestModelPatternLearningMetadataConstraintValidation:
    """Tests for constraint validation in ModelPatternLearningMetadata."""

    def test_rejects_deduplication_threshold_above_one(self) -> None:
        """Should reject deduplication_threshold_used > 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetadata(
                status="completed",
                model_version=ModelSemVer(major=1, minor=0, patch=0),
                timestamp=datetime.now(UTC),
                deduplication_threshold_used=1.5,
                promotion_threshold_used=0.70,
                training_samples=1000,
                validation_samples=200,
                convergence_achieved=True,
                early_stopped=False,
                final_epoch=50,
            )
        assert "deduplication_threshold_used" in str(exc_info.value)

    def test_rejects_deduplication_threshold_negative(self) -> None:
        """Should reject deduplication_threshold_used < 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetadata(
                status="completed",
                model_version=ModelSemVer(major=1, minor=0, patch=0),
                timestamp=datetime.now(UTC),
                deduplication_threshold_used=-0.1,
                promotion_threshold_used=0.70,
                training_samples=1000,
                validation_samples=200,
                convergence_achieved=True,
                early_stopped=False,
                final_epoch=50,
            )
        assert "deduplication_threshold_used" in str(exc_info.value)

    def test_rejects_negative_training_samples(self) -> None:
        """Should reject negative training_samples."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetadata(
                status="completed",
                model_version=ModelSemVer(major=1, minor=0, patch=0),
                timestamp=datetime.now(UTC),
                deduplication_threshold_used=0.85,
                promotion_threshold_used=0.70,
                training_samples=-1,
                validation_samples=200,
                convergence_achieved=True,
                early_stopped=False,
                final_epoch=50,
            )
        assert "training_samples" in str(exc_info.value)

    def test_rejects_negative_final_epoch(self) -> None:
        """Should reject negative final_epoch."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetadata(
                status="completed",
                model_version=ModelSemVer(major=1, minor=0, patch=0),
                timestamp=datetime.now(UTC),
                deduplication_threshold_used=0.85,
                promotion_threshold_used=0.70,
                training_samples=1000,
                validation_samples=200,
                convergence_achieved=True,
                early_stopped=False,
                final_epoch=-1,
            )
        assert "final_epoch" in str(exc_info.value)


@pytest.mark.unit
class TestModelPatternLearningMetadataDatetimeHandling:
    """Tests for datetime handling in ModelPatternLearningMetadata."""

    def test_accepts_utc_datetime(self) -> None:
        """Should accept UTC datetime."""
        utc_time = datetime.now(UTC)
        model = ModelPatternLearningMetadata(
            status="completed",
            model_version=ModelSemVer(major=1, minor=0, patch=0),
            timestamp=utc_time,
            deduplication_threshold_used=0.85,
            promotion_threshold_used=0.70,
            training_samples=1000,
            validation_samples=200,
            convergence_achieved=True,
            early_stopped=False,
            final_epoch=50,
        )
        assert model.timestamp == utc_time

    def test_accepts_naive_datetime(self) -> None:
        """Should accept naive datetime (no timezone)."""
        naive_time = datetime(2024, 1, 15, 10, 30, 0)
        model = ModelPatternLearningMetadata(
            status="completed",
            model_version=ModelSemVer(major=1, minor=0, patch=0),
            timestamp=naive_time,
            deduplication_threshold_used=0.85,
            promotion_threshold_used=0.70,
            training_samples=1000,
            validation_samples=200,
            convergence_achieved=True,
            early_stopped=False,
            final_epoch=50,
        )
        assert model.timestamp == naive_time


@pytest.mark.unit
class TestModelPatternLearningMetadataFrozen:
    """Tests for frozen (immutable) enforcement in ModelPatternLearningMetadata."""

    def test_frozen_rejects_mutation(self) -> None:
        """Frozen model should reject attribute assignment."""
        model = ModelPatternLearningMetadata(
            status="completed",
            model_version=ModelSemVer(major=1, minor=0, patch=0),
            timestamp=datetime.now(UTC),
            deduplication_threshold_used=0.85,
            promotion_threshold_used=0.70,
            training_samples=1000,
            validation_samples=200,
            convergence_achieved=True,
            early_stopped=False,
            final_epoch=50,
        )
        with pytest.raises(ValidationError) as exc_info:
            model.status = "failed"
        assert "frozen" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelPatternLearningMetadataExtraFields:
    """Tests for extra field rejection in ModelPatternLearningMetadata."""

    def test_rejects_extra_fields(self) -> None:
        """Should reject extra fields not in the model."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternLearningMetadata(
                status="completed",
                model_version=ModelSemVer(major=1, minor=0, patch=0),
                timestamp=datetime.now(UTC),
                deduplication_threshold_used=0.85,
                promotion_threshold_used=0.70,
                training_samples=1000,
                validation_samples=200,
                convergence_achieved=True,
                early_stopped=False,
                final_epoch=50,
                extra_metadata="invalid",  # type: ignore[call-arg]
            )
        assert "extra_metadata" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelPatternLearningMetadataSerialization:
    """Tests for serialization of ModelPatternLearningMetadata."""

    def test_model_dump(self) -> None:
        """model_dump() should return correct dict."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        version = ModelSemVer(major=1, minor=0, patch=0)
        model = ModelPatternLearningMetadata(
            status="completed",
            model_version=version,
            timestamp=timestamp,
            deduplication_threshold_used=0.85,
            promotion_threshold_used=0.70,
            training_samples=1000,
            validation_samples=200,
            convergence_achieved=True,
            early_stopped=False,
            final_epoch=50,
        )
        data = model.model_dump()
        assert data["status"] == "completed"
        assert data["model_version"] == version.model_dump()
        assert data["timestamp"] == timestamp
        assert data["convergence_achieved"] is True
        assert data["early_stopped"] is False

    def test_model_validate_round_trip(self) -> None:
        """model_validate() should correctly reconstruct from dict."""
        original = ModelPatternLearningMetadata(
            status="completed",
            model_version=ModelSemVer(major=1, minor=0, patch=0),
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            deduplication_threshold_used=0.85,
            promotion_threshold_used=0.70,
            training_samples=1000,
            validation_samples=200,
            convergence_achieved=True,
            early_stopped=False,
            final_epoch=50,
        )
        data = original.model_dump()
        reconstructed = ModelPatternLearningMetadata.model_validate(data)
        assert reconstructed == original


# =============================================================================
# ModelLearnedPattern Tests
# =============================================================================


def _create_valid_score_components() -> ModelPatternScoreComponents:
    """Create valid ModelPatternScoreComponents for testing."""
    return ModelPatternScoreComponents(
        label_agreement=0.85,
        cluster_cohesion=0.75,
        frequency_factor=0.65,
        confidence=0.76,
    )


def _create_valid_signature() -> ModelPatternSignature:
    """Create valid ModelPatternSignature for testing."""
    return ModelPatternSignature(
        signature="sha256_abc123def456",
        signature_version=ModelSemVer(major=1, minor=0, patch=0),
        signature_inputs=("category", "pattern_type", "keywords"),
        normalization_applied="lowercase_sort_dedupe",
    )


# Constant UUID for deterministic testing
TEST_PATTERN_UUID = UUID("12345678-1234-5678-1234-567812345678")


def _create_valid_learned_pattern() -> ModelLearnedPattern:
    """Create valid ModelLearnedPattern for testing."""
    return ModelLearnedPattern(
        pattern_id=TEST_PATTERN_UUID,
        pattern_name="Error Handling Pattern",
        pattern_type="code_pattern",
        category="error_handling",
        subcategory="exception_flow",
        tags=("python", "error", "exception"),
        keywords=("try", "except", "finally"),
        score_components=_create_valid_score_components(),
        signature_info=_create_valid_signature(),
        lifecycle_state=EnumPatternLifecycleState.VALIDATED,
        source_count=5,
        first_seen=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        last_seen=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
    )


@pytest.mark.unit
class TestModelLearnedPatternValidConstruction:
    """Tests for valid ModelLearnedPattern construction."""

    def test_construct_with_all_required_fields(self) -> None:
        """Should construct with all required fields."""
        model = _create_valid_learned_pattern()
        assert model.pattern_id == TEST_PATTERN_UUID
        assert model.pattern_name == "Error Handling Pattern"
        assert model.pattern_type == "code_pattern"
        assert model.category == "error_handling"
        assert model.subcategory == "exception_flow"
        assert model.tags == ("python", "error", "exception")
        assert model.keywords == ("try", "except", "finally")
        assert model.lifecycle_state == EnumPatternLifecycleState.VALIDATED
        assert model.source_count == 5

    def test_nested_score_components(self) -> None:
        """Should correctly nest ModelPatternScoreComponents."""
        model = _create_valid_learned_pattern()
        assert isinstance(model.score_components, ModelPatternScoreComponents)
        assert model.score_components.label_agreement == 0.85
        assert model.score_components.confidence == 0.76

    def test_nested_signature_info(self) -> None:
        """Should correctly nest ModelPatternSignature."""
        model = _create_valid_learned_pattern()
        assert isinstance(model.signature_info, ModelPatternSignature)
        assert model.signature_info.signature_version == ModelSemVer(
            major=1, minor=0, patch=0
        )
        assert "category" in model.signature_info.signature_inputs

    def test_all_lifecycle_states(self) -> None:
        """Should accept all lifecycle states."""
        for state in EnumPatternLifecycleState:
            model = ModelLearnedPattern(
                pattern_id=uuid4(),
                pattern_name="Test Pattern",
                pattern_type="test_type",
                category="test",
                subcategory="test_sub",
                tags=(),
                keywords=(),
                score_components=_create_valid_score_components(),
                signature_info=_create_valid_signature(),
                lifecycle_state=state,
                source_count=1,
                first_seen=datetime.now(UTC),
                last_seen=datetime.now(UTC),
            )
            assert model.lifecycle_state == state


@pytest.mark.unit
class TestModelLearnedPatternConstraintValidation:
    """Tests for constraint validation in ModelLearnedPattern."""

    def test_rejects_source_count_zero(self) -> None:
        """Should reject source_count of 0 (must be >= 1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLearnedPattern(
                pattern_id=uuid4(),
                pattern_name="Test Pattern",
                pattern_type="test_type",
                category="test",
                subcategory="test_sub",
                tags=(),
                keywords=(),
                score_components=_create_valid_score_components(),
                signature_info=_create_valid_signature(),
                lifecycle_state=EnumPatternLifecycleState.CANDIDATE,
                source_count=0,
                first_seen=datetime.now(UTC),
                last_seen=datetime.now(UTC),
            )
        assert "source_count" in str(exc_info.value)

    def test_rejects_negative_source_count(self) -> None:
        """Should reject negative source_count."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLearnedPattern(
                pattern_id=uuid4(),
                pattern_name="Test Pattern",
                pattern_type="test_type",
                category="test",
                subcategory="test_sub",
                tags=(),
                keywords=(),
                score_components=_create_valid_score_components(),
                signature_info=_create_valid_signature(),
                lifecycle_state=EnumPatternLifecycleState.CANDIDATE,
                source_count=-1,
                first_seen=datetime.now(UTC),
                last_seen=datetime.now(UTC),
            )
        assert "source_count" in str(exc_info.value)

    def test_accepts_source_count_one(self) -> None:
        """Should accept source_count of 1 (minimum valid)."""
        model = ModelLearnedPattern(
            pattern_id=uuid4(),
            pattern_name="Test Pattern",
            pattern_type="test_type",
            category="test",
            subcategory="test_sub",
            tags=(),
            keywords=(),
            score_components=_create_valid_score_components(),
            signature_info=_create_valid_signature(),
            lifecycle_state=EnumPatternLifecycleState.CANDIDATE,
            source_count=1,
            first_seen=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )
        assert model.source_count == 1


@pytest.mark.unit
class TestModelLearnedPatternTupleFields:
    """Tests for tuple fields in ModelLearnedPattern."""

    def test_tags_is_tuple(self) -> None:
        """tags field should be a tuple."""
        model = _create_valid_learned_pattern()
        assert isinstance(model.tags, tuple)

    def test_keywords_is_tuple(self) -> None:
        """keywords field should be a tuple."""
        model = _create_valid_learned_pattern()
        assert isinstance(model.keywords, tuple)

    def test_accepts_empty_tags(self) -> None:
        """Should accept empty tuple for tags."""
        model = ModelLearnedPattern(
            pattern_id=uuid4(),
            pattern_name="Test Pattern",
            pattern_type="test_type",
            category="test",
            subcategory="test_sub",
            tags=(),
            keywords=("keyword1",),
            score_components=_create_valid_score_components(),
            signature_info=_create_valid_signature(),
            lifecycle_state=EnumPatternLifecycleState.CANDIDATE,
            source_count=1,
            first_seen=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )
        assert model.tags == ()

    def test_accepts_empty_keywords(self) -> None:
        """Should accept empty tuple for keywords."""
        model = ModelLearnedPattern(
            pattern_id=uuid4(),
            pattern_name="Test Pattern",
            pattern_type="test_type",
            category="test",
            subcategory="test_sub",
            tags=("tag1",),
            keywords=(),
            score_components=_create_valid_score_components(),
            signature_info=_create_valid_signature(),
            lifecycle_state=EnumPatternLifecycleState.CANDIDATE,
            source_count=1,
            first_seen=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )
        assert model.keywords == ()


@pytest.mark.unit
class TestModelLearnedPatternFrozen:
    """Tests for frozen (immutable) enforcement in ModelLearnedPattern."""

    def test_frozen_rejects_mutation_pattern_id(self) -> None:
        """Frozen model should reject pattern_id assignment."""
        model = _create_valid_learned_pattern()
        with pytest.raises(ValidationError) as exc_info:
            model.pattern_id = uuid4()
        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_rejects_mutation_lifecycle_state(self) -> None:
        """Frozen model should reject lifecycle_state assignment."""
        model = _create_valid_learned_pattern()
        with pytest.raises(ValidationError) as exc_info:
            model.lifecycle_state = EnumPatternLifecycleState.DEPRECATED
        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_rejects_mutation_source_count(self) -> None:
        """Frozen model should reject source_count assignment."""
        model = _create_valid_learned_pattern()
        with pytest.raises(ValidationError) as exc_info:
            model.source_count = 10
        assert "frozen" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelLearnedPatternExtraFields:
    """Tests for extra field rejection in ModelLearnedPattern."""

    def test_rejects_extra_fields(self) -> None:
        """Should reject extra fields not in the model."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLearnedPattern(
                pattern_id=uuid4(),
                pattern_name="Test Pattern",
                pattern_type="test_type",
                category="test",
                subcategory="test_sub",
                tags=(),
                keywords=(),
                score_components=_create_valid_score_components(),
                signature_info=_create_valid_signature(),
                lifecycle_state=EnumPatternLifecycleState.CANDIDATE,
                source_count=1,
                first_seen=datetime.now(UTC),
                last_seen=datetime.now(UTC),
                extra_field="invalid",  # type: ignore[call-arg]
            )
        assert "extra_field" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelLearnedPatternSerialization:
    """Tests for serialization of ModelLearnedPattern."""

    def test_model_dump(self) -> None:
        """model_dump() should return correct dict with nested models."""
        model = _create_valid_learned_pattern()
        data = model.model_dump()

        assert data["pattern_id"] == TEST_PATTERN_UUID
        assert data["pattern_name"] == "Error Handling Pattern"
        assert data["lifecycle_state"] == EnumPatternLifecycleState.VALIDATED

        # Check nested models are serialized
        assert isinstance(data["score_components"], dict)
        assert data["score_components"]["label_agreement"] == 0.85

        assert isinstance(data["signature_info"], dict)
        expected_version = ModelSemVer(major=1, minor=0, patch=0).model_dump()
        assert data["signature_info"]["signature_version"] == expected_version

    def test_model_validate_round_trip(self) -> None:
        """model_validate() should correctly reconstruct from dict."""
        original = _create_valid_learned_pattern()
        data = original.model_dump()
        reconstructed = ModelLearnedPattern.model_validate(data)

        assert reconstructed.pattern_id == original.pattern_id
        assert reconstructed.pattern_name == original.pattern_name
        assert reconstructed.lifecycle_state == original.lifecycle_state
        assert reconstructed.score_components == original.score_components
        assert reconstructed.signature_info == original.signature_info

    def test_model_dump_json_serializable(self) -> None:
        """model_dump(mode='json') should be JSON-serializable."""
        import json

        model = _create_valid_learned_pattern()
        data = model.model_dump(mode="json")

        # Should not raise
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

        # Should round-trip via JSON
        parsed = json.loads(json_str)
        reconstructed = ModelLearnedPattern.model_validate(parsed)
        assert reconstructed.pattern_id == model.pattern_id


@pytest.mark.unit
class TestModelLearnedPatternDatetimeHandling:
    """Tests for datetime handling in ModelLearnedPattern."""

    def test_accepts_utc_datetimes(self) -> None:
        """Should accept UTC datetimes for first_seen and last_seen."""
        first = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        last = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        model = ModelLearnedPattern(
            pattern_id=uuid4(),
            pattern_name="Test Pattern",
            pattern_type="test_type",
            category="test",
            subcategory="test_sub",
            tags=(),
            keywords=(),
            score_components=_create_valid_score_components(),
            signature_info=_create_valid_signature(),
            lifecycle_state=EnumPatternLifecycleState.CANDIDATE,
            source_count=1,
            first_seen=first,
            last_seen=last,
        )
        assert model.first_seen == first
        assert model.last_seen == last

    def test_accepts_naive_datetimes(self) -> None:
        """Should accept naive datetimes (no timezone)."""
        first = datetime(2024, 1, 1, 0, 0, 0)
        last = datetime(2024, 1, 15, 12, 0, 0)

        model = ModelLearnedPattern(
            pattern_id=uuid4(),
            pattern_name="Test Pattern",
            pattern_type="test_type",
            category="test",
            subcategory="test_sub",
            tags=(),
            keywords=(),
            score_components=_create_valid_score_components(),
            signature_info=_create_valid_signature(),
            lifecycle_state=EnumPatternLifecycleState.CANDIDATE,
            source_count=1,
            first_seen=first,
            last_seen=last,
        )
        assert model.first_seen == first
        assert model.last_seen == last
