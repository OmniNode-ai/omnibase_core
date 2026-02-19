# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelServiceBaseProcessor abstract base class.

Validates abstract processor pattern functionality including
process and can_process methods, following ONEX testing patterns.
"""

import pytest

from omnibase_core.models.base.model_processor import ModelServiceBaseProcessor


@pytest.mark.unit
class TestModelServiceBaseProcessor:
    """Test abstract base processor functionality."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            ModelServiceBaseProcessor()

        assert "abstract" in str(exc_info.value).lower()

    def test_concrete_implementation_with_both_methods(self):
        """Test concrete implementation with both abstract methods."""

        class StringUpperProcessor(ModelServiceBaseProcessor):
            """Concrete processor that converts strings to uppercase."""

            def process(self, input_data: object) -> object:
                """Process input data by converting to uppercase."""
                if isinstance(input_data, str):
                    return input_data.upper()
                return input_data

            def can_process(self, input_data: object) -> bool:
                """Check if input is a string."""
                return isinstance(input_data, str)

        # Should be able to instantiate concrete class
        processor = StringUpperProcessor()
        assert processor is not None

    def test_concrete_processor_process_method(self):
        """Test process method in concrete implementation."""

        class IntegerDoubler(ModelServiceBaseProcessor):
            """Processor that doubles integers."""

            def process(self, input_data: object) -> object:
                """Double the integer value."""
                if isinstance(input_data, int):
                    return input_data * 2
                return input_data

            def can_process(self, input_data: object) -> bool:
                """Check if input is an integer."""
                return isinstance(input_data, int)

        processor = IntegerDoubler()
        result = processor.process(21)
        assert result == 42

    def test_concrete_processor_can_process_method(self):
        """Test can_process method in concrete implementation."""

        class ListProcessor(ModelServiceBaseProcessor):
            """Processor for lists only."""

            def process(self, input_data: object) -> object:
                """Process list data."""
                if isinstance(input_data, list):
                    return sorted(input_data)
                return input_data

            def can_process(self, input_data: object) -> bool:
                """Check if input is a list."""
                return isinstance(input_data, list)

        processor = ListProcessor()
        assert processor.can_process([1, 2, 3]) is True
        assert processor.can_process("not a list") is False
        assert processor.can_process(123) is False
        assert processor.can_process({"key": "value"}) is False

    def test_missing_process_method_fails(self):
        """Test that missing process method prevents instantiation."""
        with pytest.raises(TypeError) as exc_info:

            class IncompleteProcessor(ModelServiceBaseProcessor):
                """Processor missing process method."""

                def can_process(self, input_data: object) -> bool:
                    """Check if can process."""
                    return True

            IncompleteProcessor()

        assert "abstract" in str(exc_info.value).lower()

    def test_missing_can_process_method_fails(self):
        """Test that missing can_process method prevents instantiation."""
        with pytest.raises(TypeError) as exc_info:

            class IncompleteProcessor(ModelServiceBaseProcessor):
                """Processor missing can_process method."""

                def process(self, input_data: object) -> object:
                    """Process data."""
                    return input_data

            IncompleteProcessor()

        assert "abstract" in str(exc_info.value).lower()

    def test_processor_with_pydantic_validation(self):
        """Test that processor benefits from Pydantic BaseModel."""

        class ConfigurableProcessor(ModelServiceBaseProcessor):
            """Processor with configurable parameters."""

            multiplier: int = 1

            def process(self, input_data: object) -> object:
                """Multiply numeric input by multiplier."""
                if isinstance(input_data, (int, float)):
                    return input_data * self.multiplier
                return input_data

            def can_process(self, input_data: object) -> bool:
                """Check if input is numeric."""
                return isinstance(input_data, int | float)

        # Should validate on creation
        processor = ConfigurableProcessor(multiplier=5)
        assert processor.multiplier == 5
        assert processor.process(10) == 50

    def test_processor_model_config_extra_ignore(self):
        """Test that extra fields are ignored per model_config."""

        class SimpleProcessor(ModelServiceBaseProcessor):
            """Simple processor implementation."""

            def process(self, input_data: object) -> object:
                return input_data

            def can_process(self, input_data: object) -> bool:
                return True

        # Extra fields should be ignored
        processor = SimpleProcessor(unknown_field="should_be_ignored")
        assert not hasattr(processor, "unknown_field")

    def test_processor_model_config_validate_assignment(self):
        """Test that assignment validation is enabled."""

        class ValidatedProcessor(ModelServiceBaseProcessor):
            """Processor with validated field."""

            threshold: int = 10

            def process(self, input_data: object) -> object:
                return input_data

            def can_process(self, input_data: object) -> bool:
                return True

        processor = ValidatedProcessor(threshold=20)
        assert processor.threshold == 20

        # Assignment should be validated
        processor.threshold = 30
        assert processor.threshold == 30

    def test_processor_model_config_enum_values(self):
        """Test that enum values are preserved (not converted)."""

        from enum import Enum

        class ProcessMode(str, Enum):
            FAST = "fast"
            ACCURATE = "accurate"

        class EnumProcessor(ModelServiceBaseProcessor):
            """Processor with enum configuration."""

            mode: ProcessMode = ProcessMode.FAST

            def process(self, input_data: object) -> object:
                return input_data

            def can_process(self, input_data: object) -> bool:
                return True

        processor = EnumProcessor(mode=ProcessMode.ACCURATE)
        # Enum should be preserved, not converted to string
        assert processor.mode == ProcessMode.ACCURATE
        assert isinstance(processor.mode, ProcessMode)

    def test_processor_inheritance_chain(self):
        """Test that processors can be further subclassed."""

        class BaseStringProcessor(ModelServiceBaseProcessor):
            """Base processor for string operations."""

            def process(self, input_data: object) -> object:
                """Base string processing."""
                if isinstance(input_data, str):
                    return input_data.strip()
                return input_data

            def can_process(self, input_data: object) -> bool:
                """Check if input is string."""
                return isinstance(input_data, str)

        class UppercaseStringProcessor(BaseStringProcessor):
            """Specialized processor that also uppercases."""

            def process(self, input_data: object) -> object:
                """Strip and uppercase."""
                result = super().process(input_data)
                if isinstance(result, str):
                    return result.upper()
                return result

        processor = UppercaseStringProcessor()
        result = processor.process("  hello world  ")
        assert result == "HELLO WORLD"

    def test_processor_with_complex_data_types(self):
        """Test processor with complex data types."""

        class DictProcessor(ModelServiceBaseProcessor):
            """Processor for dictionary data."""

            def process(self, input_data: object) -> object:
                """Extract specific keys from dict."""
                if isinstance(input_data, dict):
                    return {
                        k: v for k, v in input_data.items() if isinstance(v, (int, str))
                    }
                return input_data

            def can_process(self, input_data: object) -> bool:
                """Check if input is dict."""
                return isinstance(input_data, dict)

        processor = DictProcessor()
        input_dict = {
            "name": "test",
            "count": 42,
            "nested": {"inner": "value"},
            "flag": True,
        }
        result = processor.process(input_dict)

        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["count"] == 42
        assert "nested" not in result  # Should be filtered out

    def test_processor_error_handling(self):
        """Test processor error handling patterns."""

        class SafeProcessor(ModelServiceBaseProcessor):
            """Processor with error handling."""

            def process(self, input_data: object) -> object:
                """Process with error handling."""
                try:
                    if isinstance(input_data, str):
                        return int(input_data)
                    return input_data
                except ValueError as e:
                    return f"Error: {e}"

            def can_process(self, input_data: object) -> bool:
                """Check if input is string."""
                return isinstance(input_data, str)

        processor = SafeProcessor()

        # Valid conversion
        assert processor.process("42") == 42

        # Invalid conversion - error handling
        result = processor.process("not_a_number")
        assert isinstance(result, str)
        assert "Error" in result

    def test_processor_with_state(self):
        """Test processor that maintains state."""

        class StatefulProcessor(ModelServiceBaseProcessor):
            """Processor that tracks processing count."""

            process_count: int = 0

            def process(self, input_data: object) -> object:
                """Process and increment counter."""
                self.process_count += 1
                return input_data

            def can_process(self, input_data: object) -> bool:
                """Always can process."""
                return True

        processor = StatefulProcessor()
        assert processor.process_count == 0

        processor.process("data1")
        assert processor.process_count == 1

        processor.process("data2")
        assert processor.process_count == 2

    def test_processor_serialization(self):
        """Test processor serialization capabilities."""

        class SerializableProcessor(ModelServiceBaseProcessor):
            """Processor with serializable config."""

            threshold: int = 10
            name: str = "default"

            def process(self, input_data: object) -> object:
                return input_data

            def can_process(self, input_data: object) -> bool:
                return True

        processor = SerializableProcessor(threshold=20, name="test_processor")

        # Should be serializable as Pydantic model
        serialized = processor.model_dump()
        assert serialized["threshold"] == 20
        assert serialized["name"] == "test_processor"

        # Should be deserializable
        restored = SerializableProcessor.model_validate(serialized)
        assert restored.threshold == 20
        assert restored.name == "test_processor"
