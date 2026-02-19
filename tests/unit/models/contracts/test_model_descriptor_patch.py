# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelDescriptorPatch (behavior patch model)."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch
from omnibase_core.models.runtime.model_descriptor_circuit_breaker import (
    ModelDescriptorCircuitBreaker,
)
from omnibase_core.models.runtime.model_descriptor_retry_policy import (
    ModelDescriptorRetryPolicy,
)


@pytest.mark.unit
class TestModelDescriptorPatch:
    """Tests for ModelDescriptorPatch (behavior patch) model."""

    @pytest.mark.unit
    def test_empty_patch(self) -> None:
        """Test creating an empty patch (all fields None)."""
        patch = ModelDescriptorPatch()
        assert patch.purity is None
        assert patch.idempotent is None
        assert patch.timeout_ms is None
        assert patch.retry_policy is None
        assert patch.circuit_breaker is None
        assert patch.concurrency_policy is None
        assert patch.isolation_policy is None
        assert patch.observability_level is None

    @pytest.mark.unit
    def test_single_override(self) -> None:
        """Test patch with single override."""
        patch = ModelDescriptorPatch(timeout_ms=5000)
        assert patch.timeout_ms == 5000
        assert patch.purity is None

    @pytest.mark.unit
    def test_multiple_overrides(self) -> None:
        """Test patch with multiple overrides."""
        patch = ModelDescriptorPatch(
            purity="pure",
            idempotent=True,
            timeout_ms=10000,
            concurrency_policy="parallel_ok",
        )
        assert patch.purity == "pure"
        assert patch.idempotent is True
        assert patch.timeout_ms == 10000
        assert patch.concurrency_policy == "parallel_ok"

    @pytest.mark.unit
    def test_purity_values(self) -> None:
        """Test valid purity values."""
        for purity in ["pure", "side_effecting"]:
            patch = ModelDescriptorPatch(purity=purity)  # type: ignore[arg-type]
            assert patch.purity == purity

    @pytest.mark.unit
    def test_purity_invalid_value(self) -> None:
        """Test invalid purity value."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(purity="invalid")  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_concurrency_policy_values(self) -> None:
        """Test valid concurrency policy values."""
        for policy in ["parallel_ok", "serialized", "singleflight"]:
            patch = ModelDescriptorPatch(concurrency_policy=policy)  # type: ignore[arg-type]
            assert patch.concurrency_policy == policy

    @pytest.mark.unit
    def test_concurrency_policy_invalid(self) -> None:
        """Test invalid concurrency policy value."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(concurrency_policy="invalid")  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_isolation_policy_values(self) -> None:
        """Test valid isolation policy values."""
        for policy in ["none", "process", "container", "vm"]:
            patch = ModelDescriptorPatch(isolation_policy=policy)  # type: ignore[arg-type]
            assert patch.isolation_policy == policy

    @pytest.mark.unit
    def test_isolation_policy_invalid(self) -> None:
        """Test invalid isolation policy value."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(isolation_policy="invalid")  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_observability_level_values(self) -> None:
        """Test valid observability level values."""
        for level in ["minimal", "standard", "verbose"]:
            patch = ModelDescriptorPatch(observability_level=level)  # type: ignore[arg-type]
            assert patch.observability_level == level

    @pytest.mark.unit
    def test_observability_level_invalid(self) -> None:
        """Test invalid observability level value."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(observability_level="invalid")  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_timeout_ms_non_negative(self) -> None:
        """Test timeout_ms must be non-negative."""
        patch = ModelDescriptorPatch(timeout_ms=0)
        assert patch.timeout_ms == 0

        with pytest.raises(ValidationError):
            ModelDescriptorPatch(timeout_ms=-1)

    @pytest.mark.unit
    def test_retry_policy_nested(self) -> None:
        """Test nested retry policy."""
        patch = ModelDescriptorPatch(
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=True,
                max_retries=5,
            )
        )
        assert patch.retry_policy is not None
        assert patch.retry_policy.enabled is True
        assert patch.retry_policy.max_retries == 5

    @pytest.mark.unit
    def test_circuit_breaker_nested(self) -> None:
        """Test nested circuit breaker."""
        patch = ModelDescriptorPatch(
            circuit_breaker=ModelDescriptorCircuitBreaker(
                enabled=True,
                failure_threshold=10,
            )
        )
        assert patch.circuit_breaker is not None
        assert patch.circuit_breaker.enabled is True
        assert patch.circuit_breaker.failure_threshold == 10

    @pytest.mark.unit
    def test_has_overrides_empty(self) -> None:
        """Test has_overrides with empty patch."""
        patch = ModelDescriptorPatch()
        assert patch.has_overrides() is False

    @pytest.mark.unit
    def test_has_overrides_with_fields(self) -> None:
        """Test has_overrides with fields set."""
        patch = ModelDescriptorPatch(timeout_ms=5000)
        assert patch.has_overrides() is True

    @pytest.mark.unit
    def test_get_override_fields_empty(self) -> None:
        """Test get_override_fields with empty patch."""
        patch = ModelDescriptorPatch()
        assert patch.get_override_fields() == []

    @pytest.mark.unit
    def test_get_override_fields_with_fields(self) -> None:
        """Test get_override_fields with fields set."""
        patch = ModelDescriptorPatch(
            purity="pure",
            timeout_ms=5000,
        )
        fields = patch.get_override_fields()
        assert "purity" in fields
        assert "timeout_ms" in fields
        assert "idempotent" not in fields

    @pytest.mark.unit
    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

    @pytest.mark.unit
    def test_frozen_model(self) -> None:
        """Test that the model is immutable."""
        patch = ModelDescriptorPatch(timeout_ms=5000)
        with pytest.raises(ValidationError):
            patch.timeout_ms = 10000  # type: ignore[misc]

    @pytest.mark.unit
    def test_repr_empty(self) -> None:
        """Test string representation of empty patch."""
        patch = ModelDescriptorPatch()
        assert "empty" in repr(patch)

    @pytest.mark.unit
    def test_repr_with_overrides(self) -> None:
        """Test string representation with overrides."""
        patch = ModelDescriptorPatch(purity="pure", timeout_ms=5000)
        repr_str = repr(patch)
        assert "overrides" in repr_str
        assert "purity" in repr_str
        assert "timeout_ms" in repr_str

    @pytest.mark.unit
    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "purity": "pure",
            "idempotent": True,
            "timeout_ms": 5000,
            "concurrency_policy": "parallel_ok",
        }
        patch = ModelDescriptorPatch.model_validate(data)
        assert patch.purity == "pure"
        assert patch.idempotent is True
        assert patch.timeout_ms == 5000
        assert patch.concurrency_policy == "parallel_ok"

    @pytest.mark.unit
    def test_to_dict_excludes_none(self) -> None:
        """Test serialization excludes None values when using exclude_none."""
        patch = ModelDescriptorPatch(purity="pure", timeout_ms=5000)
        data = patch.model_dump(exclude_none=True)
        assert data == {"purity": "pure", "timeout_ms": 5000}

    @pytest.mark.unit
    def test_equality(self) -> None:
        """Test equality comparison."""
        patch1 = ModelDescriptorPatch(purity="pure")
        patch2 = ModelDescriptorPatch(purity="pure")
        patch3 = ModelDescriptorPatch(purity="side_effecting")
        assert patch1 == patch2
        assert patch1 != patch3

    @pytest.mark.unit
    def test_full_patch(self) -> None:
        """Test patch with all fields set."""
        patch = ModelDescriptorPatch(
            purity="pure",
            idempotent=True,
            timeout_ms=5000,
            retry_policy=ModelDescriptorRetryPolicy(enabled=True),
            circuit_breaker=ModelDescriptorCircuitBreaker(enabled=True),
            concurrency_policy="parallel_ok",
            isolation_policy="process",
            observability_level="verbose",
        )
        assert patch.has_overrides() is True
        assert len(patch.get_override_fields()) == 8


@pytest.mark.unit
class TestModelDescriptorPatchConflictValidation:
    """Tests for ModelDescriptorPatch (behavior patch) settings consistency validation."""

    # =========================================================================
    # timeout_ms=0 with retry_policy conflicts
    # =========================================================================

    @pytest.mark.unit
    def test_timeout_zero_with_retry_enabled_raises(self) -> None:
        """Test that timeout_ms=0 with retry_policy.enabled=True raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDescriptorPatch(
                timeout_ms=0,
                retry_policy=ModelDescriptorRetryPolicy(
                    enabled=True,
                    max_retries=3,
                ),
            )
        assert "timeout_ms=0" in str(exc_info.value)
        assert "retry_policy" in str(exc_info.value)

    @pytest.mark.unit
    def test_timeout_zero_with_retry_disabled_ok(self) -> None:
        """Test that timeout_ms=0 with retry_policy.enabled=False is valid."""
        patch = ModelDescriptorPatch(
            timeout_ms=0,
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=False,
                max_retries=3,
            ),
        )
        assert patch.timeout_ms == 0
        assert patch.retry_policy is not None
        assert patch.retry_policy.enabled is False

    @pytest.mark.unit
    def test_timeout_zero_with_retry_zero_retries_ok(self) -> None:
        """Test that timeout_ms=0 with max_retries=0 is valid."""
        patch = ModelDescriptorPatch(
            timeout_ms=0,
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=True,
                max_retries=0,
            ),
        )
        assert patch.timeout_ms == 0
        assert patch.retry_policy is not None
        assert patch.retry_policy.max_retries == 0

    @pytest.mark.unit
    def test_timeout_zero_without_retry_policy_ok(self) -> None:
        """Test that timeout_ms=0 without retry_policy is valid."""
        patch = ModelDescriptorPatch(timeout_ms=0)
        assert patch.timeout_ms == 0
        assert patch.retry_policy is None

    @pytest.mark.unit
    def test_positive_timeout_with_retry_enabled_ok(self) -> None:
        """Test that positive timeout with retry_policy.enabled=True is valid."""
        patch = ModelDescriptorPatch(
            timeout_ms=5000,
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=True,
                max_retries=3,
            ),
        )
        assert patch.timeout_ms == 5000
        assert patch.retry_policy is not None
        assert patch.retry_policy.enabled is True

    # =========================================================================
    # idempotent=False with retry_policy conflicts
    # =========================================================================

    @pytest.mark.unit
    def test_non_idempotent_with_retry_enabled_raises(self) -> None:
        """Test that idempotent=False with retry_policy.enabled=True raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDescriptorPatch(
                idempotent=False,
                retry_policy=ModelDescriptorRetryPolicy(
                    enabled=True,
                    max_retries=3,
                ),
            )
        assert "idempotent" in str(exc_info.value)
        assert "retry" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_non_idempotent_with_retry_disabled_ok(self) -> None:
        """Test that idempotent=False with retry_policy.enabled=False is valid."""
        patch = ModelDescriptorPatch(
            idempotent=False,
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=False,
                max_retries=3,
            ),
        )
        assert patch.idempotent is False
        assert patch.retry_policy is not None
        assert patch.retry_policy.enabled is False

    @pytest.mark.unit
    def test_non_idempotent_with_retry_zero_retries_ok(self) -> None:
        """Test that idempotent=False with max_retries=0 is valid."""
        patch = ModelDescriptorPatch(
            idempotent=False,
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=True,
                max_retries=0,
            ),
        )
        assert patch.idempotent is False
        assert patch.retry_policy is not None
        assert patch.retry_policy.max_retries == 0

    @pytest.mark.unit
    def test_non_idempotent_without_retry_policy_ok(self) -> None:
        """Test that idempotent=False without retry_policy is valid."""
        patch = ModelDescriptorPatch(idempotent=False)
        assert patch.idempotent is False
        assert patch.retry_policy is None

    @pytest.mark.unit
    def test_idempotent_true_with_retry_enabled_ok(self) -> None:
        """Test that idempotent=True with retry_policy.enabled=True is valid."""
        patch = ModelDescriptorPatch(
            idempotent=True,
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=True,
                max_retries=3,
            ),
        )
        assert patch.idempotent is True
        assert patch.retry_policy is not None
        assert patch.retry_policy.enabled is True

    @pytest.mark.unit
    def test_idempotent_none_with_retry_enabled_ok(self) -> None:
        """Test that idempotent=None (unset) with retry_policy.enabled=True is valid.

        When idempotent is None (not specified in patch), the base contract's
        value will be used, so we cannot validate at patch level.
        """
        patch = ModelDescriptorPatch(
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=True,
                max_retries=3,
            ),
        )
        assert patch.idempotent is None
        assert patch.retry_policy is not None
        assert patch.retry_policy.enabled is True

    # =========================================================================
    # Combined conflict scenarios
    # =========================================================================

    @pytest.mark.unit
    def test_valid_complete_patch_with_retry(self) -> None:
        """Test a complete valid patch with retry configuration."""
        patch = ModelDescriptorPatch(
            purity="side_effecting",
            idempotent=True,
            timeout_ms=30000,
            retry_policy=ModelDescriptorRetryPolicy(
                enabled=True,
                max_retries=5,
                backoff_strategy="exponential",
            ),
            circuit_breaker=ModelDescriptorCircuitBreaker(enabled=True),
            concurrency_policy="serialized",
            isolation_policy="process",
            observability_level="verbose",
        )
        assert patch.has_overrides() is True
        assert len(patch.get_override_fields()) == 8

    @pytest.mark.unit
    def test_error_message_contains_guidance(self) -> None:
        """Test that error messages provide actionable guidance."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDescriptorPatch(
                timeout_ms=0,
                retry_policy=ModelDescriptorRetryPolicy(enabled=True, max_retries=3),
            )
        error_str = str(exc_info.value)
        # Verify error contains helpful guidance
        assert "timeout" in error_str.lower()
        assert "disable" in error_str.lower() or "positive" in error_str.lower()

    @pytest.mark.unit
    def test_multiple_conflicts_first_wins(self) -> None:
        """Test that when multiple conflicts exist, the first one raises."""
        # Both conflicts: timeout_ms=0 with retry AND non-idempotent with retry
        # The timeout check comes first in the validator
        with pytest.raises(ValidationError) as exc_info:
            ModelDescriptorPatch(
                timeout_ms=0,
                idempotent=False,
                retry_policy=ModelDescriptorRetryPolicy(enabled=True, max_retries=3),
            )
        # Should fail on timeout conflict first
        assert "timeout_ms=0" in str(exc_info.value)
