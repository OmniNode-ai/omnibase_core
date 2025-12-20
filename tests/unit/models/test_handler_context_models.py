"""Tests for handler context models with time injection.

These tests verify the type-level enforcement that:
- Orchestrator and Effect contexts have `now` for time-dependent operations
- Reducer and Compute contexts do NOT have `now` (pure function requirement)

This ensures:
1. Deterministic testing via time injection for orchestrators and effects
2. Replay safety for reducers and compute nodes by preventing wall-clock time access
3. Consistent base fields (correlation_id, envelope_id) across all contexts
4. Thread safety via frozen models

See Also:
    - OMN-948: Time injection context models for handlers
    - docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md
"""

import importlib.util
import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError


def _import_module_directly(module_path: Path, module_name: str) -> types.ModuleType:
    """Import a module directly from its file path, bypassing package __init__.py.

    This is necessary to avoid circular import issues in the effect package.
    """
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Get the source directory
_src_dir = Path(__file__).parent.parent.parent.parent / "src"

# Import context models directly to avoid circular imports in effect package
_effect_context_module = _import_module_directly(
    _src_dir / "omnibase_core" / "models" / "effect" / "model_effect_context.py",
    "omnibase_core.models.effect.model_effect_context",
)
ModelEffectContext: Any = _effect_context_module.ModelEffectContext

_orchestrator_context_module = _import_module_directly(
    _src_dir
    / "omnibase_core"
    / "models"
    / "orchestrator"
    / "model_orchestrator_context.py",
    "omnibase_core.models.orchestrator.model_orchestrator_context",
)
ModelOrchestratorContext: Any = _orchestrator_context_module.ModelOrchestratorContext

_reducer_context_module = _import_module_directly(
    _src_dir / "omnibase_core" / "models" / "reducer" / "model_reducer_context.py",
    "omnibase_core.models.reducer.model_reducer_context",
)
ModelReducerContext: Any = _reducer_context_module.ModelReducerContext

_compute_context_module = _import_module_directly(
    _src_dir / "omnibase_core" / "models" / "compute" / "model_compute_context.py",
    "omnibase_core.models.compute.model_compute_context",
)
ModelComputeContext: Any = _compute_context_module.ModelComputeContext


@pytest.mark.unit
class TestModelOrchestratorContext:
    """Tests for orchestrator handler context."""

    def test_has_now_field(self) -> None:
        """Orchestrator context must have `now` field for deadline calculations."""
        ctx = ModelOrchestratorContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        assert hasattr(ctx, "now")
        assert isinstance(ctx.now, datetime)

    def test_now_defaults_to_utc(self) -> None:
        """The `now` field should default to UTC-aware datetime."""
        ctx = ModelOrchestratorContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        assert ctx.now.tzinfo is not None

    def test_now_can_be_injected(self) -> None:
        """Should accept injected time for deterministic testing."""
        fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        ctx = ModelOrchestratorContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            now=fixed_time,
        )
        assert ctx.now == fixed_time

    def test_is_frozen(self) -> None:
        """Context should be immutable after creation."""
        ctx = ModelOrchestratorContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        with pytest.raises(ValidationError):
            ctx.now = datetime.now(UTC)  # type: ignore[misc]

    def test_has_correlation_id(self) -> None:
        """Context must have correlation_id for request tracing."""
        corr_id = uuid4()
        ctx = ModelOrchestratorContext(
            correlation_id=corr_id,
            envelope_id=uuid4(),
        )
        assert ctx.correlation_id == corr_id

    def test_has_envelope_id(self) -> None:
        """Context must have envelope_id for causality tracking."""
        env_id = uuid4()
        ctx = ModelOrchestratorContext(
            correlation_id=uuid4(),
            envelope_id=env_id,
        )
        assert ctx.envelope_id == env_id

    def test_optional_trace_id(self) -> None:
        """Context should support optional trace_id for distributed tracing."""
        trace = uuid4()
        ctx = ModelOrchestratorContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            trace_id=trace,
        )
        assert ctx.trace_id == trace

    def test_optional_span_id(self) -> None:
        """Context should support optional span_id for distributed tracing."""
        span = uuid4()
        ctx = ModelOrchestratorContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            span_id=span,
        )
        assert ctx.span_id == span

    def test_extra_fields_forbidden(self) -> None:
        """Context should reject unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelOrchestratorContext(
                correlation_id=uuid4(),
                envelope_id=uuid4(),
                unknown_field="value",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelEffectContext:
    """Tests for effect handler context."""

    def test_has_now_field(self) -> None:
        """Effect context must have `now` field for retry/metrics calculations."""
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        assert hasattr(ctx, "now")
        assert isinstance(ctx.now, datetime)

    def test_now_defaults_to_utc(self) -> None:
        """The `now` field should default to UTC-aware datetime."""
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        assert ctx.now.tzinfo is not None

    def test_has_retry_attempt(self) -> None:
        """Effect context should include retry attempt for backoff logic."""
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            retry_attempt=3,
        )
        assert ctx.retry_attempt == 3

    def test_retry_attempt_defaults_to_zero(self) -> None:
        """Retry attempt should default to 0 (first attempt)."""
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        assert ctx.retry_attempt == 0

    def test_retry_attempt_must_be_non_negative(self) -> None:
        """Retry attempt cannot be negative."""
        with pytest.raises(ValidationError):
            ModelEffectContext(
                correlation_id=uuid4(),
                envelope_id=uuid4(),
                retry_attempt=-1,
            )

    def test_now_can_be_injected(self) -> None:
        """Should accept injected time for deterministic testing."""
        fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            now=fixed_time,
        )
        assert ctx.now == fixed_time

    def test_is_frozen(self) -> None:
        """Context should be immutable after creation."""
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        with pytest.raises(ValidationError):
            ctx.now = datetime.now(UTC)  # type: ignore[misc]

    def test_has_correlation_id(self) -> None:
        """Context must have correlation_id for request tracing."""
        corr_id = uuid4()
        ctx = ModelEffectContext(
            correlation_id=corr_id,
            envelope_id=uuid4(),
        )
        assert ctx.correlation_id == corr_id

    def test_has_envelope_id(self) -> None:
        """Context must have envelope_id for causality tracking."""
        env_id = uuid4()
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=env_id,
        )
        assert ctx.envelope_id == env_id

    def test_optional_trace_id(self) -> None:
        """Context should support optional trace_id for distributed tracing."""
        trace = uuid4()
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            trace_id=trace,
        )
        assert ctx.trace_id == trace

    def test_optional_span_id(self) -> None:
        """Context should support optional span_id for distributed tracing."""
        span = uuid4()
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            span_id=span,
        )
        assert ctx.span_id == span

    def test_extra_fields_forbidden(self) -> None:
        """Context should reject unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelEffectContext(
                correlation_id=uuid4(),
                envelope_id=uuid4(),
                unknown_field="value",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelReducerContext:
    """Tests for reducer handler context - must NOT have time injection."""

    def test_does_not_have_now_field(self) -> None:
        """CRITICAL: Reducer context must NOT have `now` field.

        Reducers must be pure functions with deterministic output.
        Accessing wall-clock time would break replay safety.
        """
        ctx = ModelReducerContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        assert not hasattr(ctx, "now"), "Reducer context must NOT have 'now' field"

    def test_now_not_in_model_fields(self) -> None:
        """Verify `now` is not in the model's field definitions."""
        assert "now" not in ModelReducerContext.model_fields, (
            "Reducer context must not define 'now' field"
        )

    def test_cannot_pass_now_to_constructor(self) -> None:
        """Should reject `now` argument (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelReducerContext(
                correlation_id=uuid4(),
                envelope_id=uuid4(),
                now=datetime.now(UTC),  # type: ignore[call-arg]
            )

    def test_has_partition_id_for_sharding(self) -> None:
        """Reducer context should support partition ID for sharded reducers."""
        partition = uuid4()
        ctx = ModelReducerContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            partition_id=partition,
        )
        assert ctx.partition_id == partition

    def test_partition_id_is_optional(self) -> None:
        """Partition ID should be optional, defaulting to None."""
        ctx = ModelReducerContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        assert ctx.partition_id is None

    def test_is_frozen(self) -> None:
        """Context should be immutable after creation."""
        ctx = ModelReducerContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        with pytest.raises(ValidationError):
            ctx.correlation_id = uuid4()  # type: ignore[misc]

    def test_has_correlation_id(self) -> None:
        """Context must have correlation_id for request tracing."""
        corr_id = uuid4()
        ctx = ModelReducerContext(
            correlation_id=corr_id,
            envelope_id=uuid4(),
        )
        assert ctx.correlation_id == corr_id

    def test_has_envelope_id(self) -> None:
        """Context must have envelope_id for causality tracking."""
        env_id = uuid4()
        ctx = ModelReducerContext(
            correlation_id=uuid4(),
            envelope_id=env_id,
        )
        assert ctx.envelope_id == env_id

    def test_optional_trace_id(self) -> None:
        """Context should support optional trace_id for distributed tracing."""
        trace = uuid4()
        ctx = ModelReducerContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            trace_id=trace,
        )
        assert ctx.trace_id == trace

    def test_optional_span_id(self) -> None:
        """Context should support optional span_id for distributed tracing."""
        span = uuid4()
        ctx = ModelReducerContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            span_id=span,
        )
        assert ctx.span_id == span

    def test_extra_fields_forbidden(self) -> None:
        """Context should reject unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelReducerContext(
                correlation_id=uuid4(),
                envelope_id=uuid4(),
                unknown_field="value",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelComputeContext:
    """Tests for compute handler context - must NOT have time injection."""

    def test_does_not_have_now_field(self) -> None:
        """CRITICAL: Compute context must NOT have `now` field.

        COMPUTE nodes must be pure functions with deterministic output.
        Accessing wall-clock time would break caching and reproducibility.
        """
        ctx = ModelComputeContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        assert not hasattr(ctx, "now"), "Compute context must NOT have 'now' field"

    def test_now_not_in_model_fields(self) -> None:
        """Verify `now` is not in the model's field definitions."""
        assert "now" not in ModelComputeContext.model_fields, (
            "Compute context must not define 'now' field"
        )

    def test_cannot_pass_now_to_constructor(self) -> None:
        """Should reject `now` argument (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelComputeContext(
                correlation_id=uuid4(),
                envelope_id=uuid4(),
                now=datetime.now(UTC),  # type: ignore[call-arg]
            )

    def test_has_computation_type(self) -> None:
        """Compute context should support computation_type for algorithm tracking."""
        ctx = ModelComputeContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            computation_type="transform_json_to_xml",
        )
        assert ctx.computation_type == "transform_json_to_xml"

    def test_computation_type_is_optional(self) -> None:
        """Computation type should be optional, defaulting to None."""
        ctx = ModelComputeContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        assert ctx.computation_type is None

    def test_is_frozen(self) -> None:
        """Context should be immutable after creation."""
        ctx = ModelComputeContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
        )
        with pytest.raises(ValidationError):
            ctx.correlation_id = uuid4()  # type: ignore[misc]

    def test_has_correlation_id(self) -> None:
        """Context must have correlation_id for request tracing."""
        corr_id = uuid4()
        ctx = ModelComputeContext(
            correlation_id=corr_id,
            envelope_id=uuid4(),
        )
        assert ctx.correlation_id == corr_id

    def test_has_envelope_id(self) -> None:
        """Context must have envelope_id for causality tracking."""
        env_id = uuid4()
        ctx = ModelComputeContext(
            correlation_id=uuid4(),
            envelope_id=env_id,
        )
        assert ctx.envelope_id == env_id

    def test_optional_trace_id(self) -> None:
        """Context should support optional trace_id for distributed tracing."""
        trace = uuid4()
        ctx = ModelComputeContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            trace_id=trace,
        )
        assert ctx.trace_id == trace

    def test_optional_span_id(self) -> None:
        """Context should support optional span_id for distributed tracing."""
        span = uuid4()
        ctx = ModelComputeContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            span_id=span,
        )
        assert ctx.span_id == span

    def test_extra_fields_forbidden(self) -> None:
        """Context should reject unknown fields (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelComputeContext(
                correlation_id=uuid4(),
                envelope_id=uuid4(),
                unknown_field="value",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestContextModelParity:
    """Tests ensuring all context models have consistent base fields."""

    def test_all_have_correlation_id(self) -> None:
        """All context models must have correlation_id for tracing."""
        for model_cls in [
            ModelOrchestratorContext,
            ModelEffectContext,
            ModelReducerContext,
            ModelComputeContext,
        ]:
            assert "correlation_id" in model_cls.model_fields, (
                f"{model_cls.__name__} must have correlation_id field"
            )

    def test_all_have_envelope_id(self) -> None:
        """All context models must have envelope_id for causality."""
        for model_cls in [
            ModelOrchestratorContext,
            ModelEffectContext,
            ModelReducerContext,
            ModelComputeContext,
        ]:
            assert "envelope_id" in model_cls.model_fields, (
                f"{model_cls.__name__} must have envelope_id field"
            )

    def test_all_have_optional_trace_id(self) -> None:
        """All context models must have optional trace_id for distributed tracing."""
        for model_cls in [
            ModelOrchestratorContext,
            ModelEffectContext,
            ModelReducerContext,
            ModelComputeContext,
        ]:
            assert "trace_id" in model_cls.model_fields, (
                f"{model_cls.__name__} must have trace_id field"
            )

    def test_all_have_optional_span_id(self) -> None:
        """All context models must have optional span_id for distributed tracing."""
        for model_cls in [
            ModelOrchestratorContext,
            ModelEffectContext,
            ModelReducerContext,
            ModelComputeContext,
        ]:
            assert "span_id" in model_cls.model_fields, (
                f"{model_cls.__name__} must have span_id field"
            )

    def test_all_are_frozen(self) -> None:
        """All context models must be frozen for thread safety."""
        for model_cls in [
            ModelOrchestratorContext,
            ModelEffectContext,
            ModelReducerContext,
            ModelComputeContext,
        ]:
            assert model_cls.model_config.get("frozen") is True, (
                f"{model_cls.__name__} must have frozen=True"
            )

    def test_all_forbid_extra(self) -> None:
        """All context models must forbid extra fields for type safety."""
        for model_cls in [
            ModelOrchestratorContext,
            ModelEffectContext,
            ModelReducerContext,
            ModelComputeContext,
        ]:
            assert model_cls.model_config.get("extra") == "forbid", (
                f"{model_cls.__name__} must have extra='forbid'"
            )

    def test_time_injection_only_on_allowed_contexts(self) -> None:
        """Only orchestrator and effect contexts should have `now`.

        This is the critical architectural constraint:
        - Orchestrators need `now` for deadline/timeout calculations
        - Effects need `now` for retry timing and metrics
        - Reducers must NOT have `now` to maintain purity and replay safety
        - Compute nodes must NOT have `now` to maintain caching and reproducibility
        """
        assert "now" in ModelOrchestratorContext.model_fields, (
            "Orchestrator context must have 'now' for deadline calculations"
        )
        assert "now" in ModelEffectContext.model_fields, (
            "Effect context must have 'now' for retry/metrics calculations"
        )
        assert "now" not in ModelReducerContext.model_fields, (
            "Reducer context must NOT have 'now' to maintain purity"
        )
        assert "now" not in ModelComputeContext.model_fields, (
            "Compute context must NOT have 'now' to maintain caching validity"
        )


@pytest.mark.unit
class TestTimeInjectionUseCases:
    """Tests demonstrating practical use cases for time injection."""

    def test_orchestrator_deadline_calculation(self) -> None:
        """Orchestrators can calculate deadlines using injected time."""
        from datetime import timedelta

        fixed_time = datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC)
        ctx = ModelOrchestratorContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            now=fixed_time,
        )

        # Calculate a 30-second deadline
        timeout_ms = 30000
        deadline = ctx.now + timedelta(milliseconds=timeout_ms)

        expected_deadline = datetime(2024, 6, 15, 10, 0, 30, tzinfo=UTC)
        assert deadline == expected_deadline

    def test_effect_backoff_calculation(self) -> None:
        """Effects can calculate exponential backoff using retry_attempt."""
        ctx = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            retry_attempt=3,  # Fourth attempt (0-indexed)
        )

        # Calculate exponential backoff: 1s * 2^attempt
        base_backoff_ms = 1000
        backoff_ms = base_backoff_ms * (2**ctx.retry_attempt)

        # 1000 * 2^3 = 8000ms = 8 seconds
        assert backoff_ms == 8000

    def test_deterministic_testing_with_fixed_time(self) -> None:
        """Time injection enables fully deterministic tests."""
        fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

        # Create multiple contexts with same fixed time
        ctx1 = ModelOrchestratorContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            now=fixed_time,
        )
        ctx2 = ModelEffectContext(
            correlation_id=uuid4(),
            envelope_id=uuid4(),
            now=fixed_time,
        )

        # Both contexts have identical time - deterministic behavior
        assert ctx1.now == ctx2.now == fixed_time

    def test_reducer_purity_enforcement(self) -> None:
        """Reducer contexts enforce purity by excluding time.

        If a reducer needs time information, it must be provided
        in the event/intent data, not injected as runtime context.
        This ensures the reducer's output is deterministic and
        can be safely replayed for event sourcing.
        """
        # This is a compile-time / construction-time check
        # Attempting to pass `now` will raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerContext(
                correlation_id=uuid4(),
                envelope_id=uuid4(),
                now=datetime.now(UTC),  # type: ignore[call-arg]
            )

        # Verify the error mentions the unexpected field
        error_message = str(exc_info.value)
        assert "now" in error_message.lower() or "extra" in error_message.lower()

    def test_compute_purity_enforcement(self) -> None:
        """Compute contexts enforce purity by excluding time.

        COMPUTE nodes must be pure functions that produce deterministic
        output based solely on their input data. Wall-clock time would
        break caching validity and reproducibility.

        If a computation needs time information, it must be passed as
        part of the input data, not injected as runtime context.
        """
        # This is a compile-time / construction-time check
        # Attempting to pass `now` will raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ModelComputeContext(
                correlation_id=uuid4(),
                envelope_id=uuid4(),
                now=datetime.now(UTC),  # type: ignore[call-arg]
            )

        # Verify the error mentions the unexpected field
        error_message = str(exc_info.value)
        assert "now" in error_message.lower() or "extra" in error_message.lower()
