# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelToolExecutionContent (OMN-1701).

Tests comprehensive model functionality including:
- Required field validation (tool_name_raw, tool_name)
- Field constraints (max_length on content_preview, error_message)
- Numeric constraints (content_length >= 0, duration_ms >= 0)
- Optional field handling with defaults
- Dual-field pattern (tool_name_raw + tool_name)
- Privacy fields (is_content_redacted, redaction_policy_version)
- Frozen model immutability
- Extra field rejection
- Serialization round-trip
- Import verification

The model is frozen (immutable) and uses extra="forbid".
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.hooks.claude_code import EnumClaudeCodeToolName
from omnibase_core.models.intelligence import ModelToolExecutionContent

pytestmark = pytest.mark.unit


# ============================================================================
# Test: Required Fields
# ============================================================================


class TestModelToolExecutionContentRequiredFields:
    """Tests for required field validation."""

    def test_create_with_required_fields_only(self) -> None:
        """Test creating model with only required fields."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
        )

        assert content.tool_name_raw == "Read"
        assert content.tool_name == EnumClaudeCodeToolName.READ
        # Check optional defaults
        assert content.file_path is None
        assert content.language is None
        assert content.content_preview is None
        assert content.content_length is None
        assert content.content_hash is None
        assert content.is_content_redacted is False
        assert content.redaction_policy_version is None
        assert content.success is True
        assert content.error_type is None
        assert content.error_message is None
        assert content.duration_ms is None
        assert content.session_id is None
        assert content.correlation_id is None
        assert content.timestamp is None

    def test_tool_name_raw_is_required(self) -> None:
        """Test that tool_name_raw is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionContent(
                tool_name=EnumClaudeCodeToolName.READ,
            )  # type: ignore[call-arg]

        assert "tool_name_raw" in str(exc_info.value)

    def test_tool_name_is_required(self) -> None:
        """Test that tool_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionContent(
                tool_name_raw="Read",
            )  # type: ignore[call-arg]

        assert "tool_name" in str(exc_info.value)

    def test_tool_name_raw_min_length(self) -> None:
        """Test that tool_name_raw requires min length of 1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionContent(
                tool_name_raw="",
                tool_name=EnumClaudeCodeToolName.READ,
            )

        assert "tool_name_raw" in str(exc_info.value)


# ============================================================================
# Test: Field Validation - String Constraints
# ============================================================================


class TestModelToolExecutionContentStringConstraints:
    """Tests for string field constraints."""

    def test_content_preview_max_length_valid(self) -> None:
        """Test content_preview accepts up to 2000 characters."""
        long_content = "x" * 2000
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            content_preview=long_content,
        )
        assert len(content.content_preview or "") == 2000

    def test_content_preview_max_length_exceeded(self) -> None:
        """Test content_preview rejects more than 2000 characters."""
        too_long = "x" * 2001
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionContent(
                tool_name_raw="Read",
                tool_name=EnumClaudeCodeToolName.READ,
                content_preview=too_long,
            )

        assert "content_preview" in str(exc_info.value)

    def test_error_message_max_length_valid(self) -> None:
        """Test error_message accepts up to 500 characters."""
        long_error = "e" * 500
        content = ModelToolExecutionContent(
            tool_name_raw="Bash",
            tool_name=EnumClaudeCodeToolName.BASH,
            success=False,
            error_message=long_error,
        )
        assert len(content.error_message or "") == 500

    def test_error_message_max_length_exceeded(self) -> None:
        """Test error_message rejects more than 500 characters."""
        too_long = "e" * 501
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionContent(
                tool_name_raw="Bash",
                tool_name=EnumClaudeCodeToolName.BASH,
                success=False,
                error_message=too_long,
            )

        assert "error_message" in str(exc_info.value)


# ============================================================================
# Test: Field Validation - Numeric Constraints
# ============================================================================


class TestModelToolExecutionContentNumericConstraints:
    """Tests for numeric field constraints."""

    def test_content_length_valid_at_zero(self) -> None:
        """Test content_length at minimum value (0)."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            content_length=0,
        )
        assert content.content_length == 0

    def test_content_length_valid_large_value(self) -> None:
        """Test content_length with large positive value."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            content_length=1000000,
        )
        assert content.content_length == 1000000

    def test_content_length_invalid_negative(self) -> None:
        """Test content_length rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionContent(
                tool_name_raw="Read",
                tool_name=EnumClaudeCodeToolName.READ,
                content_length=-1,
            )

        assert "content_length" in str(exc_info.value)

    def test_duration_ms_valid_at_zero(self) -> None:
        """Test duration_ms at minimum value (0)."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            duration_ms=0.0,
        )
        assert content.duration_ms == 0.0

    def test_duration_ms_valid_positive(self) -> None:
        """Test duration_ms with positive value."""
        content = ModelToolExecutionContent(
            tool_name_raw="Bash",
            tool_name=EnumClaudeCodeToolName.BASH,
            duration_ms=150.5,
        )
        assert content.duration_ms == 150.5

    def test_duration_ms_invalid_negative(self) -> None:
        """Test duration_ms rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionContent(
                tool_name_raw="Bash",
                tool_name=EnumClaudeCodeToolName.BASH,
                duration_ms=-1.0,
            )

        assert "duration_ms" in str(exc_info.value)


# ============================================================================
# Test: Optional Fields
# ============================================================================


class TestModelToolExecutionContentOptionalFields:
    """Tests for optional field handling."""

    def test_create_with_all_fields(self) -> None:
        """Test creating model with all fields populated."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        content = ModelToolExecutionContent(
            tool_name_raw="Write",
            tool_name=EnumClaudeCodeToolName.WRITE,
            file_path="/home/user/test.py",
            language="python",
            content_preview="def main(): pass",
            content_length=16,
            content_hash="abc123hash",
            is_content_redacted=False,
            redaction_policy_version=None,
            success=True,
            error_type=None,
            error_message=None,
            duration_ms=42.5,
            session_id="sess-123",
            correlation_id="corr-456",
            timestamp=timestamp,
        )

        assert content.tool_name_raw == "Write"
        assert content.tool_name == EnumClaudeCodeToolName.WRITE
        assert content.file_path == "/home/user/test.py"
        assert content.language == "python"
        assert content.content_preview == "def main(): pass"
        assert content.content_length == 16
        assert content.content_hash == "abc123hash"
        assert content.is_content_redacted is False
        assert content.redaction_policy_version is None
        assert content.success is True
        assert content.error_type is None
        assert content.error_message is None
        assert content.duration_ms == 42.5
        assert content.session_id == "sess-123"
        assert content.correlation_id == "corr-456"
        assert content.timestamp == timestamp

    def test_all_optional_fields_accept_none(self) -> None:
        """Test that all optional fields accept None."""
        content = ModelToolExecutionContent(
            tool_name_raw="Bash",
            tool_name=EnumClaudeCodeToolName.BASH,
            file_path=None,
            language=None,
            content_preview=None,
            content_length=None,
            content_hash=None,
            redaction_policy_version=None,
            error_type=None,
            error_message=None,
            duration_ms=None,
            session_id=None,
            correlation_id=None,
            timestamp=None,
        )

        assert content.file_path is None
        assert content.language is None
        assert content.content_preview is None
        assert content.content_length is None
        assert content.content_hash is None
        assert content.redaction_policy_version is None
        assert content.error_type is None
        assert content.error_message is None
        assert content.duration_ms is None
        assert content.session_id is None
        assert content.correlation_id is None
        assert content.timestamp is None


# ============================================================================
# Test: Dual-Field Pattern
# ============================================================================


class TestModelToolExecutionContentDualFieldPattern:
    """Tests for dual-field pattern (tool_name_raw + tool_name)."""

    def test_known_tool_dual_field(self) -> None:
        """Test dual-field pattern with known tool."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
        )
        assert content.tool_name_raw == "Read"
        assert content.tool_name == EnumClaudeCodeToolName.READ

    def test_unknown_tool_dual_field(self) -> None:
        """Test dual-field pattern with unknown tool name."""
        content = ModelToolExecutionContent(
            tool_name_raw="SomeFutureTool",
            tool_name=EnumClaudeCodeToolName.UNKNOWN,
        )
        # Raw name is preserved
        assert content.tool_name_raw == "SomeFutureTool"
        # Enum is UNKNOWN
        assert content.tool_name == EnumClaudeCodeToolName.UNKNOWN

    def test_mcp_tool_dual_field(self) -> None:
        """Test dual-field pattern with MCP tool."""
        content = ModelToolExecutionContent(
            tool_name_raw="mcp__linear-server__list_issues",
            tool_name=EnumClaudeCodeToolName.MCP,
        )
        # Raw name preserves full MCP tool identifier
        assert content.tool_name_raw == "mcp__linear-server__list_issues"
        # Enum is MCP category
        assert content.tool_name == EnumClaudeCodeToolName.MCP

    def test_dual_field_mismatch_allowed(self) -> None:
        """Test that mismatched raw/enum values are allowed (no validation link)."""
        # This is intentionally allowed for flexibility
        content = ModelToolExecutionContent(
            tool_name_raw="Write",
            tool_name=EnumClaudeCodeToolName.READ,  # Intentionally wrong
        )
        assert content.tool_name_raw == "Write"
        assert content.tool_name == EnumClaudeCodeToolName.READ


# ============================================================================
# Test: Privacy Fields
# ============================================================================


class TestModelToolExecutionContentPrivacyFields:
    """Tests for privacy/redaction fields."""

    def test_is_content_redacted_defaults_to_false(self) -> None:
        """Test is_content_redacted defaults to False."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
        )
        assert content.is_content_redacted is False

    def test_redacted_content(self) -> None:
        """Test redacted content with policy version."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            content_preview="[REDACTED]",
            is_content_redacted=True,
            redaction_policy_version="1.0.0",
        )
        assert content.content_preview == "[REDACTED]"
        assert content.is_content_redacted is True
        assert content.redaction_policy_version == "1.0.0"

    def test_redaction_policy_version_optional(self) -> None:
        """Test redaction_policy_version is optional."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            is_content_redacted=True,
            redaction_policy_version=None,
        )
        assert content.is_content_redacted is True
        assert content.redaction_policy_version is None


# ============================================================================
# Test: Execution Metadata
# ============================================================================


class TestModelToolExecutionContentExecutionMetadata:
    """Tests for execution metadata fields."""

    def test_success_defaults_to_true(self) -> None:
        """Test success field defaults to True."""
        content = ModelToolExecutionContent(
            tool_name_raw="Bash",
            tool_name=EnumClaudeCodeToolName.BASH,
        )
        assert content.success is True

    def test_failed_execution_with_error_details(self) -> None:
        """Test failed execution with error details."""
        content = ModelToolExecutionContent(
            tool_name_raw="Bash",
            tool_name=EnumClaudeCodeToolName.BASH,
            success=False,
            error_type="TimeoutError",
            error_message="Command timed out after 30 seconds",
        )
        assert content.success is False
        assert content.error_type == "TimeoutError"
        assert content.error_message == "Command timed out after 30 seconds"


# ============================================================================
# Test: Frozen Immutability
# ============================================================================


class TestModelToolExecutionContentFrozenImmutability:
    """Tests for frozen model immutability."""

    def test_frozen_immutability_tool_name_raw(self) -> None:
        """Test that tool_name_raw cannot be modified."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
        )

        with pytest.raises(ValidationError):
            content.tool_name_raw = "Write"

    def test_frozen_immutability_tool_name(self) -> None:
        """Test that tool_name cannot be modified."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
        )

        with pytest.raises(ValidationError):
            content.tool_name = EnumClaudeCodeToolName.WRITE

    def test_frozen_immutability_file_path(self) -> None:
        """Test that file_path cannot be modified."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            file_path="/original/path.py",
        )

        with pytest.raises(ValidationError):
            content.file_path = "/new/path.py"

    def test_frozen_immutability_success(self) -> None:
        """Test that success cannot be modified."""
        content = ModelToolExecutionContent(
            tool_name_raw="Bash",
            tool_name=EnumClaudeCodeToolName.BASH,
            success=True,
        )

        with pytest.raises(ValidationError):
            content.success = False


# ============================================================================
# Test: Extra Fields Forbidden
# ============================================================================


class TestModelToolExecutionContentExtraFieldsForbidden:
    """Tests for extra field rejection."""

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionContent(
                tool_name_raw="Read",
                tool_name=EnumClaudeCodeToolName.READ,
                unknown_field="bad",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)

    def test_multiple_extra_fields_forbidden(self) -> None:
        """Test that multiple extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelToolExecutionContent(  # type: ignore[call-arg]
                tool_name_raw="Read",
                tool_name=EnumClaudeCodeToolName.READ,
                extra1="bad",
                extra2=123,
            )

        error_str = str(exc_info.value)
        assert "extra1" in error_str or "extra2" in error_str


# ============================================================================
# Test: Serialization Round-Trip
# ============================================================================


class TestModelToolExecutionContentSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump_round_trip(self) -> None:
        """Test model_dump and model_validate round-trip."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        original = ModelToolExecutionContent(
            tool_name_raw="Write",
            tool_name=EnumClaudeCodeToolName.WRITE,
            file_path="/home/user/test.py",
            language="python",
            content_preview="def main(): pass",
            content_length=16,
            content_hash="abc123",
            is_content_redacted=False,
            success=True,
            duration_ms=25.5,
            session_id="sess-123",
            correlation_id="corr-456",
            timestamp=timestamp,
        )

        data = original.model_dump()
        restored = ModelToolExecutionContent.model_validate(data)

        assert original.tool_name_raw == restored.tool_name_raw
        assert original.tool_name == restored.tool_name
        assert original.file_path == restored.file_path
        assert original.language == restored.language
        assert original.content_preview == restored.content_preview
        assert original.content_length == restored.content_length
        assert original.content_hash == restored.content_hash
        assert original.is_content_redacted == restored.is_content_redacted
        assert original.success == restored.success
        assert original.duration_ms == restored.duration_ms
        assert original.session_id == restored.session_id
        assert original.correlation_id == restored.correlation_id
        assert original.timestamp == restored.timestamp

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round-trip."""
        original = ModelToolExecutionContent(
            tool_name_raw="Bash",
            tool_name=EnumClaudeCodeToolName.BASH,
            content_preview="echo hello",
            duration_ms=100.0,
        )

        json_str = original.model_dump_json()
        restored = ModelToolExecutionContent.model_validate_json(json_str)

        assert original.tool_name_raw == restored.tool_name_raw
        assert original.tool_name == restored.tool_name
        assert original.content_preview == restored.content_preview
        assert original.duration_ms == restored.duration_ms

    def test_model_dump_with_defaults(self) -> None:
        """Test that model_dump includes default values."""
        content = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
        )

        data = content.model_dump()

        assert data["tool_name_raw"] == "Read"
        assert data["tool_name"] == EnumClaudeCodeToolName.READ
        assert data["is_content_redacted"] is False
        assert data["success"] is True
        assert data["file_path"] is None


# ============================================================================
# Test: Model Equality
# ============================================================================


class TestModelToolExecutionContentEquality:
    """Tests for model equality comparisons."""

    def test_equality_same_values(self) -> None:
        """Test equality for models with same values."""
        c1 = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            file_path="/path/file.py",
        )
        c2 = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            file_path="/path/file.py",
        )

        assert c1 == c2

    def test_inequality_different_tool_name(self) -> None:
        """Test inequality for models with different tool names."""
        c1 = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
        )
        c2 = ModelToolExecutionContent(
            tool_name_raw="Write",
            tool_name=EnumClaudeCodeToolName.WRITE,
        )

        assert c1 != c2

    def test_inequality_different_file_path(self) -> None:
        """Test inequality for models with different file paths."""
        c1 = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            file_path="/path/a.py",
        )
        c2 = ModelToolExecutionContent(
            tool_name_raw="Read",
            tool_name=EnumClaudeCodeToolName.READ,
            file_path="/path/b.py",
        )

        assert c1 != c2


# ============================================================================
# Test: from_tool_name() Factory Method
# ============================================================================


class TestModelToolExecutionContentFromToolName:
    """Tests for from_tool_name() factory method.

    The factory method prevents dual-field mismatches by auto-resolving
    the enum from the raw tool name string.
    """

    def test_from_tool_name_known_tool(self) -> None:
        """Test factory method with known tool name."""
        content = ModelToolExecutionContent.from_tool_name("Read")

        assert content.tool_name_raw == "Read"
        assert content.tool_name == EnumClaudeCodeToolName.READ

    def test_from_tool_name_unknown_tool(self) -> None:
        """Test factory method with unknown tool name."""
        content = ModelToolExecutionContent.from_tool_name("SomeFutureTool")

        assert content.tool_name_raw == "SomeFutureTool"
        assert content.tool_name == EnumClaudeCodeToolName.UNKNOWN

    def test_from_tool_name_mcp_tool(self) -> None:
        """Test factory method with MCP tool name (mcp__server__method pattern)."""
        content = ModelToolExecutionContent.from_tool_name(
            "mcp__linear-server__list_issues"
        )

        assert content.tool_name_raw == "mcp__linear-server__list_issues"
        assert content.tool_name == EnumClaudeCodeToolName.MCP

    def test_from_tool_name_with_optional_fields(self) -> None:
        """Test factory method with optional kwargs."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        content = ModelToolExecutionContent.from_tool_name(
            "Write",
            file_path="/home/user/test.py",
            language="python",
            content_preview="def main(): pass",
            content_length=16,
            content_hash="abc123hash",
            is_content_redacted=False,
            success=True,
            duration_ms=42.5,
            session_id="sess-123",
            correlation_id="corr-456",
            timestamp=timestamp,
        )

        # Required fields set correctly
        assert content.tool_name_raw == "Write"
        assert content.tool_name == EnumClaudeCodeToolName.WRITE

        # Optional fields passed through
        assert content.file_path == "/home/user/test.py"
        assert content.language == "python"
        assert content.content_preview == "def main(): pass"
        assert content.content_length == 16
        assert content.content_hash == "abc123hash"
        assert content.is_content_redacted is False
        assert content.success is True
        assert content.duration_ms == 42.5
        assert content.session_id == "sess-123"
        assert content.correlation_id == "corr-456"
        assert content.timestamp == timestamp

    def test_from_tool_name_preserves_raw_string(self) -> None:
        """Test that raw string is preserved exactly as provided."""
        # Test with various casing and characters
        test_cases = [
            "Read",
            "mcp__linear-server__list_issues",
            "SomeFutureTool_v2",
            "tool-with-dashes",
            "ALLCAPS",
        ]

        for raw_name in test_cases:
            content = ModelToolExecutionContent.from_tool_name(raw_name)
            assert content.tool_name_raw == raw_name, (
                f"Raw string not preserved for {raw_name}"
            )

    def test_from_tool_name_auto_resolves_enum(self) -> None:
        """Test that enum is auto-resolved correctly for various tools."""
        # Known tools should resolve to their enum values
        known_tools = [
            ("Read", EnumClaudeCodeToolName.READ),
            ("Write", EnumClaudeCodeToolName.WRITE),
            ("Edit", EnumClaudeCodeToolName.EDIT),
            ("Bash", EnumClaudeCodeToolName.BASH),
            ("Glob", EnumClaudeCodeToolName.GLOB),
            ("Grep", EnumClaudeCodeToolName.GREP),
            ("WebFetch", EnumClaudeCodeToolName.WEB_FETCH),
            ("WebSearch", EnumClaudeCodeToolName.WEB_SEARCH),
            ("TaskCreate", EnumClaudeCodeToolName.TASK_CREATE),
            ("Skill", EnumClaudeCodeToolName.SKILL),
        ]

        for raw_name, expected_enum in known_tools:
            content = ModelToolExecutionContent.from_tool_name(raw_name)
            assert content.tool_name == expected_enum, (
                f"Expected {expected_enum} for {raw_name}, got {content.tool_name}"
            )

    def test_from_tool_name_returns_frozen_instance(self) -> None:
        """Test that factory method returns immutable (frozen) instance."""
        content = ModelToolExecutionContent.from_tool_name("Read")

        # Attempting to modify should raise ValidationError
        with pytest.raises(ValidationError):
            content.tool_name_raw = "Write"

        with pytest.raises(ValidationError):
            content.tool_name = EnumClaudeCodeToolName.WRITE

        with pytest.raises(ValidationError):
            content.file_path = "/some/path.py"

    def test_from_tool_name_mcp_various_patterns(self) -> None:
        """Test MCP tool pattern matching with various server/method combinations."""
        mcp_tools = [
            "mcp__linear-server__list_issues",
            "mcp__github__create_pr",
            "mcp__slack__send_message",
            "mcp__custom-server__custom_method",
        ]

        for mcp_tool in mcp_tools:
            content = ModelToolExecutionContent.from_tool_name(mcp_tool)
            assert content.tool_name == EnumClaudeCodeToolName.MCP, (
                f"Expected MCP enum for {mcp_tool}"
            )
            assert content.tool_name_raw == mcp_tool

    def test_from_tool_name_case_sensitivity(self) -> None:
        """Test that tool name matching is case-sensitive."""
        # "Read" should match, but "read" or "READ" should not
        content_exact = ModelToolExecutionContent.from_tool_name("Read")
        assert content_exact.tool_name == EnumClaudeCodeToolName.READ

        content_lower = ModelToolExecutionContent.from_tool_name("read")
        assert content_lower.tool_name == EnumClaudeCodeToolName.UNKNOWN
        assert content_lower.tool_name_raw == "read"

        content_upper = ModelToolExecutionContent.from_tool_name("READ")
        assert content_upper.tool_name == EnumClaudeCodeToolName.UNKNOWN
        assert content_upper.tool_name_raw == "READ"

    def test_from_tool_name_with_error_fields(self) -> None:
        """Test factory method with error-related optional fields."""
        content = ModelToolExecutionContent.from_tool_name(
            "Bash",
            success=False,
            error_type="TimeoutError",
            error_message="Command timed out after 30 seconds",
        )

        assert content.tool_name_raw == "Bash"
        assert content.tool_name == EnumClaudeCodeToolName.BASH
        assert content.success is False
        assert content.error_type == "TimeoutError"
        assert content.error_message == "Command timed out after 30 seconds"

    def test_from_tool_name_with_redaction_fields(self) -> None:
        """Test factory method with privacy/redaction fields."""
        content = ModelToolExecutionContent.from_tool_name(
            "Read",
            content_preview="[REDACTED]",
            is_content_redacted=True,
            redaction_policy_version="1.0.0",
        )

        assert content.tool_name_raw == "Read"
        assert content.tool_name == EnumClaudeCodeToolName.READ
        assert content.content_preview == "[REDACTED]"
        assert content.is_content_redacted is True
        assert content.redaction_policy_version == "1.0.0"


# ============================================================================
# Test: Import Verification
# ============================================================================


class TestModelToolExecutionContentImport:
    """Tests for model import from package."""

    def test_import_from_intelligence_module(self) -> None:
        """Test that ModelToolExecutionContent can be imported from intelligence module."""
        from omnibase_core.models.intelligence import (
            ModelToolExecutionContent as Imported,
        )

        assert Imported is ModelToolExecutionContent

    def test_model_in_all(self) -> None:
        """Test that ModelToolExecutionContent is in __all__."""
        from omnibase_core.models import intelligence

        assert "ModelToolExecutionContent" in intelligence.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
