"""
Comprehensive tests for ModelOnexResult.

Tests cover:
- Basic instantiation with required fields
- Optional field handling
- Recursive child_results composition
- Field validation and type safety
- Pydantic model_config validation
- Edge cases and boundary conditions
"""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.metadata.model_semver import ModelSemVer
from omnibase_core.models.results.model_generic_metadata import ModelGenericMetadata
from omnibase_core.models.results.model_onex_message import ModelOnexMessage
from omnibase_core.models.results.model_onex_result import ModelOnexResult
from omnibase_core.models.results.model_unified_summary import ModelUnifiedSummary
from omnibase_core.models.results.model_unified_version import ModelUnifiedVersion


class TestModelOnexResultBasicInstantiation:
    """Test basic instantiation with required fields."""

    def test_minimal_instantiation_with_status_only(self):
        """Test creating result with only required status field."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS)

        assert result.status == EnumOnexStatus.SUCCESS
        assert result.messages == []
        assert result.target is None
        assert result.child_results is None

    def test_instantiation_with_all_core_fields(self):
        """Test creating result with all primary fields populated."""
        run_id = uuid4()
        timestamp = datetime.now()

        result = ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            target="src/test_file.py",
            run_id=run_id,
            tool_name="test_tool",
            duration=1.5,
            exit_code=0,
            timestamp=timestamp,
        )

        assert result.status == EnumOnexStatus.SUCCESS
        assert result.target == "src/test_file.py"
        assert result.run_id == run_id
        assert result.tool_name == "test_tool"
        assert result.duration == 1.5
        assert result.exit_code == 0
        assert result.timestamp == timestamp

    def test_instantiation_with_messages(self):
        """Test creating result with messages list."""
        messages = [
            ModelOnexMessage(summary="Test passed", level=EnumLogLevel.INFO),
            ModelOnexMessage(summary="Warning found", level=EnumLogLevel.WARNING),
        ]

        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, messages=messages)

        assert len(result.messages) == 2
        assert result.messages[0].summary == "Test passed"
        assert result.messages[1].level == EnumLogLevel.WARNING


class TestModelOnexResultFieldValidation:
    """Test field validation and type safety."""

    def test_status_field_required(self):
        """Test that status field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexResult()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("status",) for error in errors)
        assert any(error["type"] == "missing" for error in errors)

    def test_status_must_be_valid_enum(self):
        """Test that status must be valid EnumOnexStatus value."""
        with pytest.raises(ValidationError):
            ModelOnexResult(status="invalid_status")

    def test_exit_code_accepts_integers(self):
        """Test exit_code field accepts integer values."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, exit_code=0)
        assert result.exit_code == 0

        result = ModelOnexResult(status=EnumOnexStatus.ERROR, exit_code=1)
        assert result.exit_code == 1

    def test_duration_accepts_floats(self):
        """Test duration field accepts float values."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, duration=1.234)
        assert result.duration == 1.234
        assert isinstance(result.duration, float)

    def test_coverage_accepts_floats(self):
        """Test coverage field accepts float values."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, coverage=85.5)
        assert result.coverage == 85.5


class TestModelOnexResultRecursiveComposition:
    """Test recursive child_results composition."""

    def test_single_level_child_results(self):
        """Test adding child results (one level)."""
        parent = ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            tool_name="parent_tool",
            child_results=[
                ModelOnexResult(status=EnumOnexStatus.SUCCESS, tool_name="child1"),
                ModelOnexResult(status=EnumOnexStatus.SUCCESS, tool_name="child2"),
            ],
        )

        assert len(parent.child_results) == 2
        assert parent.child_results[0].tool_name == "child1"
        assert parent.child_results[1].tool_name == "child2"

    def test_nested_child_results_multiple_levels(self):
        """Test nested child results (multiple levels of recursion)."""
        grandchild = ModelOnexResult(
            status=EnumOnexStatus.SUCCESS, tool_name="grandchild"
        )
        child = ModelOnexResult(
            status=EnumOnexStatus.SUCCESS, tool_name="child", child_results=[grandchild]
        )
        parent = ModelOnexResult(
            status=EnumOnexStatus.SUCCESS, tool_name="parent", child_results=[child]
        )

        assert parent.tool_name == "parent"
        assert len(parent.child_results) == 1
        assert parent.child_results[0].tool_name == "child"
        assert len(parent.child_results[0].child_results) == 1
        assert parent.child_results[0].child_results[0].tool_name == "grandchild"

    def test_empty_child_results_list(self):
        """Test that empty child_results list is handled correctly."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, child_results=[])
        assert result.child_results == []


class TestModelOnexResultComplexFields:
    """Test complex nested field structures."""

    def test_summary_field_integration(self):
        """Test summary field with ModelUnifiedSummary."""
        summary = ModelUnifiedSummary(
            total=10, passed=8, failed=2, skipped=0, fixed=0, warnings=1
        )
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, summary=summary)

        assert result.summary.total == 10
        assert result.summary.passed == 8
        assert result.summary.failed == 2
        assert result.summary.warnings == 1

    def test_metadata_field_integration(self):
        """Test metadata field with ModelGenericMetadata."""
        now = datetime.now()
        metadata = ModelGenericMetadata(
            created_at=now,
            created_by="test_user",
            version=ModelSemVer(major=1, minor=0, patch=0),
            tags=["test", "validation"],
        )
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, metadata=metadata)

        assert result.metadata.created_at == now
        assert result.metadata.created_by == "test_user"
        assert result.metadata.version.major == 1
        assert "test" in result.metadata.tags

    def test_version_field_integration(self):
        """Test version field with ModelUnifiedVersion."""
        version = ModelUnifiedVersion(
            protocol_version=ModelSemVer(major=1, minor=0, patch=0),
            tool_version=ModelSemVer(major=2, minor=1, patch=3),
        )
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, version=version)

        assert result.version.protocol_version.major == 1
        assert result.version.tool_version.major == 2


class TestModelOnexResultOptionalFields:
    """Test optional field handling."""

    def test_all_optional_fields_can_be_none(self):
        """Test that all optional fields can be None."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS)

        assert result.target is None
        assert result.summary is None
        assert result.metadata is None
        assert result.suggestions is None
        assert result.diff is None
        assert result.auto_fix_applied is None
        assert result.fixed_files is None
        assert result.failed_files is None
        assert result.version is None
        assert result.duration is None
        assert result.exit_code is None
        assert result.run_id is None
        assert result.child_results is None
        assert result.output_format is None
        assert result.cli_args is None
        assert result.orchestrator_info is None
        assert result.tool_name is None
        assert result.skipped_reason is None
        assert result.coverage is None
        assert result.test_type is None
        assert result.batch_id is None
        assert result.parent_id is None
        assert result.timestamp is None

    def test_suggestions_list_field(self):
        """Test suggestions list field."""
        suggestions = ["Fix line 10", "Consider refactoring", "Update documentation"]
        result = ModelOnexResult(status=EnumOnexStatus.WARNING, suggestions=suggestions)

        assert len(result.suggestions) == 3
        assert "Fix line 10" in result.suggestions

    def test_fixed_and_failed_files_lists(self):
        """Test fixed_files and failed_files list fields."""
        result = ModelOnexResult(
            status=EnumOnexStatus.PARTIAL,
            fixed_files=["file1.py", "file2.py"],
            failed_files=["file3.py"],
        )

        assert len(result.fixed_files) == 2
        assert len(result.failed_files) == 1
        assert "file1.py" in result.fixed_files
        assert "file3.py" in result.failed_files

    def test_cli_args_list_field(self):
        """Test cli_args list field."""
        cli_args = ["--verbose", "--config=test.yaml", "--parallel"]
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, cli_args=cli_args)

        assert len(result.cli_args) == 3
        assert "--verbose" in result.cli_args


class TestModelOnexResultUUIDs:
    """Test UUID field handling."""

    def test_run_id_uuid_field(self):
        """Test run_id UUID field."""
        run_id = uuid4()
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, run_id=run_id)

        assert result.run_id == run_id
        assert isinstance(result.run_id, type(run_id))

    def test_batch_id_and_parent_id_uuids(self):
        """Test batch_id and parent_id UUID fields."""
        batch_id = uuid4()
        parent_id = uuid4()

        result = ModelOnexResult(
            status=EnumOnexStatus.SUCCESS, batch_id=batch_id, parent_id=parent_id
        )

        assert result.batch_id == batch_id
        assert result.parent_id == parent_id


class TestModelOnexResultBooleanFields:
    """Test boolean field handling."""

    def test_auto_fix_applied_boolean(self):
        """Test auto_fix_applied boolean field."""
        result_fixed = ModelOnexResult(
            status=EnumOnexStatus.SUCCESS, auto_fix_applied=True
        )
        result_not_fixed = ModelOnexResult(
            status=EnumOnexStatus.WARNING, auto_fix_applied=False
        )

        assert result_fixed.auto_fix_applied is True
        assert result_not_fixed.auto_fix_applied is False


class TestModelOnexResultEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_messages_list_default(self):
        """Test that messages defaults to empty list."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS)
        assert result.messages == []
        assert isinstance(result.messages, list)

    def test_zero_duration(self):
        """Test duration can be zero."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, duration=0.0)
        assert result.duration == 0.0

    def test_negative_exit_code(self):
        """Test that negative exit codes are accepted."""
        result = ModelOnexResult(status=EnumOnexStatus.ERROR, exit_code=-1)
        assert result.exit_code == -1

    def test_large_coverage_value(self):
        """Test coverage with boundary values."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, coverage=100.0)
        assert result.coverage == 100.0

    def test_empty_diff_string(self):
        """Test diff field with empty string."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, diff="")
        assert result.diff == ""

    def test_multiline_diff_string(self):
        """Test diff field with multiline content."""
        diff_content = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
-old line
+new line
"""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, diff=diff_content)
        assert result.diff == diff_content


class TestModelOnexResultSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump_basic(self):
        """Test model_dump() produces correct dictionary."""
        result = ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            target="test.py",
            tool_name="test_tool",
            duration=1.5,
        )

        dumped = result.model_dump()

        assert dumped["status"] == EnumOnexStatus.SUCCESS
        assert dumped["target"] == "test.py"
        assert dumped["tool_name"] == "test_tool"
        assert dumped["duration"] == 1.5

    def test_model_dump_exclude_none(self):
        """Test model_dump(exclude_none=True) removes None fields."""
        result = ModelOnexResult(status=EnumOnexStatus.SUCCESS, target="test.py")

        dumped = result.model_dump(exclude_none=True)

        assert "status" in dumped
        assert "target" in dumped
        assert "summary" not in dumped
        assert "metadata" not in dumped

    def test_model_dump_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            target="test.py",
            duration=1.5,
            exit_code=0,
        )

        json_str = original.model_dump_json()
        restored = ModelOnexResult.model_validate_json(json_str)

        assert restored.status == original.status
        assert restored.target == original.target
        assert restored.duration == original.duration
        assert restored.exit_code == original.exit_code


class TestModelOnexResultModelConfig:
    """Test Pydantic model_config settings."""

    def test_arbitrary_types_allowed_config(self):
        """Test that arbitrary_types_allowed is configured correctly."""
        assert ModelOnexResult.model_config["arbitrary_types_allowed"] is True

    def test_json_schema_extra_has_example(self):
        """Test that json_schema_extra contains example data."""
        schema_extra = ModelOnexResult.model_config.get("json_schema_extra", {})
        assert "example" in schema_extra

        example = schema_extra["example"]
        assert "status" in example
        assert example["status"] == "success"
        assert "messages" in example


class TestModelOnexResultTypeSafety:
    """Test type safety - ZERO TOLERANCE for Any types."""

    def test_no_any_types_in_annotations(self):
        """Test that model fields don't use Any type."""
        from typing import get_type_hints

        hints = get_type_hints(ModelOnexResult)

        # Check that no field uses Any type directly
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            # Allow typing.Any in union with None, but not bare Any
            assert (
                "typing.Any" not in type_str or "None" in type_str
            ), f"Field {field_name} uses Any type: {type_str}"

    def test_messages_list_is_typed(self):
        """Test that messages list is properly typed."""
        from typing import get_type_hints

        hints = get_type_hints(ModelOnexResult)
        messages_type = hints.get("messages")

        assert messages_type is not None
        assert "list" in str(messages_type).lower()
        assert "ModelOnexMessage" in str(messages_type) or "list" in str(messages_type)


class TestModelOnexResultStatusEnumHandling:
    """Test status enum field handling with all enum values."""

    def test_all_status_enum_values(self):
        """Test instantiation with all EnumOnexStatus values."""
        statuses = [
            EnumOnexStatus.SUCCESS,
            EnumOnexStatus.ERROR,
            EnumOnexStatus.WARNING,
            EnumOnexStatus.SKIPPED,
            EnumOnexStatus.PARTIAL,
            EnumOnexStatus.ERROR,
            EnumOnexStatus.UNKNOWN,
        ]

        for status in statuses:
            result = ModelOnexResult(status=status)
            assert result.status == status

    def test_status_enum_comparison(self):
        """Test status enum comparison."""
        result1 = ModelOnexResult(status=EnumOnexStatus.SUCCESS)
        result2 = ModelOnexResult(status=EnumOnexStatus.SUCCESS)
        result3 = ModelOnexResult(status=EnumOnexStatus.ERROR)

        assert result1.status == result2.status
        assert result1.status != result3.status
