# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelPerformanceRequirements.

Covers the 5 fields:
  - single_operation_max_ms
  - batch_operation_max_s
  - memory_limit_mb
  - cpu_limit_percent
  - throughput_min_ops_per_second
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_performance_requirements import (
    ModelPerformanceRequirements,
)


@pytest.mark.unit
class TestModelPerformanceRequirementsConstruction:
    def test_default_construction_all_none(self) -> None:
        m = ModelPerformanceRequirements()
        assert m.single_operation_max_ms is None
        assert m.batch_operation_max_s is None
        assert m.memory_limit_mb is None
        assert m.cpu_limit_percent is None
        assert m.throughput_min_ops_per_second is None

    def test_full_construction(self) -> None:
        m = ModelPerformanceRequirements(
            single_operation_max_ms=500,
            batch_operation_max_s=30,
            memory_limit_mb=256,
            cpu_limit_percent=80,
            throughput_min_ops_per_second=100.0,
        )
        assert m.single_operation_max_ms == 500
        assert m.batch_operation_max_s == 30
        assert m.memory_limit_mb == 256
        assert m.cpu_limit_percent == 80
        assert m.throughput_min_ops_per_second == 100.0

    def test_partial_construction_only_single_op(self) -> None:
        m = ModelPerformanceRequirements(single_operation_max_ms=100)
        assert m.single_operation_max_ms == 100
        assert m.batch_operation_max_s is None
        assert m.memory_limit_mb is None
        assert m.cpu_limit_percent is None
        assert m.throughput_min_ops_per_second is None

    def test_extra_fields_ignored(self) -> None:
        # model_config has extra="ignore"
        m = ModelPerformanceRequirements(
            single_operation_max_ms=10,
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert m.single_operation_max_ms == 10
        assert not hasattr(m, "unknown_field")


@pytest.mark.unit
class TestSingleOperationMaxMs:
    def test_minimum_valid_value(self) -> None:
        m = ModelPerformanceRequirements(single_operation_max_ms=1)
        assert m.single_operation_max_ms == 1

    def test_typical_value(self) -> None:
        m = ModelPerformanceRequirements(single_operation_max_ms=200)
        assert m.single_operation_max_ms == 200

    def test_large_value(self) -> None:
        m = ModelPerformanceRequirements(single_operation_max_ms=60000)
        assert m.single_operation_max_ms == 60000

    def test_zero_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(single_operation_max_ms=0)

    def test_negative_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(single_operation_max_ms=-1)

    def test_none_is_valid(self) -> None:
        m = ModelPerformanceRequirements(single_operation_max_ms=None)
        assert m.single_operation_max_ms is None

    def test_validate_assignment_zero_rejected(self) -> None:
        m = ModelPerformanceRequirements(single_operation_max_ms=10)
        with pytest.raises(ValidationError):
            m.single_operation_max_ms = 0

    def test_validate_assignment_valid(self) -> None:
        m = ModelPerformanceRequirements(single_operation_max_ms=10)
        m.single_operation_max_ms = 50
        assert m.single_operation_max_ms == 50


@pytest.mark.unit
class TestBatchOperationMaxS:
    def test_minimum_valid_value(self) -> None:
        m = ModelPerformanceRequirements(batch_operation_max_s=1)
        assert m.batch_operation_max_s == 1

    def test_typical_value(self) -> None:
        m = ModelPerformanceRequirements(batch_operation_max_s=60)
        assert m.batch_operation_max_s == 60

    def test_large_value(self) -> None:
        m = ModelPerformanceRequirements(batch_operation_max_s=3600)
        assert m.batch_operation_max_s == 3600

    def test_zero_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(batch_operation_max_s=0)

    def test_negative_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(batch_operation_max_s=-5)

    def test_none_is_valid(self) -> None:
        m = ModelPerformanceRequirements(batch_operation_max_s=None)
        assert m.batch_operation_max_s is None

    def test_validate_assignment_negative_rejected(self) -> None:
        m = ModelPerformanceRequirements(batch_operation_max_s=10)
        with pytest.raises(ValidationError):
            m.batch_operation_max_s = -1

    def test_validate_assignment_valid(self) -> None:
        m = ModelPerformanceRequirements(batch_operation_max_s=10)
        m.batch_operation_max_s = 120
        assert m.batch_operation_max_s == 120


@pytest.mark.unit
class TestMemoryLimitMb:
    def test_minimum_valid_value(self) -> None:
        m = ModelPerformanceRequirements(memory_limit_mb=1)
        assert m.memory_limit_mb == 1

    def test_typical_value(self) -> None:
        m = ModelPerformanceRequirements(memory_limit_mb=512)
        assert m.memory_limit_mb == 512

    def test_large_value(self) -> None:
        m = ModelPerformanceRequirements(memory_limit_mb=65536)
        assert m.memory_limit_mb == 65536

    def test_zero_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(memory_limit_mb=0)

    def test_negative_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(memory_limit_mb=-128)

    def test_none_is_valid(self) -> None:
        m = ModelPerformanceRequirements(memory_limit_mb=None)
        assert m.memory_limit_mb is None

    def test_validate_assignment_zero_rejected(self) -> None:
        m = ModelPerformanceRequirements(memory_limit_mb=256)
        with pytest.raises(ValidationError):
            m.memory_limit_mb = 0

    def test_validate_assignment_valid(self) -> None:
        m = ModelPerformanceRequirements(memory_limit_mb=256)
        m.memory_limit_mb = 1024
        assert m.memory_limit_mb == 1024


@pytest.mark.unit
class TestCpuLimitPercent:
    def test_minimum_valid_value(self) -> None:
        m = ModelPerformanceRequirements(cpu_limit_percent=1)
        assert m.cpu_limit_percent == 1

    def test_maximum_valid_value(self) -> None:
        m = ModelPerformanceRequirements(cpu_limit_percent=100)
        assert m.cpu_limit_percent == 100

    def test_typical_value(self) -> None:
        m = ModelPerformanceRequirements(cpu_limit_percent=75)
        assert m.cpu_limit_percent == 75

    def test_zero_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(cpu_limit_percent=0)

    def test_negative_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(cpu_limit_percent=-10)

    def test_above_100_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(cpu_limit_percent=101)

    def test_none_is_valid(self) -> None:
        m = ModelPerformanceRequirements(cpu_limit_percent=None)
        assert m.cpu_limit_percent is None

    def test_validate_assignment_above_100_rejected(self) -> None:
        m = ModelPerformanceRequirements(cpu_limit_percent=50)
        with pytest.raises(ValidationError):
            m.cpu_limit_percent = 200

    def test_validate_assignment_valid(self) -> None:
        m = ModelPerformanceRequirements(cpu_limit_percent=50)
        m.cpu_limit_percent = 90
        assert m.cpu_limit_percent == 90


@pytest.mark.unit
class TestThroughputMinOpsPerSecond:
    def test_minimum_valid_value_zero(self) -> None:
        # ge=0.0, so 0.0 is allowed
        m = ModelPerformanceRequirements(throughput_min_ops_per_second=0.0)
        assert m.throughput_min_ops_per_second == 0.0

    def test_fractional_value(self) -> None:
        m = ModelPerformanceRequirements(throughput_min_ops_per_second=0.5)
        assert m.throughput_min_ops_per_second == 0.5

    def test_typical_integer_like_value(self) -> None:
        m = ModelPerformanceRequirements(throughput_min_ops_per_second=1000.0)
        assert m.throughput_min_ops_per_second == 1000.0

    def test_large_value(self) -> None:
        m = ModelPerformanceRequirements(throughput_min_ops_per_second=1_000_000.0)
        assert m.throughput_min_ops_per_second == 1_000_000.0

    def test_negative_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelPerformanceRequirements(throughput_min_ops_per_second=-1.0)

    def test_none_is_valid(self) -> None:
        m = ModelPerformanceRequirements(throughput_min_ops_per_second=None)
        assert m.throughput_min_ops_per_second is None

    def test_validate_assignment_negative_rejected(self) -> None:
        m = ModelPerformanceRequirements(throughput_min_ops_per_second=10.0)
        with pytest.raises(ValidationError):
            m.throughput_min_ops_per_second = -0.1

    def test_validate_assignment_valid(self) -> None:
        m = ModelPerformanceRequirements(throughput_min_ops_per_second=10.0)
        m.throughput_min_ops_per_second = 500.0
        assert m.throughput_min_ops_per_second == 500.0
