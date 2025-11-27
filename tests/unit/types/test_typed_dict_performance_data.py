"""
Test suite for TypedDictPerformanceData.
"""

from omnibase_core.types.typed_dict_performance_data import TypedDictPerformanceData


class TestTypedDictPerformanceData:
    """Test TypedDictPerformanceData functionality."""

    def test_typed_dict_performance_data_empty(self):
        """Test creating empty TypedDictPerformanceData."""
        data: TypedDictPerformanceData = {}

        assert isinstance(data, dict)
        assert len(data) == 0

    def test_typed_dict_performance_data_with_average_execution_time(self):
        """Test TypedDictPerformanceData with average execution time only."""
        data: TypedDictPerformanceData = {"average_execution_time_ms": 150.5}

        assert data["average_execution_time_ms"] == 150.5
        assert isinstance(data["average_execution_time_ms"], float)

    def test_typed_dict_performance_data_with_peak_memory_usage(self):
        """Test TypedDictPerformanceData with peak memory usage only."""
        data: TypedDictPerformanceData = {"peak_memory_usage_mb": 256.75}

        assert data["peak_memory_usage_mb"] == 256.75
        assert isinstance(data["peak_memory_usage_mb"], float)

    def test_typed_dict_performance_data_with_total_invocations(self):
        """Test TypedDictPerformanceData with total invocations only."""
        data: TypedDictPerformanceData = {"total_invocations": 1000}

        assert data["total_invocations"] == 1000
        assert isinstance(data["total_invocations"], int)

    def test_typed_dict_performance_data_complete(self):
        """Test TypedDictPerformanceData with all fields."""
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": 200.25,
            "peak_memory_usage_mb": 512.0,
            "total_invocations": 5000,
        }

        assert data["average_execution_time_ms"] == 200.25
        assert data["peak_memory_usage_mb"] == 512.0
        assert data["total_invocations"] == 5000

    def test_typed_dict_performance_data_partial_fields(self):
        """Test TypedDictPerformanceData with some fields."""
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": 100.0,
            "total_invocations": 2500,
        }

        assert data["average_execution_time_ms"] == 100.0
        assert data["total_invocations"] == 2500
        assert "peak_memory_usage_mb" not in data

    def test_typed_dict_performance_data_zero_values(self):
        """Test TypedDictPerformanceData with zero values."""
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": 0.0,
            "peak_memory_usage_mb": 0.0,
            "total_invocations": 0,
        }

        assert data["average_execution_time_ms"] == 0.0
        assert data["peak_memory_usage_mb"] == 0.0
        assert data["total_invocations"] == 0

    def test_typed_dict_performance_data_negative_values(self):
        """Test TypedDictPerformanceData with negative values."""
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": -1.5,
            "peak_memory_usage_mb": -10.0,
            "total_invocations": -100,
        }

        assert data["average_execution_time_ms"] == -1.5
        assert data["peak_memory_usage_mb"] == -10.0
        assert data["total_invocations"] == -100

    def test_typed_dict_performance_data_large_values(self):
        """Test TypedDictPerformanceData with large values."""
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": 999999.99,
            "peak_memory_usage_mb": 999999.99,
            "total_invocations": 999999999,
        }

        assert data["average_execution_time_ms"] == 999999.99
        assert data["peak_memory_usage_mb"] == 999999.99
        assert data["total_invocations"] == 999999999

    def test_typed_dict_performance_data_decimal_precision(self):
        """Test TypedDictPerformanceData with high decimal precision."""
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": 123.456789,
            "peak_memory_usage_mb": 987.654321,
        }

        assert data["average_execution_time_ms"] == 123.456789
        assert data["peak_memory_usage_mb"] == 987.654321

    def test_typed_dict_performance_data_type_annotations(self):
        """Test that all fields have correct type annotations."""
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": 100.0,
            "peak_memory_usage_mb": 200.0,
            "total_invocations": 1000,
        }

        assert isinstance(data["average_execution_time_ms"], float)
        assert isinstance(data["peak_memory_usage_mb"], float)
        assert isinstance(data["total_invocations"], int)

    def test_typed_dict_performance_data_mutability(self):
        """Test that TypedDictPerformanceData behaves like a regular dict."""
        data: TypedDictPerformanceData = {"average_execution_time_ms": 100.0}

        # Should be able to modify like a regular dict
        data["peak_memory_usage_mb"] = 200.0
        data["total_invocations"] = 500
        data["average_execution_time_ms"] = 150.0

        assert data["average_execution_time_ms"] == 150.0
        assert data["peak_memory_usage_mb"] == 200.0
        assert data["total_invocations"] == 500

    def test_typed_dict_performance_data_equality(self):
        """Test equality comparison between instances."""
        data1: TypedDictPerformanceData = {
            "average_execution_time_ms": 100.0,
            "peak_memory_usage_mb": 200.0,
            "total_invocations": 1000,
        }

        data2: TypedDictPerformanceData = {
            "average_execution_time_ms": 100.0,
            "peak_memory_usage_mb": 200.0,
            "total_invocations": 1000,
        }

        assert data1 == data2

        # Modify one field
        data2["average_execution_time_ms"] = 200.0
        assert data1 != data2

    def test_typed_dict_performance_data_edge_cases(self):
        """Test edge cases for performance data."""
        # Test with very small values
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": 0.001,
            "peak_memory_usage_mb": 0.001,
            "total_invocations": 1,
        }

        assert data["average_execution_time_ms"] == 0.001
        assert data["peak_memory_usage_mb"] == 0.001
        assert data["total_invocations"] == 1

    def test_typed_dict_performance_data_float_precision(self):
        """Test float precision handling."""
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": 1.0 / 3.0,  # Should be approximately 0.333...
            "peak_memory_usage_mb": 2.0 / 3.0,  # Should be approximately 0.666...
        }

        assert abs(data["average_execution_time_ms"] - 0.3333333333333333) < 1e-10
        assert abs(data["peak_memory_usage_mb"] - 0.6666666666666666) < 1e-10

    def test_typed_dict_performance_data_optional_fields(self):
        """Test that all fields are optional (total=False)."""
        # Test with no fields
        empty_data: TypedDictPerformanceData = {}
        assert len(empty_data) == 0

        # Test with one field
        single_field_data: TypedDictPerformanceData = {
            "average_execution_time_ms": 100.0
        }
        assert len(single_field_data) == 1

        # Test with two fields
        two_field_data: TypedDictPerformanceData = {
            "average_execution_time_ms": 100.0,
            "peak_memory_usage_mb": 200.0,
        }
        assert len(two_field_data) == 2

    def test_typed_dict_performance_data_nested_access(self):
        """Test accessing nested properties."""
        data: TypedDictPerformanceData = {
            "average_execution_time_ms": 100.0,
            "peak_memory_usage_mb": 200.0,
            "total_invocations": 1000,
        }

        # Test accessing all fields
        fields = [
            "average_execution_time_ms",
            "peak_memory_usage_mb",
            "total_invocations",
        ]
        for field in fields:
            assert field in data
            if field == "total_invocations":
                assert isinstance(data[field], int)
            else:
                assert isinstance(data[field], float)
