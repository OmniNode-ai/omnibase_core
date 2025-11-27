"""Tests for ModelLogFormatting."""

from omnibase_core.models.configuration.model_log_formatting import ModelLogFormatting


class TestModelLogFormattingBasics:
    def test_create_default(self):
        fmt = ModelLogFormatting()
        assert fmt.format_type == "text"
        assert fmt.include_timestamp is True
        assert fmt.include_level is True

    def test_format_type_validation(self):
        for ftype in ["text", "json", "structured", "custom"]:
            fmt = ModelLogFormatting(format_type=ftype)
            assert fmt.format_type == ftype


class TestModelLogFormattingMethods:
    def test_format_message_text(self):
        fmt = ModelLogFormatting(format_type="text")
        message = fmt.format_message("ERROR", "test_logger", "Test message")
        assert isinstance(message, str)
        assert "Test message" in message

    def test_format_message_json(self):
        fmt = ModelLogFormatting(format_type="json")
        message = fmt.format_message("ERROR", "test_logger", "Test message")
        assert isinstance(message, str)
        import json

        data = json.loads(message)
        assert data["message"] == "Test message"

    def test_format_message_structured(self):
        fmt = ModelLogFormatting(format_type="structured")
        message = fmt.format_message("ERROR", "test_logger", "Test message")
        assert isinstance(message, str)
        assert 'message="Test message"' in message

    def test_apply_truncation(self):
        fmt = ModelLogFormatting(truncate_long_messages=True, max_message_length=100)
        message = "A" * 200  # Create a message longer than max
        truncated = fmt._apply_truncation(message)
        assert len(truncated) == 100
        assert truncated.endswith("...")

    def test_no_truncation_when_disabled(self):
        fmt = ModelLogFormatting(truncate_long_messages=False)
        message = "This is a message"
        assert fmt._apply_truncation(message) == message

    def test_effective_json_indent(self):
        fmt = ModelLogFormatting(json_indent=4)
        assert fmt.effective_json_indent == 4

    def test_format_analysis(self):
        fmt = ModelLogFormatting()
        analysis = fmt.format_analysis
        assert isinstance(analysis, dict)
        assert "format_type" in analysis
        assert "format_checks" in analysis


class TestModelLogFormattingCustomization:
    def test_field_order_customization(self):
        fmt = ModelLogFormatting(field_order=["level", "timestamp", "message"])
        assert fmt.field_order == ["level", "timestamp", "message"]

    def test_field_separator_customization(self):
        fmt = ModelLogFormatting(field_separator=" - ")
        assert fmt.field_separator == " - "

    def test_timestamp_format_customization(self):
        fmt = ModelLogFormatting(timestamp_format="%Y-%m-%d")
        assert fmt.timestamp_format == "%Y-%m-%d"


class TestModelLogFormattingSerialization:
    def test_serialization(self):
        fmt = ModelLogFormatting(format_type="json")
        data = fmt.model_dump()
        assert data["format_type"] == "json"

    def test_roundtrip(self):
        original = ModelLogFormatting(format_type="json", json_indent=2)
        data = original.model_dump()
        restored = ModelLogFormatting.model_validate(data)
        assert restored.format_type == original.format_type
        assert restored.json_indent == original.json_indent
