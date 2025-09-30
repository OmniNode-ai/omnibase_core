"""
Test suite for ModelCliResultMetadata.

Tests the clean, strongly-typed replacement for dict[str, Any] in CLI result metadata.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_data_classification import EnumDataClassification
from omnibase_core.enums.enum_result_category import EnumResultCategory
from omnibase_core.enums.enum_result_type import EnumResultType
from omnibase_core.enums.enum_retention_policy import EnumRetentionPolicy
from omnibase_core.models.cli.model_cli_result_metadata import (
    ModelCliResultMetadata,
)
from omnibase_core.models.metadata.model_semver import ModelSemVer


class TestModelCliResultMetadata:
    """Test cases for ModelCliResultMetadata."""

    def test_initialization_empty(self):
        """Test empty initialization with defaults."""
        metadata = ModelCliResultMetadata()

        assert metadata.metadata_version is None
        assert metadata.result_type == EnumResultType.INFO
        assert metadata.result_category is None
        assert metadata.source_command is None
        assert metadata.source_node is None
        assert isinstance(metadata.processed_at, datetime)
        assert metadata.processor_version is None
        assert metadata.quality_score is None
        assert metadata.confidence_level is None
        assert metadata.data_classification == "internal"
        assert metadata.retention_policy is None
        assert metadata.tags == []
        assert metadata.labels == {}
        assert metadata.processing_time_ms is None
        assert metadata.resource_usage == {}
        assert metadata.compliance_flags == {}
        assert metadata.audit_trail == []
        assert metadata.custom_metadata == {}

    def test_initialization_with_values(self):
        """Test initialization with specific values."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        timestamp = datetime.now(UTC)

        metadata = ModelCliResultMetadata(
            metadata_version=version,
            result_type=EnumResultType.SUCCESS,
            result_category=EnumResultCategory.SUCCESS,
            source_command="test_command",
            source_node="test_node",
            processed_at=timestamp,
            processor_version="1.0.0",
            quality_score=0.95,
            confidence_level=0.88,
            data_classification="public",
            retention_policy="30_days",
            tags=["test", "unit"],
            processing_time_ms=125.5,
        )

        assert metadata.metadata_version == version
        assert metadata.result_type == EnumResultType.SUCCESS
        assert metadata.result_category == EnumResultCategory.SUCCESS
        assert metadata.source_command == "test_command"
        assert metadata.source_node == "test_node"
        assert metadata.processed_at == timestamp
        assert metadata.processor_version.major == 1
        assert metadata.processor_version.minor == 0
        assert metadata.processor_version.patch == 0
        assert metadata.quality_score == 0.95
        assert metadata.confidence_level == 0.88
        assert metadata.data_classification == EnumDataClassification.PUBLIC
        assert metadata.retention_policy == EnumRetentionPolicy.THIRTY_DAYS
        assert metadata.tags == ["test", "unit"]
        assert metadata.processing_time_ms == 125.5

    def test_processed_at_default_utc(self):
        """Test that default processed_at timestamp is in UTC."""
        metadata = ModelCliResultMetadata()

        # Should be recent and in UTC
        now = datetime.now(UTC)
        time_diff = abs((now - metadata.processed_at).total_seconds())
        assert time_diff < 1.0  # Should be within 1 second
        assert metadata.processed_at.tzinfo == UTC

    def test_add_tag(self):
        """Test adding tags."""
        metadata = ModelCliResultMetadata()

        # Start with empty tags
        assert metadata.tags == []

        # Add tags
        metadata.add_tag("performance")
        metadata.add_tag("regression")

        assert len(metadata.tags) == 2
        assert "performance" in metadata.tags
        assert "regression" in metadata.tags

        # Adding duplicate tag should not duplicate
        metadata.add_tag("performance")
        assert len(metadata.tags) == 2  # Should still be 2

    def test_add_label(self):
        """Test adding labels."""
        metadata = ModelCliResultMetadata()

        # Start with empty labels
        assert metadata.labels == {}

        # Add labels
        metadata.add_label("environment", "production")
        metadata.add_label("team", "backend")

        assert metadata.labels["environment"] == "production"
        assert metadata.labels["team"] == "backend"
        assert len(metadata.labels) == 2

    def test_quality_score_validation(self):
        """Test quality score validation and setting."""
        metadata = ModelCliResultMetadata()

        # Valid scores
        metadata.set_quality_score(0.0)
        assert metadata.quality_score == 0.0

        metadata.set_quality_score(0.5)
        assert metadata.quality_score == 0.5

        metadata.set_quality_score(1.0)
        assert metadata.quality_score == 1.0

        # Invalid scores should raise ValueError
        with pytest.raises(
            ValueError,
            match="Quality score must be between 0.0 and 1.0",
        ):
            metadata.set_quality_score(-0.1)

        with pytest.raises(
            ValueError,
            match="Quality score must be between 0.0 and 1.0",
        ):
            metadata.set_quality_score(1.1)

    def test_confidence_level_validation(self):
        """Test confidence level validation and setting."""
        metadata = ModelCliResultMetadata()

        # Valid confidence levels
        metadata.set_confidence_level(0.0)
        assert metadata.confidence_level == 0.0

        metadata.set_confidence_level(0.75)
        assert metadata.confidence_level == 0.75

        metadata.set_confidence_level(1.0)
        assert metadata.confidence_level == 1.0

        # Invalid confidence levels should raise ValueError
        with pytest.raises(
            ValueError,
            match="Confidence level must be between 0.0 and 1.0",
        ):
            metadata.set_confidence_level(-0.01)

        with pytest.raises(
            ValueError,
            match="Confidence level must be between 0.0 and 1.0",
        ):
            metadata.set_confidence_level(1.01)

    def test_add_resource_usage(self):
        """Test adding resource usage information."""
        metadata = ModelCliResultMetadata()

        # Start with empty resource usage
        assert metadata.resource_usage == {}

        # Add resource data
        metadata.add_resource_usage("cpu_time", 250.5)
        metadata.add_resource_usage("memory_mb", 512.0)
        metadata.add_resource_usage("disk_io", 1024.0)

        assert metadata.resource_usage["cpu_time"] == 250.5
        assert metadata.resource_usage["memory_mb"] == 512.0
        assert metadata.resource_usage["disk_io"] == 1024.0
        assert len(metadata.resource_usage) == 3

    def test_compliance_flags(self):
        """Test compliance flag operations."""
        metadata = ModelCliResultMetadata()

        # Start with empty compliance flags
        assert metadata.compliance_flags == {}

        # Set compliance flags
        metadata.set_compliance_flag("gdpr_compliant", True)
        metadata.set_compliance_flag("sox_compliant", False)
        metadata.set_compliance_flag("hipaa_compliant", True)

        assert metadata.compliance_flags["gdpr_compliant"] is True
        assert metadata.compliance_flags["sox_compliant"] is False
        assert metadata.compliance_flags["hipaa_compliant"] is True

        # Test is_compliant method
        assert not metadata.is_compliant()  # False because sox_compliant is False

        # Set all to True
        metadata.set_compliance_flag("sox_compliant", True)
        assert metadata.is_compliant()  # Now all are True

    def test_audit_trail(self):
        """Test audit trail functionality."""
        metadata = ModelCliResultMetadata()

        # Start with empty audit trail
        assert metadata.audit_trail == []

        # Add audit entries
        metadata.add_audit_entry("Process started")
        metadata.add_audit_entry("Validation completed")

        assert len(metadata.audit_trail) == 2

        # Check that timestamps are added to entries
        for entry in metadata.audit_trail:
            assert ":" in entry  # Should contain timestamp
            assert "Process started" in entry or "Validation completed" in entry

    def test_custom_metadata_operations(self):
        """Test custom metadata field operations."""
        metadata = ModelCliResultMetadata()

        # Start with empty custom metadata
        assert metadata.custom_metadata == {}

        # Set various types of custom fields
        metadata.set_custom_field("string_field", "test_value")
        metadata.set_custom_field("int_field", 42)
        metadata.set_custom_field("float_field", 3.14)
        metadata.set_custom_field("bool_field", True)

        # Verify values - custom_metadata stores ModelCliValue wrappers
        # Access raw_value to get the unwrapped Python value
        assert metadata.custom_metadata["string_field"].raw_value == "test_value"
        assert metadata.custom_metadata["int_field"].raw_value == 42
        assert metadata.custom_metadata["float_field"].raw_value == 3.14
        assert metadata.custom_metadata["bool_field"].raw_value is True

        # Test get_custom_field - returns ModelCliValue wrapper
        string_field = metadata.get_custom_field("string_field")
        assert string_field is not None
        assert string_field.raw_value == "test_value"

        int_field = metadata.get_custom_field("int_field")
        assert int_field is not None
        assert int_field.raw_value == 42

        assert metadata.get_custom_field("nonexistent") is None

        # Test with default value
        default_field = metadata.get_custom_field("nonexistent", "default")
        assert default_field == "default"

    def test_complex_metadata_scenario(self):
        """Test complex metadata scenario with all features."""
        version = ModelSemVer(major=2, minor=1, patch=0)
        metadata = ModelCliResultMetadata(
            metadata_version=version,
            result_type=EnumResultType.SUCCESS,
            result_category=EnumResultCategory.SUCCESS,
            source_command="run_integration_tests",
            source_node="test_runner_node",
            processor_version="2.1.0",
            data_classification="confidential",
            retention_policy="90_days",
        )

        # Add comprehensive metadata
        metadata.add_tag("integration")
        metadata.add_tag("api")
        metadata.add_tag("critical")

        metadata.add_label("environment", "staging")
        metadata.add_label("team", "qa")
        metadata.add_label("priority", "high")

        metadata.set_quality_score(0.92)
        metadata.set_confidence_level(0.87)

        metadata.add_resource_usage("cpu_seconds", 45.2)
        metadata.add_resource_usage("memory_peak_mb", 256.0)
        metadata.add_resource_usage("network_kb", 1024.5)

        metadata.set_compliance_flag("security_scan", True)
        metadata.set_compliance_flag("vulnerability_check", True)
        metadata.set_compliance_flag("code_review", True)

        metadata.add_audit_entry("Test suite started")
        metadata.add_audit_entry("API endpoints validated")
        metadata.add_audit_entry("Security checks passed")

        metadata.set_custom_field("test_count", 150)
        metadata.set_custom_field("success_rate", 0.96)
        metadata.set_custom_field("test_environment", "k8s-staging")

        # Verify all data
        assert len(metadata.tags) == 3
        assert len(metadata.labels) == 3
        assert metadata.quality_score == 0.92
        assert metadata.confidence_level == 0.87
        assert len(metadata.resource_usage) == 3
        assert len(metadata.compliance_flags) == 3
        assert metadata.is_compliant()
        assert len(metadata.audit_trail) == 3
        assert len(metadata.custom_metadata) == 3

    def test_pydantic_validation_constraints(self):
        """Test Pydantic validation constraints."""
        # Test quality_score constraints
        with pytest.raises(ValidationError):
            ModelCliResultMetadata(quality_score=-0.1)

        with pytest.raises(ValidationError):
            ModelCliResultMetadata(quality_score=1.1)

        # Test confidence_level constraints
        with pytest.raises(ValidationError):
            ModelCliResultMetadata(confidence_level=-0.01)

        with pytest.raises(ValidationError):
            ModelCliResultMetadata(confidence_level=1.01)

        # Valid values should work
        metadata = ModelCliResultMetadata(quality_score=0.5, confidence_level=0.8)
        assert metadata.quality_score == 0.5
        assert metadata.confidence_level == 0.8

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        metadata = ModelCliResultMetadata(
            metadata_version=version,
            result_type=EnumResultType.INFO,
            tags=["unit", "fast"],
            quality_score=0.95,
        )
        metadata.add_label("env", "test")

        # Test model_dump
        data = metadata.model_dump()

        assert data["result_type"] == EnumResultType.INFO
        assert data["tags"] == ["unit", "fast"]
        # Check that labels are stored correctly in the internal fields
        assert len(data["label_ids"]) == 1
        assert len(data["label_names"]) == 1
        assert "env" in data["label_names"]
        assert data["quality_score"] == 0.95

        # Test excluding None values
        data_exclude_none = metadata.model_dump(exclude_none=True)
        assert "result_category" not in data_exclude_none
        assert "source_command" not in data_exclude_none

    def test_pydantic_deserialization(self):
        """Test Pydantic model deserialization."""
        timestamp = datetime.now(UTC)
        data = {
            "result_type": EnumResultType.SUCCESS,
            "result_category": EnumResultCategory.SUCCESS,
            "source_command": "pytest",
            "processed_at": timestamp.isoformat(),
            "quality_score": 0.88,
            "confidence_level": 0.76,
            "data_classification": "public",
            "tags": ["deserialization", "test"],
            "labels": {"framework": "pytest"},
            "processing_time_ms": 200.0,
            "resource_usage": {"memory": 128.0},
            "compliance_flags": {"test_coverage": True},
            "audit_trail": ["Test started"],
            "custom_metadata": {"test_id": "12345"},
        }

        metadata = ModelCliResultMetadata.model_validate(data)

        assert metadata.result_type == EnumResultType.SUCCESS
        assert metadata.result_category == EnumResultCategory.SUCCESS
        assert metadata.source_command == "pytest"
        assert metadata.quality_score == 0.88
        assert metadata.confidence_level == 0.76
        assert metadata.data_classification == "public"
        assert metadata.tags == ["deserialization", "test"]
        assert metadata.labels == {"framework": "pytest"}
        assert metadata.processing_time_ms == 200.0
        assert metadata.resource_usage == {"memory": 128.0}
        assert metadata.compliance_flags == {"test_coverage": True}
        assert metadata.audit_trail == ["Test started"]
        # custom_metadata stores ModelCliValue wrappers, check raw_value
        assert "test_id" in metadata.custom_metadata
        assert metadata.custom_metadata["test_id"].raw_value == "12345"

    def test_model_round_trip(self):
        """Test serialization -> deserialization round trip."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        original = ModelCliResultMetadata(
            metadata_version=version,
            result_type=EnumResultType.INFO,
            result_category=EnumResultCategory.VALIDATION,
            source_command="round_trip_cmd",
            quality_score=0.91,
            confidence_level=0.83,
            data_classification="restricted",
        )

        # Add data via methods
        original.add_tag("round-trip")
        original.add_label("test_type", "round_trip")
        original.add_resource_usage("test_time", 50.0)
        original.set_compliance_flag("validation_passed", True)
        original.set_custom_field("iteration", 1)

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back to model
        restored = ModelCliResultMetadata.model_validate(data)

        # Should be equal
        assert restored.metadata_version.major == original.metadata_version.major
        assert restored.result_type == original.result_type
        assert restored.result_category == original.result_category
        assert restored.source_command == original.source_command
        assert restored.quality_score == original.quality_score
        assert restored.confidence_level == original.confidence_level
        assert restored.data_classification == original.data_classification
        assert restored.tags == original.tags
        assert restored.labels == original.labels
        assert restored.resource_usage == original.resource_usage
        assert restored.compliance_flags == original.compliance_flags
        # Compare custom_metadata values through raw_value
        assert "iteration" in restored.custom_metadata
        assert (
            restored.custom_metadata["iteration"].raw_value
            == original.custom_metadata["iteration"].raw_value
        )

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        metadata = ModelCliResultMetadata(
            result_type=EnumResultType.INFO,
            tags=["json", "serialization"],
            quality_score=0.89,
        )

        # Test JSON serialization
        json_str = metadata.model_dump_json()
        assert isinstance(json_str, str)
        assert '"result_type":"info"' in json_str
        assert '"quality_score":0.89' in json_str

        # Test JSON deserialization
        restored = ModelCliResultMetadata.model_validate_json(json_str)
        assert restored.result_type == EnumResultType.INFO
        assert restored.quality_score == 0.89

    def test_is_compliant_edge_cases(self):
        """Test is_compliant method edge cases."""
        metadata = ModelCliResultMetadata()

        # Empty compliance flags should return True
        assert metadata.is_compliant()

        # Single True flag
        metadata.set_compliance_flag("test", True)
        assert metadata.is_compliant()

        # Single False flag
        metadata.set_compliance_flag("test", False)
        assert not metadata.is_compliant()

        # Mixed flags with at least one False
        metadata.set_compliance_flag("other", True)
        assert not metadata.is_compliant()  # Still False due to "test" flag

        # All True flags
        metadata.set_compliance_flag("test", True)
        assert metadata.is_compliant()

    def test_edge_cases_empty_collections(self):
        """Test edge cases with empty collections."""
        metadata = ModelCliResultMetadata(
            tags=[],
            labels={},
            resource_usage={},
            compliance_flags={},
            audit_trail=[],
            custom_metadata={},
        )

        # All collections should be empty
        assert metadata.tags == []
        assert metadata.labels == {}
        assert metadata.resource_usage == {}
        assert metadata.compliance_flags == {}
        assert metadata.audit_trail == []
        assert metadata.custom_metadata == {}

        # is_compliant should return True for empty flags
        assert metadata.is_compliant()

    def test_metadata_version_with_semver(self):
        """Test metadata version with different SemVer values."""
        # Test with version
        version = ModelSemVer(major=1, minor=2, patch=3)
        metadata = ModelCliResultMetadata(metadata_version=version)

        assert metadata.metadata_version == version
        assert metadata.metadata_version.major == 1
        assert metadata.metadata_version.minor == 2
        assert metadata.metadata_version.patch == 3

        # Test serialization with SemVer
        data = metadata.model_dump()
        restored = ModelCliResultMetadata.model_validate(data)
        assert restored.metadata_version.major == 1
        assert restored.metadata_version.minor == 2
        assert restored.metadata_version.patch == 3
