"""Tests for EnumPipelineStage."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_pipeline_stage import EnumPipelineStage


@pytest.mark.unit
class TestEnumPipelineStage:
    """Test suite for EnumPipelineStage."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumPipelineStage.FILE_DISCOVERY == "FILE_DISCOVERY"
        assert EnumPipelineStage.STAMP_VALIDATION == "STAMP_VALIDATION"
        assert EnumPipelineStage.CONTENT_EXTRACTION == "CONTENT_EXTRACTION"
        assert EnumPipelineStage.LANGEXTRACT_PROCESSING == "LANGEXTRACT_PROCESSING"
        assert EnumPipelineStage.VECTOR_EMBEDDING == "VECTOR_EMBEDDING"
        assert EnumPipelineStage.DATABASE_STORAGE == "DATABASE_STORAGE"
        assert EnumPipelineStage.EVENT_PUBLISHING == "EVENT_PUBLISHING"
        assert EnumPipelineStage.VALIDATION_COMPLETE == "VALIDATION_COMPLETE"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumPipelineStage, str)
        assert issubclass(EnumPipelineStage, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        stage = EnumPipelineStage.FILE_DISCOVERY
        assert isinstance(stage, str)
        assert stage == "FILE_DISCOVERY"
        assert len(stage) == 14

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumPipelineStage)
        assert len(values) == 8
        assert EnumPipelineStage.FILE_DISCOVERY in values
        assert EnumPipelineStage.VALIDATION_COMPLETE in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumPipelineStage.CONTENT_EXTRACTION in EnumPipelineStage
        assert "CONTENT_EXTRACTION" in [e.value for e in EnumPipelineStage]

    def test_enum_comparison(self):
        """Test enum comparison."""
        stage1 = EnumPipelineStage.VECTOR_EMBEDDING
        stage2 = EnumPipelineStage.VECTOR_EMBEDDING
        stage3 = EnumPipelineStage.DATABASE_STORAGE

        assert stage1 == stage2
        assert stage1 != stage3
        assert stage1 == "VECTOR_EMBEDDING"

    def test_enum_serialization(self):
        """Test enum serialization."""
        stage = EnumPipelineStage.LANGEXTRACT_PROCESSING
        serialized = stage.value
        assert serialized == "LANGEXTRACT_PROCESSING"
        json_str = json.dumps(stage)
        assert json_str == '"LANGEXTRACT_PROCESSING"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        stage = EnumPipelineStage("STAMP_VALIDATION")
        assert stage == EnumPipelineStage.STAMP_VALIDATION

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumPipelineStage("INVALID_STAGE")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "FILE_DISCOVERY",
            "STAMP_VALIDATION",
            "CONTENT_EXTRACTION",
            "LANGEXTRACT_PROCESSING",
            "VECTOR_EMBEDDING",
            "DATABASE_STORAGE",
            "EVENT_PUBLISHING",
            "VALIDATION_COMPLETE",
        }
        actual_values = {e.value for e in EnumPipelineStage}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumPipelineStage.__doc__ is not None
        assert "pipeline" in EnumPipelineStage.__doc__.lower()

    def test_pipeline_logical_order(self):
        """Test logical ordering of pipeline stages."""
        # Expected order of pipeline stages
        expected_order = [
            EnumPipelineStage.FILE_DISCOVERY,
            EnumPipelineStage.STAMP_VALIDATION,
            EnumPipelineStage.CONTENT_EXTRACTION,
            EnumPipelineStage.LANGEXTRACT_PROCESSING,
            EnumPipelineStage.VECTOR_EMBEDDING,
            EnumPipelineStage.DATABASE_STORAGE,
            EnumPipelineStage.EVENT_PUBLISHING,
            EnumPipelineStage.VALIDATION_COMPLETE,
        ]
        # All stages should be valid
        assert all(stage in EnumPipelineStage for stage in expected_order)

    def test_initial_stages(self):
        """Test initial processing stages."""
        initial_stages = {
            EnumPipelineStage.FILE_DISCOVERY,
            EnumPipelineStage.STAMP_VALIDATION,
            EnumPipelineStage.CONTENT_EXTRACTION,
        }
        assert all(stage in EnumPipelineStage for stage in initial_stages)

    def test_processing_stages(self):
        """Test data processing stages."""
        processing_stages = {
            EnumPipelineStage.LANGEXTRACT_PROCESSING,
            EnumPipelineStage.VECTOR_EMBEDDING,
        }
        assert all(stage in EnumPipelineStage for stage in processing_stages)

    def test_finalization_stages(self):
        """Test finalization stages."""
        finalization_stages = {
            EnumPipelineStage.DATABASE_STORAGE,
            EnumPipelineStage.EVENT_PUBLISHING,
            EnumPipelineStage.VALIDATION_COMPLETE,
        }
        assert all(stage in EnumPipelineStage for stage in finalization_stages)

    def test_all_stages_categorized(self):
        """Test that all pipeline stages are properly categorized."""
        # Initial stages
        initial = {
            EnumPipelineStage.FILE_DISCOVERY,
            EnumPipelineStage.STAMP_VALIDATION,
            EnumPipelineStage.CONTENT_EXTRACTION,
        }

        # Processing stages
        processing = {
            EnumPipelineStage.LANGEXTRACT_PROCESSING,
            EnumPipelineStage.VECTOR_EMBEDDING,
        }

        # Finalization stages
        finalization = {
            EnumPipelineStage.DATABASE_STORAGE,
            EnumPipelineStage.EVENT_PUBLISHING,
            EnumPipelineStage.VALIDATION_COMPLETE,
        }

        # All stages should be categorized
        all_stages = initial | processing | finalization
        assert all_stages == set(EnumPipelineStage)
