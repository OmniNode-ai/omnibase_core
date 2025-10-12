"""
Tests for ModelMissingTool.

This module tests the enterprise missing tool tracking model with comprehensive
error analysis, business intelligence, and operational insights.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_tool_category import EnumToolCategory
from omnibase_core.enums.enum_tool_criticality import EnumToolCriticality
from omnibase_core.enums.enum_tool_missing_reason import EnumToolMissingReason
from omnibase_core.enums.enum_tool_status import EnumToolStatus
from omnibase_core.models.core.model_missing_tool import ModelMissingTool


class TestModelMissingToolBasic:
    """Test basic ModelMissingTool functionality."""

    def test_create_missing_tool_basic(self):
        """Test creating a basic missing tool."""
        tool = ModelMissingTool(
            tool_name="test_tool",
            reason="Tool not found in registry",
            expected_type="TestTool",
        )

        assert tool.tool_name == "test_tool"
        assert tool.reason == "Tool not found in registry"
        assert tool.expected_type == "TestTool"
        assert tool.reason_category == EnumToolMissingReason.NOT_FOUND
        assert tool.criticality == EnumToolCriticality.MEDIUM
        assert tool.tool_category == EnumToolCategory.UTILITY

    def test_create_missing_tool_with_all_fields(self):
        """Test creating a missing tool with all fields."""
        tool = ModelMissingTool(
            tool_name="critical_processor",
            reason="Import error: ModuleNotFoundError",
            expected_type="CriticalProcessor",
            reason_category=EnumToolMissingReason.IMPORT_ERROR,
            criticality=EnumToolCriticality.HIGH,
            tool_category=EnumToolCategory.PROCESSOR,
            expected_interface="ProcessorProtocol",
            actual_type_found="None",
            error_details="ModuleNotFoundError: No module named 'critical_processor'",
        )

        assert tool.tool_name == "critical_processor"
        assert tool.reason == "Import error: ModuleNotFoundError"
        assert tool.expected_type == "CriticalProcessor"
        assert tool.reason_category == EnumToolMissingReason.IMPORT_ERROR
        assert tool.criticality == EnumToolCriticality.HIGH
        assert tool.tool_category == EnumToolCategory.PROCESSOR
        assert tool.expected_interface == "ProcessorProtocol"
        assert tool.actual_type_found == "None"
        assert (
            tool.error_details
            == "ModuleNotFoundError: No module named 'critical_processor'"
        )

    def test_missing_tool_validation(self):
        """Test missing tool validation."""
        # Valid tool
        tool = ModelMissingTool(
            tool_name="valid_tool", reason="Valid reason", expected_type="ValidType"
        )
        assert tool.tool_name == "valid_tool"

        # Test required fields
        with pytest.raises(ValueError):
            ModelMissingTool(
                tool_name="",  # Empty name should fail
                reason="Test reason",
                expected_type="TestType",
            )

        with pytest.raises(ValueError):
            ModelMissingTool(
                tool_name="test_tool",
                reason="",  # Empty reason should fail
                expected_type="TestType",
            )

        with pytest.raises(ValueError):
            ModelMissingTool(
                tool_name="test_tool",
                reason="Test reason",
                expected_type="",  # Empty expected_type should fail
            )

    def test_missing_tool_serialization(self):
        """Test missing tool serialization."""
        tool = ModelMissingTool(
            tool_name="serialization_test",
            reason="Testing serialization",
            expected_type="SerializationType",
        )

        data = tool.model_dump()
        assert data["tool_name"] == "serialization_test"
        assert data["reason"] == "Testing serialization"
        assert data["expected_type"] == "SerializationType"
        assert data["reason_category"] == "NOT_FOUND"
        assert data["criticality"] == "MEDIUM"
        assert data["tool_category"] == "UTILITY"

    def test_missing_tool_deserialization(self):
        """Test missing tool deserialization."""
        data = {
            "tool_name": "deserialization_test",
            "reason": "Testing deserialization",
            "expected_type": "DeserializationType",
            "reason_category": "IMPORT_ERROR",
            "criticality": "HIGH",
            "tool_category": "PROCESSOR",
        }

        tool = ModelMissingTool.model_validate(data)
        assert tool.tool_name == "deserialization_test"
        assert tool.reason == "Testing deserialization"
        assert tool.expected_type == "DeserializationType"
        assert tool.reason_category == EnumToolMissingReason.IMPORT_ERROR
        assert tool.criticality == EnumToolCriticality.HIGH
        assert tool.tool_category == EnumToolCategory.PROCESSOR


class TestModelMissingToolEnums:
    """Test ModelMissingTool with different enum values."""

    def test_reason_categories(self):
        """Test different reason categories."""
        for reason in EnumToolMissingReason:
            tool = ModelMissingTool(
                tool_name="test_tool",
                reason=f"Test reason for {reason.value}",
                expected_type="TestType",
                reason_category=reason,
            )
            assert tool.reason_category == reason

    def test_criticality_levels(self):
        """Test different criticality levels."""
        for criticality in EnumToolCriticality:
            tool = ModelMissingTool(
                tool_name="test_tool",
                reason="Test reason",
                expected_type="TestType",
                criticality=criticality,
            )
            assert tool.criticality == criticality

    def test_tool_categories(self):
        """Test different tool categories."""
        for category in EnumToolCategory:
            tool = ModelMissingTool(
                tool_name="test_tool",
                reason="Test reason",
                expected_type="TestType",
                tool_category=category,
            )
            assert tool.tool_category == category

    def test_enum_combinations(self):
        """Test various enum combinations."""
        tool = ModelMissingTool(
            tool_name="complex_tool",
            reason="Complex error scenario",
            expected_type="ComplexType",
            reason_category=EnumToolMissingReason.TYPE_MISMATCH,
            criticality=EnumToolCriticality.CRITICAL,
            tool_category=EnumToolCategory.SECURITY,
        )

        assert tool.reason_category == EnumToolMissingReason.TYPE_MISMATCH
        assert tool.criticality == EnumToolCriticality.CRITICAL
        assert tool.tool_category == EnumToolCategory.SECURITY


class TestModelMissingToolEdgeCases:
    """Test ModelMissingTool edge cases."""

    def test_long_tool_name(self):
        """Test tool name at maximum length."""
        long_name = "a" * 200  # Maximum length
        tool = ModelMissingTool(
            tool_name=long_name, reason="Test reason", expected_type="TestType"
        )
        assert tool.tool_name == long_name

    def test_long_reason(self):
        """Test reason at maximum length."""
        long_reason = "a" * 1000  # Maximum length
        tool = ModelMissingTool(
            tool_name="test_tool", reason=long_reason, expected_type="TestType"
        )
        assert tool.reason == long_reason

    def test_long_expected_type(self):
        """Test expected_type at maximum length."""
        long_type = "a" * 500  # Maximum length
        tool = ModelMissingTool(
            tool_name="test_tool", reason="Test reason", expected_type=long_type
        )
        assert tool.expected_type == long_type

    def test_long_expected_interface(self):
        """Test expected_interface at maximum length."""
        long_interface = "a" * 300  # Maximum length
        tool = ModelMissingTool(
            tool_name="test_tool",
            reason="Test reason",
            expected_type="TestType",
            expected_interface=long_interface,
        )
        assert tool.expected_interface == long_interface

    def test_long_actual_type_found(self):
        """Test actual_type_found at maximum length."""
        long_type = "a" * 500  # Maximum length
        tool = ModelMissingTool(
            tool_name="test_tool",
            reason="Test reason",
            expected_type="TestType",
            actual_type_found=long_type,
        )
        assert tool.actual_type_found == long_type

    def test_long_error_details(self):
        """Test error_details at maximum length."""
        long_error = "a" * 2000  # Maximum length
        tool = ModelMissingTool(
            tool_name="test_tool",
            reason="Test reason",
            expected_type="TestType",
            error_details=long_error,
        )
        assert tool.error_details == long_error

    def test_unicode_characters(self):
        """Test with unicode characters."""
        tool = ModelMissingTool(
            tool_name="测试工具", reason="Unicode测试原因", expected_type="Unicode类型"
        )
        assert tool.tool_name == "测试工具"
        assert tool.reason == "Unicode测试原因"
        assert tool.expected_type == "Unicode类型"

    def test_special_characters(self):
        """Test with special characters."""
        tool = ModelMissingTool(
            tool_name="tool-with-special_chars.123",
            reason="Reason with special chars: !@#$%^&*()",
            expected_type="Type<Generic>",
        )
        assert tool.tool_name == "tool-with-special_chars.123"
        assert tool.reason == "Reason with special chars: !@#$%^&*()"
        assert tool.expected_type == "Type<Generic>"


class TestModelMissingToolBusinessScenarios:
    """Test ModelMissingTool in business scenarios."""

    def test_import_error_scenario(self):
        """Test import error scenario."""
        tool = ModelMissingTool(
            tool_name="missing_dependency",
            reason="ImportError: No module named 'missing_dependency'",
            expected_type="MissingDependency",
            reason_category=EnumToolMissingReason.IMPORT_ERROR,
            criticality=EnumToolCriticality.HIGH,
            tool_category=EnumToolCategory.DEPENDENCY,
            error_details="Traceback (most recent call last):\n  File 'main.py', line 1, in <module>\n    import missing_dependency\nModuleNotFoundError: No module named 'missing_dependency'",
        )

        assert tool.reason_category == EnumToolMissingReason.IMPORT_ERROR
        assert tool.criticality == EnumToolCriticality.HIGH
        assert tool.tool_category == EnumToolCategory.DEPENDENCY

    def test_type_mismatch_scenario(self):
        """Test type mismatch scenario."""
        tool = ModelMissingTool(
            tool_name="type_mismatch_tool",
            reason="Type mismatch: expected Processor, got StringProcessor",
            expected_type="Processor",
            reason_category=EnumToolMissingReason.TYPE_MISMATCH,
            criticality=EnumToolCriticality.MEDIUM,
            tool_category=EnumToolCategory.PROCESSOR,
            actual_type_found="StringProcessor",
            expected_interface="ProcessorProtocol",
        )

        assert tool.reason_category == EnumToolMissingReason.TYPE_MISMATCH
        assert tool.actual_type_found == "StringProcessor"
        assert tool.expected_interface == "ProcessorProtocol"

    def test_security_tool_missing_scenario(self):
        """Test security tool missing scenario."""
        tool = ModelMissingTool(
            tool_name="security_validator",
            reason="Security tool not found - critical for authentication",
            expected_type="SecurityValidator",
            reason_category=EnumToolMissingReason.NOT_FOUND,
            criticality=EnumToolCriticality.CRITICAL,
            tool_category=EnumToolCategory.SECURITY,
            expected_interface="SecurityValidatorProtocol",
        )

        assert tool.criticality == EnumToolCriticality.CRITICAL
        assert tool.tool_category == EnumToolCategory.SECURITY

    def test_utility_tool_missing_scenario(self):
        """Test utility tool missing scenario."""
        tool = ModelMissingTool(
            tool_name="utility_helper",
            reason="Utility tool not found - non-critical",
            expected_type="UtilityHelper",
            reason_category=EnumToolMissingReason.NOT_FOUND,
            criticality=EnumToolCriticality.LOW,
            tool_category=EnumToolCategory.UTILITY,
        )

        assert tool.criticality == EnumToolCriticality.LOW
        assert tool.tool_category == EnumToolCategory.UTILITY


class TestModelMissingToolValidation:
    """Test ModelMissingTool validation rules."""

    def test_tool_name_validation(self):
        """Test tool name validation."""
        # Valid names
        valid_names = [
            "simple_tool",
            "tool-with-dashes",
            "tool.with.dots",
            "tool123",
            "ToolWithCaps",
        ]

        for name in valid_names:
            tool = ModelMissingTool(
                tool_name=name, reason="Test reason", expected_type="TestType"
            )
            assert tool.tool_name == name

        # Invalid names (too long)
        with pytest.raises(ValueError):
            ModelMissingTool(
                tool_name="a" * 201,  # Too long
                reason="Test reason",
                expected_type="TestType",
            )

    def test_reason_validation(self):
        """Test reason validation."""
        # Valid reasons
        valid_reasons = [
            "Simple reason",
            "Reason with numbers 123",
            "Reason with symbols !@#$%",
            "Reason with unicode 测试",
        ]

        for reason in valid_reasons:
            tool = ModelMissingTool(
                tool_name="test_tool", reason=reason, expected_type="TestType"
            )
            assert tool.reason == reason

        # Invalid reasons (too long)
        with pytest.raises(ValueError):
            ModelMissingTool(
                tool_name="test_tool",
                reason="a" * 1001,  # Too long
                expected_type="TestType",
            )

    def test_expected_type_validation(self):
        """Test expected_type validation."""
        # Valid types
        valid_types = [
            "SimpleType",
            "Type<Generic>",
            "TypeWithNumbers123",
            "Type.With.Dots",
        ]

        for type_name in valid_types:
            tool = ModelMissingTool(
                tool_name="test_tool", reason="Test reason", expected_type=type_name
            )
            assert tool.expected_type == type_name

        # Invalid types (too long)
        with pytest.raises(ValueError):
            ModelMissingTool(
                tool_name="test_tool",
                reason="Test reason",
                expected_type="a" * 501,  # Too long
            )


class TestModelMissingToolSerialization:
    """Test ModelMissingTool serialization scenarios."""

    def test_json_serialization(self):
        """Test JSON serialization."""
        tool = ModelMissingTool(
            tool_name="json_test_tool",
            reason="Testing JSON serialization",
            expected_type="JsonTestType",
            reason_category=EnumToolMissingReason.IMPORT_ERROR,
            criticality=EnumToolCriticality.HIGH,
            tool_category=EnumToolCategory.PROCESSOR,
        )

        json_data = tool.model_dump_json()
        assert isinstance(json_data, str)
        assert "json_test_tool" in json_data
        assert "Testing JSON serialization" in json_data
        assert "JsonTestType" in json_data

    def test_roundtrip_serialization(self):
        """Test serialization and deserialization roundtrip."""
        original_tool = ModelMissingTool(
            tool_name="roundtrip_tool",
            reason="Testing roundtrip serialization",
            expected_type="RoundtripType",
            reason_category=EnumToolMissingReason.TYPE_MISMATCH,
            criticality=EnumToolCriticality.MEDIUM,
            tool_category=EnumToolCategory.UTILITY,
            expected_interface="RoundtripProtocol",
            actual_type_found="WrongType",
            error_details="Type mismatch error details",
        )

        # Serialize
        data = original_tool.model_dump()

        # Deserialize
        restored_tool = ModelMissingTool.model_validate(data)

        # Verify all fields match
        assert restored_tool.tool_name == original_tool.tool_name
        assert restored_tool.reason == original_tool.reason
        assert restored_tool.expected_type == original_tool.expected_type
        assert restored_tool.reason_category == original_tool.reason_category
        assert restored_tool.criticality == original_tool.criticality
        assert restored_tool.tool_category == original_tool.tool_category
        assert restored_tool.expected_interface == original_tool.expected_interface
        assert restored_tool.actual_type_found == original_tool.actual_type_found
        assert restored_tool.error_details == original_tool.error_details

    def test_partial_serialization(self):
        """Test serialization with only required fields."""
        tool = ModelMissingTool(
            tool_name="partial_tool",
            reason="Partial serialization test",
            expected_type="PartialType",
        )

        data = tool.model_dump()
        assert "tool_name" in data
        assert "reason" in data
        assert "expected_type" in data
        assert data["tool_name"] == "partial_tool"
        assert data["reason"] == "Partial serialization test"
        assert data["expected_type"] == "PartialType"
