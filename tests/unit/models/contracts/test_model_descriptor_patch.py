# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelDescriptorPatch."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch
from omnibase_core.models.runtime.model_descriptor_circuit_breaker import (
    ModelDescriptorCircuitBreaker,
)
from omnibase_core.models.runtime.model_descriptor_retry_policy import (
    ModelDescriptorRetryPolicy,
)


class TestModelDescriptorPatch:
    """Tests for ModelDescriptorPatch model."""

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

    def test_single_override(self) -> None:
        """Test patch with single override."""
        patch = ModelDescriptorPatch(timeout_ms=5000)
        assert patch.timeout_ms == 5000
        assert patch.purity is None

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

    def test_purity_values(self) -> None:
        """Test valid purity values."""
        for purity in ["pure", "side_effecting"]:
            patch = ModelDescriptorPatch(purity=purity)  # type: ignore[arg-type]
            assert patch.purity == purity

    def test_purity_invalid_value(self) -> None:
        """Test invalid purity value."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(purity="invalid")  # type: ignore[arg-type]

    def test_concurrency_policy_values(self) -> None:
        """Test valid concurrency policy values."""
        for policy in ["parallel_ok", "serialized", "singleflight"]:
            patch = ModelDescriptorPatch(concurrency_policy=policy)  # type: ignore[arg-type]
            assert patch.concurrency_policy == policy

    def test_concurrency_policy_invalid(self) -> None:
        """Test invalid concurrency policy value."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(concurrency_policy="invalid")  # type: ignore[arg-type]

    def test_isolation_policy_values(self) -> None:
        """Test valid isolation policy values."""
        for policy in ["none", "process", "container", "vm"]:
            patch = ModelDescriptorPatch(isolation_policy=policy)  # type: ignore[arg-type]
            assert patch.isolation_policy == policy

    def test_isolation_policy_invalid(self) -> None:
        """Test invalid isolation policy value."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(isolation_policy="invalid")  # type: ignore[arg-type]

    def test_observability_level_values(self) -> None:
        """Test valid observability level values."""
        for level in ["minimal", "standard", "verbose"]:
            patch = ModelDescriptorPatch(observability_level=level)  # type: ignore[arg-type]
            assert patch.observability_level == level

    def test_observability_level_invalid(self) -> None:
        """Test invalid observability level value."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(observability_level="invalid")  # type: ignore[arg-type]

    def test_timeout_ms_non_negative(self) -> None:
        """Test timeout_ms must be non-negative."""
        patch = ModelDescriptorPatch(timeout_ms=0)
        assert patch.timeout_ms == 0

        with pytest.raises(ValidationError):
            ModelDescriptorPatch(timeout_ms=-1)

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

    def test_has_overrides_empty(self) -> None:
        """Test has_overrides with empty patch."""
        patch = ModelDescriptorPatch()
        assert patch.has_overrides() is False

    def test_has_overrides_with_fields(self) -> None:
        """Test has_overrides with fields set."""
        patch = ModelDescriptorPatch(timeout_ms=5000)
        assert patch.has_overrides() is True

    def test_get_override_fields_empty(self) -> None:
        """Test get_override_fields with empty patch."""
        patch = ModelDescriptorPatch()
        assert patch.get_override_fields() == []

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

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelDescriptorPatch(
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

    def test_frozen_model(self) -> None:
        """Test that the model is immutable."""
        patch = ModelDescriptorPatch(timeout_ms=5000)
        with pytest.raises(ValidationError):
            patch.timeout_ms = 10000  # type: ignore[misc]

    def test_repr_empty(self) -> None:
        """Test string representation of empty patch."""
        patch = ModelDescriptorPatch()
        assert "empty" in repr(patch)

    def test_repr_with_overrides(self) -> None:
        """Test string representation with overrides."""
        patch = ModelDescriptorPatch(purity="pure", timeout_ms=5000)
        repr_str = repr(patch)
        assert "overrides" in repr_str
        assert "purity" in repr_str
        assert "timeout_ms" in repr_str

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

    def test_to_dict_excludes_none(self) -> None:
        """Test serialization excludes None values when using exclude_none."""
        patch = ModelDescriptorPatch(purity="pure", timeout_ms=5000)
        data = patch.model_dump(exclude_none=True)
        assert data == {"purity": "pure", "timeout_ms": 5000}

    def test_equality(self) -> None:
        """Test equality comparison."""
        patch1 = ModelDescriptorPatch(purity="pure")
        patch2 = ModelDescriptorPatch(purity="pure")
        patch3 = ModelDescriptorPatch(purity="side_effecting")
        assert patch1 == patch2
        assert patch1 != patch3

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
