# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for injection metrics payload models.

This module tests the injection metrics event payloads used to measure
and improve manifest/context injection quality. These payloads are
emitted by omniclaude and consumed by omnibase_infra.

Test Coverage:
    - Basic instantiation with required fields
    - Field validation (bounds, literals, constraints)
    - Extra fields forbidden
    - Model immutability (frozen=True)
    - Serialization round-trip

Created: 2026-02-04
PR Coverage: OMN-1901 Injection Metrics Event Contracts
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.events.model_agent_match_payload import (
    ModelAgentMatchPayload,
)
from omnibase_core.models.events.model_context_utilization_payload import (
    ModelContextUtilizationPayload,
)
from omnibase_core.models.events.model_latency_breakdown_payload import (
    ModelLatencyBreakdownPayload,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_timestamp() -> datetime:
    """Create a sample timezone-aware timestamp."""
    return datetime.now(UTC)


@pytest.fixture
def sample_context_utilization_payload(
    sample_timestamp: datetime,
) -> ModelContextUtilizationPayload:
    """Create a sample context utilization payload for testing."""
    return ModelContextUtilizationPayload(
        session_ref="sess-abc-123",
        utilization_score=0.75,
        utilization_method="identifier_match",
        injected_count=10,
        reused_count=7,
        timestamp=sample_timestamp,
    )


@pytest.fixture
def sample_agent_match_payload(sample_timestamp: datetime) -> ModelAgentMatchPayload:
    """Create a sample agent match payload for testing."""
    return ModelAgentMatchPayload(
        session_ref="sess-abc-123",
        requested_agent=None,
        routed_agent="code-reviewer",
        match_score=0.95,
        routing_path="direct",
        timestamp=sample_timestamp,
    )


@pytest.fixture
def sample_latency_breakdown_payload(
    sample_timestamp: datetime,
) -> ModelLatencyBreakdownPayload:
    """Create a sample latency breakdown payload for testing."""
    return ModelLatencyBreakdownPayload(
        session_ref="sess-abc-123",
        prompt_index=0,
        routing_ms=15,
        retrieval_ms=45,
        injection_ms=10,
        user_visible_latency_ms=120,
        cohort="control",
        cache_hit=True,
        timestamp=sample_timestamp,
    )


# ============================================================================
# Tests for ModelContextUtilizationPayload
# ============================================================================


@pytest.mark.unit
class TestModelContextUtilizationPayloadBasic:
    """Test ModelContextUtilizationPayload basic creation and validation."""

    def test_creation_all_required_fields(self, sample_timestamp: datetime) -> None:
        """Test creating payload with all required fields."""
        payload = ModelContextUtilizationPayload(
            session_ref="sess-123",
            utilization_score=0.8,
            utilization_method="semantic",
            injected_count=5,
            reused_count=4,
            timestamp=sample_timestamp,
        )

        assert payload.session_ref == "sess-123"
        assert payload.utilization_score == 0.8
        assert payload.utilization_method == "semantic"
        assert payload.injected_count == 5
        assert payload.reused_count == 4
        assert payload.timestamp == sample_timestamp

    def test_missing_required_fields_raises(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContextUtilizationPayload()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        required_fields = {
            "session_ref",
            "utilization_score",
            "utilization_method",
            "injected_count",
            "reused_count",
            "timestamp",
        }
        error_locs = {str(e["loc"][0]) for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(error_locs)

    def test_extra_fields_forbidden(self, sample_timestamp: datetime) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelContextUtilizationPayload(
                session_ref="sess-123",
                utilization_score=0.8,
                utilization_method="semantic",
                injected_count=5,
                reused_count=4,
                timestamp=sample_timestamp,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelContextUtilizationPayloadValidation:
    """Test ModelContextUtilizationPayload field validation."""

    def test_utilization_score_valid_range(self, sample_timestamp: datetime) -> None:
        """Test that utilization_score accepts valid values (0.0 to 1.0)."""
        # Minimum value
        payload = ModelContextUtilizationPayload(
            session_ref="sess-123",
            utilization_score=0.0,
            utilization_method="heuristic",
            injected_count=5,
            reused_count=0,
            timestamp=sample_timestamp,
        )
        assert payload.utilization_score == 0.0

        # Maximum value
        payload = ModelContextUtilizationPayload(
            session_ref="sess-123",
            utilization_score=1.0,
            utilization_method="heuristic",
            injected_count=5,
            reused_count=5,
            timestamp=sample_timestamp,
        )
        assert payload.utilization_score == 1.0

    def test_utilization_score_below_minimum_rejected(
        self, sample_timestamp: datetime
    ) -> None:
        """Test that utilization_score below 0.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContextUtilizationPayload(
                session_ref="sess-123",
                utilization_score=-0.1,
                utilization_method="semantic",
                injected_count=5,
                reused_count=4,
                timestamp=sample_timestamp,
            )
        assert any(
            "utilization_score" in str(e.get("loc", []))
            for e in exc_info.value.errors()
        )

    def test_utilization_score_above_maximum_rejected(
        self, sample_timestamp: datetime
    ) -> None:
        """Test that utilization_score above 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContextUtilizationPayload(
                session_ref="sess-123",
                utilization_score=1.1,
                utilization_method="semantic",
                injected_count=5,
                reused_count=4,
                timestamp=sample_timestamp,
            )
        assert any(
            "utilization_score" in str(e.get("loc", []))
            for e in exc_info.value.errors()
        )

    def test_utilization_method_valid_literals(
        self, sample_timestamp: datetime
    ) -> None:
        """Test that utilization_method accepts valid literal values."""
        for method in ("identifier_match", "semantic", "heuristic"):
            payload = ModelContextUtilizationPayload(
                session_ref="sess-123",
                utilization_score=0.5,
                utilization_method=method,  # type: ignore[arg-type]
                injected_count=5,
                reused_count=3,
                timestamp=sample_timestamp,
            )
            assert payload.utilization_method == method

    def test_utilization_method_invalid_rejected(
        self, sample_timestamp: datetime
    ) -> None:
        """Test that invalid utilization_method is rejected."""
        with pytest.raises(ValidationError):
            ModelContextUtilizationPayload(
                session_ref="sess-123",
                utilization_score=0.5,
                utilization_method="invalid_method",  # type: ignore[arg-type]
                injected_count=5,
                reused_count=3,
                timestamp=sample_timestamp,
            )

    def test_counts_must_be_non_negative(self, sample_timestamp: datetime) -> None:
        """Test that injected_count and reused_count must be >= 0."""
        with pytest.raises(ValidationError):
            ModelContextUtilizationPayload(
                session_ref="sess-123",
                utilization_score=0.5,
                utilization_method="semantic",
                injected_count=-1,
                reused_count=0,
                timestamp=sample_timestamp,
            )

        with pytest.raises(ValidationError):
            ModelContextUtilizationPayload(
                session_ref="sess-123",
                utilization_score=0.5,
                utilization_method="semantic",
                injected_count=5,
                reused_count=-1,
                timestamp=sample_timestamp,
            )

    def test_session_ref_cannot_be_empty(self, sample_timestamp: datetime) -> None:
        """Test that session_ref cannot be empty string."""
        with pytest.raises(ValidationError):
            ModelContextUtilizationPayload(
                session_ref="",
                utilization_score=0.5,
                utilization_method="semantic",
                injected_count=5,
                reused_count=3,
                timestamp=sample_timestamp,
            )


# ============================================================================
# Tests for ModelAgentMatchPayload
# ============================================================================


@pytest.mark.unit
class TestModelAgentMatchPayloadBasic:
    """Test ModelAgentMatchPayload basic creation and validation."""

    def test_creation_all_fields(self, sample_timestamp: datetime) -> None:
        """Test creating payload with all fields specified."""
        payload = ModelAgentMatchPayload(
            session_ref="sess-123",
            requested_agent="my-agent",
            routed_agent="code-reviewer",
            match_score=0.9,
            routing_path="direct",
            timestamp=sample_timestamp,
        )

        assert payload.session_ref == "sess-123"
        assert payload.requested_agent == "my-agent"
        assert payload.routed_agent == "code-reviewer"
        assert payload.match_score == 0.9
        assert payload.routing_path == "direct"

    def test_requested_agent_optional(self, sample_timestamp: datetime) -> None:
        """Test that requested_agent can be None (auto-routed)."""
        payload = ModelAgentMatchPayload(
            session_ref="sess-123",
            requested_agent=None,
            routed_agent="auto-selected",
            match_score=0.85,
            routing_path="fallback",
            timestamp=sample_timestamp,
        )

        assert payload.requested_agent is None

    def test_extra_fields_forbidden(self, sample_timestamp: datetime) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelAgentMatchPayload(
                session_ref="sess-123",
                routed_agent="agent",
                match_score=0.9,
                routing_path="direct",
                timestamp=sample_timestamp,
                extra_field="bad",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelAgentMatchPayloadValidation:
    """Test ModelAgentMatchPayload field validation."""

    def test_match_score_valid_range(self, sample_timestamp: datetime) -> None:
        """Test that match_score accepts valid values (0.0 to 1.0)."""
        for score in (0.0, 0.5, 1.0):
            payload = ModelAgentMatchPayload(
                session_ref="sess-123",
                routed_agent="agent",
                match_score=score,
                routing_path="direct",
                timestamp=sample_timestamp,
            )
            assert payload.match_score == score

    def test_match_score_out_of_range_rejected(
        self, sample_timestamp: datetime
    ) -> None:
        """Test that match_score outside 0.0-1.0 is rejected."""
        with pytest.raises(ValidationError):
            ModelAgentMatchPayload(
                session_ref="sess-123",
                routed_agent="agent",
                match_score=-0.1,
                routing_path="direct",
                timestamp=sample_timestamp,
            )

        with pytest.raises(ValidationError):
            ModelAgentMatchPayload(
                session_ref="sess-123",
                routed_agent="agent",
                match_score=1.1,
                routing_path="direct",
                timestamp=sample_timestamp,
            )

    def test_routing_path_valid_literals(self, sample_timestamp: datetime) -> None:
        """Test that routing_path accepts valid literal values."""
        for path in ("direct", "fallback", "override"):
            payload = ModelAgentMatchPayload(
                session_ref="sess-123",
                routed_agent="agent",
                match_score=0.9,
                routing_path=path,  # type: ignore[arg-type]
                timestamp=sample_timestamp,
            )
            assert payload.routing_path == path

    def test_routing_path_invalid_rejected(self, sample_timestamp: datetime) -> None:
        """Test that invalid routing_path is rejected."""
        with pytest.raises(ValidationError):
            ModelAgentMatchPayload(
                session_ref="sess-123",
                routed_agent="agent",
                match_score=0.9,
                routing_path="invalid_path",  # type: ignore[arg-type]
                timestamp=sample_timestamp,
            )

    def test_routed_agent_cannot_be_empty(self, sample_timestamp: datetime) -> None:
        """Test that routed_agent cannot be empty string."""
        with pytest.raises(ValidationError):
            ModelAgentMatchPayload(
                session_ref="sess-123",
                routed_agent="",
                match_score=0.9,
                routing_path="direct",
                timestamp=sample_timestamp,
            )


# ============================================================================
# Tests for ModelLatencyBreakdownPayload
# ============================================================================


@pytest.mark.unit
class TestModelLatencyBreakdownPayloadBasic:
    """Test ModelLatencyBreakdownPayload basic creation and validation."""

    def test_creation_all_fields(self, sample_timestamp: datetime) -> None:
        """Test creating payload with all fields specified."""
        payload = ModelLatencyBreakdownPayload(
            session_ref="sess-123",
            prompt_index=2,
            routing_ms=10,
            retrieval_ms=50,
            injection_ms=5,
            user_visible_latency_ms=100,
            cohort="treatment-a",
            cache_hit=False,
            timestamp=sample_timestamp,
        )

        assert payload.session_ref == "sess-123"
        assert payload.prompt_index == 2
        assert payload.routing_ms == 10
        assert payload.retrieval_ms == 50
        assert payload.injection_ms == 5
        assert payload.user_visible_latency_ms == 100
        assert payload.cohort == "treatment-a"
        assert payload.cache_hit is False

    def test_extra_fields_forbidden(self, sample_timestamp: datetime) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelLatencyBreakdownPayload(
                session_ref="sess-123",
                prompt_index=0,
                routing_ms=10,
                retrieval_ms=50,
                injection_ms=5,
                user_visible_latency_ms=100,
                cohort="control",
                cache_hit=True,
                timestamp=sample_timestamp,
                extra_field="bad",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelLatencyBreakdownPayloadValidation:
    """Test ModelLatencyBreakdownPayload field validation."""

    def test_prompt_index_must_be_non_negative(
        self, sample_timestamp: datetime
    ) -> None:
        """Test that prompt_index must be >= 0."""
        # Valid: 0
        payload = ModelLatencyBreakdownPayload(
            session_ref="sess-123",
            prompt_index=0,
            routing_ms=10,
            retrieval_ms=50,
            injection_ms=5,
            user_visible_latency_ms=100,
            cohort="control",
            cache_hit=True,
            timestamp=sample_timestamp,
        )
        assert payload.prompt_index == 0

        # Invalid: negative
        with pytest.raises(ValidationError):
            ModelLatencyBreakdownPayload(
                session_ref="sess-123",
                prompt_index=-1,
                routing_ms=10,
                retrieval_ms=50,
                injection_ms=5,
                user_visible_latency_ms=100,
                cohort="control",
                cache_hit=True,
                timestamp=sample_timestamp,
            )

    def test_latency_fields_must_be_non_negative(
        self, sample_timestamp: datetime
    ) -> None:
        """Test that all millisecond fields must be >= 0."""
        base_kwargs = {
            "session_ref": "sess-123",
            "prompt_index": 0,
            "routing_ms": 10,
            "retrieval_ms": 50,
            "injection_ms": 5,
            "user_visible_latency_ms": 100,
            "cohort": "control",
            "cache_hit": True,
            "timestamp": sample_timestamp,
        }

        for field in (
            "routing_ms",
            "retrieval_ms",
            "injection_ms",
            "user_visible_latency_ms",
        ):
            kwargs = {**base_kwargs, field: -1}
            with pytest.raises(ValidationError):
                ModelLatencyBreakdownPayload(**kwargs)  # type: ignore[arg-type]

    def test_cohort_cannot_be_empty(self, sample_timestamp: datetime) -> None:
        """Test that cohort cannot be empty string."""
        with pytest.raises(ValidationError):
            ModelLatencyBreakdownPayload(
                session_ref="sess-123",
                prompt_index=0,
                routing_ms=10,
                retrieval_ms=50,
                injection_ms=5,
                user_visible_latency_ms=100,
                cohort="",
                cache_hit=True,
                timestamp=sample_timestamp,
            )


# ============================================================================
# Tests for Timestamp Timezone Awareness
# ============================================================================


@pytest.mark.unit
class TestTimestampTimezoneAwareness:
    """Test that all injection metrics models reject naive datetimes."""

    def test_context_utilization_rejects_naive_datetime(self) -> None:
        """Test that ModelContextUtilizationPayload rejects naive datetime."""
        from datetime import datetime as dt

        naive_timestamp = dt.now()  # No timezone info

        with pytest.raises(ValidationError) as exc_info:
            ModelContextUtilizationPayload(
                session_ref="sess-123",
                utilization_score=0.5,
                utilization_method="semantic",
                injected_count=5,
                reused_count=3,
                timestamp=naive_timestamp,
            )

        # Verify the error is about timezone awareness
        errors = exc_info.value.errors()
        assert any("timezone-aware" in str(e.get("msg", "")) for e in errors)

    def test_agent_match_rejects_naive_datetime(self) -> None:
        """Test that ModelAgentMatchPayload rejects naive datetime."""
        from datetime import datetime as dt

        naive_timestamp = dt.now()  # No timezone info

        with pytest.raises(ValidationError) as exc_info:
            ModelAgentMatchPayload(
                session_ref="sess-123",
                routed_agent="agent",
                match_score=0.9,
                routing_path="direct",
                timestamp=naive_timestamp,
            )

        errors = exc_info.value.errors()
        assert any("timezone-aware" in str(e.get("msg", "")) for e in errors)

    def test_latency_breakdown_rejects_naive_datetime(self) -> None:
        """Test that ModelLatencyBreakdownPayload rejects naive datetime."""
        from datetime import datetime as dt

        naive_timestamp = dt.now()  # No timezone info

        with pytest.raises(ValidationError) as exc_info:
            ModelLatencyBreakdownPayload(
                session_ref="sess-123",
                prompt_index=0,
                routing_ms=10,
                retrieval_ms=50,
                injection_ms=5,
                user_visible_latency_ms=100,
                cohort="control",
                cache_hit=True,
                timestamp=naive_timestamp,
            )

        errors = exc_info.value.errors()
        assert any("timezone-aware" in str(e.get("msg", "")) for e in errors)


# ============================================================================
# Tests for Model Immutability (All Models)
# ============================================================================


@pytest.mark.unit
class TestInjectionMetricsImmutability:
    """Test that all injection metrics models are frozen (immutable)."""

    def test_context_utilization_is_frozen(
        self, sample_context_utilization_payload: ModelContextUtilizationPayload
    ) -> None:
        """Verify ModelContextUtilizationPayload is immutable."""
        with pytest.raises(ValidationError):
            sample_context_utilization_payload.session_ref = "new-id"  # type: ignore[misc]

    def test_agent_match_is_frozen(
        self, sample_agent_match_payload: ModelAgentMatchPayload
    ) -> None:
        """Verify ModelAgentMatchPayload is immutable."""
        with pytest.raises(ValidationError):
            sample_agent_match_payload.routed_agent = "new-agent"  # type: ignore[misc]

    def test_latency_breakdown_is_frozen(
        self, sample_latency_breakdown_payload: ModelLatencyBreakdownPayload
    ) -> None:
        """Verify ModelLatencyBreakdownPayload is immutable."""
        with pytest.raises(ValidationError):
            sample_latency_breakdown_payload.routing_ms = 999  # type: ignore[misc]


# ============================================================================
# Tests for Serialization (All Models)
# ============================================================================


@pytest.mark.unit
class TestInjectionMetricsSerialization:
    """Test serialization for all injection metrics models."""

    def test_context_utilization_roundtrip(
        self, sample_context_utilization_payload: ModelContextUtilizationPayload
    ) -> None:
        """Test ModelContextUtilizationPayload serialization round-trip."""
        data = sample_context_utilization_payload.model_dump()
        restored = ModelContextUtilizationPayload.model_validate(data)

        assert restored.session_ref == sample_context_utilization_payload.session_ref
        assert (
            restored.utilization_score
            == sample_context_utilization_payload.utilization_score
        )
        assert (
            restored.utilization_method
            == sample_context_utilization_payload.utilization_method
        )

    def test_agent_match_roundtrip(
        self, sample_agent_match_payload: ModelAgentMatchPayload
    ) -> None:
        """Test ModelAgentMatchPayload serialization round-trip."""
        data = sample_agent_match_payload.model_dump()
        restored = ModelAgentMatchPayload.model_validate(data)

        assert restored.session_ref == sample_agent_match_payload.session_ref
        assert restored.routed_agent == sample_agent_match_payload.routed_agent
        assert restored.match_score == sample_agent_match_payload.match_score

    def test_latency_breakdown_roundtrip(
        self, sample_latency_breakdown_payload: ModelLatencyBreakdownPayload
    ) -> None:
        """Test ModelLatencyBreakdownPayload serialization round-trip."""
        data = sample_latency_breakdown_payload.model_dump()
        restored = ModelLatencyBreakdownPayload.model_validate(data)

        assert restored.session_ref == sample_latency_breakdown_payload.session_ref
        assert restored.routing_ms == sample_latency_breakdown_payload.routing_ms
        assert restored.cache_hit == sample_latency_breakdown_payload.cache_hit

    def test_all_models_json_serializable(
        self,
        sample_context_utilization_payload: ModelContextUtilizationPayload,
        sample_agent_match_payload: ModelAgentMatchPayload,
        sample_latency_breakdown_payload: ModelLatencyBreakdownPayload,
    ) -> None:
        """Test that all models can be serialized to JSON."""
        for payload in (
            sample_context_utilization_payload,
            sample_agent_match_payload,
            sample_latency_breakdown_payload,
        ):
            json_str = payload.model_dump_json()
            assert isinstance(json_str, str)
            assert "sess-abc-123" in json_str


# ============================================================================
# Tests for Topic Constants
# ============================================================================


@pytest.mark.unit
class TestInjectionMetricsTopics:
    """Test injection metrics topic constants."""

    def test_topic_constants_defined(self) -> None:
        """Verify topic constants are defined and follow naming convention."""
        from omnibase_core.constants import (
            INJECTION_METRICS_TOPICS,
            TOPIC_INJECTION_AGENT_MATCH,
            TOPIC_INJECTION_CONTEXT_UTILIZATION,
            TOPIC_INJECTION_LATENCY_BREAKDOWN,
        )

        assert (
            TOPIC_INJECTION_CONTEXT_UTILIZATION
            == "onex.evt.injection-metrics.context-utilization.v1"
        )
        assert (
            TOPIC_INJECTION_AGENT_MATCH == "onex.evt.injection-metrics.agent-match.v1"
        )
        assert (
            TOPIC_INJECTION_LATENCY_BREAKDOWN
            == "onex.evt.injection-metrics.latency-breakdown.v1"
        )

        assert len(INJECTION_METRICS_TOPICS) == 3
        assert TOPIC_INJECTION_CONTEXT_UTILIZATION in INJECTION_METRICS_TOPICS
        assert TOPIC_INJECTION_AGENT_MATCH in INJECTION_METRICS_TOPICS
        assert TOPIC_INJECTION_LATENCY_BREAKDOWN in INJECTION_METRICS_TOPICS

    def test_topics_follow_naming_convention(self) -> None:
        """Verify topics follow onex.evt.<domain>.<event-type>.v1 pattern."""
        from omnibase_core.constants import INJECTION_METRICS_TOPICS

        for topic in INJECTION_METRICS_TOPICS:
            parts = topic.split(".")
            assert len(parts) == 5
            assert parts[0] == "onex"
            assert parts[1] == "evt"
            assert parts[2] == "injection-metrics"
            assert parts[4] == "v1"
