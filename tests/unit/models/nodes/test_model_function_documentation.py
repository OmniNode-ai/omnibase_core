"""
Unit tests for ModelFunctionDocumentation.

Tests all aspects of the function documentation model including:
- Model instantiation and validation
- Documentation content management
- Examples and notes handling
- Quality scoring
- Summary generation
- Factory methods
- Protocol implementations
"""

import pytest

from omnibase_core.models.nodes.model_function_documentation import (
    ModelFunctionDocumentation,
)


class TestModelFunctionDocumentation:
    """Test cases for ModelFunctionDocumentation."""

    def test_model_instantiation_default(self):
        """Test that model can be instantiated with defaults."""
        doc = ModelFunctionDocumentation()

        assert doc.docstring is None
        assert doc.examples == []
        assert doc.notes == []

    def test_model_instantiation_with_data(self):
        """Test model instantiation with data."""
        doc = ModelFunctionDocumentation(
            docstring="Test docstring",
            examples=["example1", "example2"],
            notes=["note1", "note2"],
        )

        assert doc.docstring == "Test docstring"
        assert doc.examples == ["example1", "example2"]
        assert doc.notes == ["note1", "note2"]

    def test_has_documentation_true(self):
        """Test has_documentation returns True when docstring exists."""
        doc = ModelFunctionDocumentation(docstring="Test documentation")
        assert doc.has_documentation() is True

    def test_has_documentation_false_none(self):
        """Test has_documentation returns False when None."""
        doc = ModelFunctionDocumentation()
        assert doc.has_documentation() is False

    def test_has_documentation_false_empty(self):
        """Test has_documentation returns False when empty string."""
        doc = ModelFunctionDocumentation(docstring="")
        assert doc.has_documentation() is False

    def test_has_documentation_false_whitespace(self):
        """Test has_documentation returns False when only whitespace."""
        doc = ModelFunctionDocumentation(docstring="   ")
        assert doc.has_documentation() is False

    def test_has_examples_true(self):
        """Test has_examples returns True when examples exist."""
        doc = ModelFunctionDocumentation(examples=["example1"])
        assert doc.has_examples() is True

    def test_has_examples_false(self):
        """Test has_examples returns False when no examples."""
        doc = ModelFunctionDocumentation()
        assert doc.has_examples() is False

    def test_has_notes_true(self):
        """Test has_notes returns True when notes exist."""
        doc = ModelFunctionDocumentation(notes=["note1"])
        assert doc.has_notes() is True

    def test_has_notes_false(self):
        """Test has_notes returns False when no notes."""
        doc = ModelFunctionDocumentation()
        assert doc.has_notes() is False

    def test_add_example(self):
        """Test add_example method."""
        doc = ModelFunctionDocumentation()

        doc.add_example("example1")
        assert "example1" in doc.examples
        assert len(doc.examples) == 1

    def test_add_example_no_duplicate(self):
        """Test add_example doesn't add duplicates."""
        doc = ModelFunctionDocumentation(examples=["example1"])

        doc.add_example("example1")
        assert doc.examples.count("example1") == 1

    def test_add_multiple_examples(self):
        """Test adding multiple examples."""
        doc = ModelFunctionDocumentation()

        doc.add_example("example1")
        doc.add_example("example2")
        doc.add_example("example3")

        assert len(doc.examples) == 3

    def test_add_note(self):
        """Test add_note method."""
        doc = ModelFunctionDocumentation()

        doc.add_note("note1")
        assert "note1" in doc.notes
        assert len(doc.notes) == 1

    def test_add_note_no_duplicate(self):
        """Test add_note doesn't add duplicates."""
        doc = ModelFunctionDocumentation(notes=["note1"])

        doc.add_note("note1")
        assert doc.notes.count("note1") == 1

    def test_add_multiple_notes(self):
        """Test adding multiple notes."""
        doc = ModelFunctionDocumentation()

        doc.add_note("note1")
        doc.add_note("note2")
        doc.add_note("note3")

        assert len(doc.notes) == 3

    def test_get_documentation_quality_score_none(self):
        """Test quality score with no documentation."""
        doc = ModelFunctionDocumentation()

        score = doc.get_documentation_quality_score()
        assert score == 0.0

    def test_get_documentation_quality_score_only_docstring(self):
        """Test quality score with only docstring."""
        doc = ModelFunctionDocumentation(docstring="Test docstring")

        score = doc.get_documentation_quality_score()
        assert score == 0.5

    def test_get_documentation_quality_score_docstring_and_examples(self):
        """Test quality score with docstring and examples."""
        doc = ModelFunctionDocumentation(
            docstring="Test docstring",
            examples=["example1"],
        )

        score = doc.get_documentation_quality_score()
        assert score == 0.8

    def test_get_documentation_quality_score_complete(self):
        """Test quality score with complete documentation."""
        doc = ModelFunctionDocumentation(
            docstring="Test docstring",
            examples=["example1"],
            notes=["note1"],
        )

        score = doc.get_documentation_quality_score()
        assert score == 1.0

    def test_get_documentation_quality_score_capped_at_one(self):
        """Test quality score is capped at 1.0."""
        doc = ModelFunctionDocumentation(
            docstring="Test docstring",
            examples=["example1"],
            notes=["note1"],
        )

        score = doc.get_documentation_quality_score()
        assert score <= 1.0

    def test_get_documentation_summary(self):
        """Test get_documentation_summary method."""
        doc = ModelFunctionDocumentation(
            docstring="Test docstring",
            examples=["example1", "example2"],
            notes=["note1"],
        )

        summary = doc.get_documentation_summary()

        assert summary["has_documentation"] is True
        assert summary["has_examples"] is True
        assert summary["has_notes"] is True
        assert summary["examples_count"] == 2
        assert summary["notes_count"] == 1
        assert summary["quality_score"] == 1.0

    def test_get_documentation_summary_empty(self):
        """Test get_documentation_summary with empty documentation."""
        doc = ModelFunctionDocumentation()

        summary = doc.get_documentation_summary()

        assert summary["has_documentation"] is False
        assert summary["has_examples"] is False
        assert summary["has_notes"] is False
        assert summary["examples_count"] == 0
        assert summary["notes_count"] == 0
        assert summary["quality_score"] == 0.0

    def test_create_documented_factory(self):
        """Test create_documented factory method."""
        doc = ModelFunctionDocumentation.create_documented(
            docstring="Test docstring",
            examples=["example1", "example2"],
        )

        assert doc.docstring == "Test docstring"
        assert doc.examples == ["example1", "example2"]

    def test_create_documented_factory_no_examples(self):
        """Test create_documented without examples."""
        doc = ModelFunctionDocumentation.create_documented(
            docstring="Test docstring",
        )

        assert doc.docstring == "Test docstring"
        assert doc.examples == []

    def test_create_with_examples_factory(self):
        """Test create_with_examples factory method."""
        doc = ModelFunctionDocumentation.create_with_examples(
            examples=["example1", "example2", "example3"],
        )

        assert doc.examples == ["example1", "example2", "example3"]
        assert doc.docstring is None

    def test_get_id_protocol(self):
        """Test get_id protocol method raises OnexError without ID field."""
        from omnibase_core.exceptions.onex_error import OnexError

        doc = ModelFunctionDocumentation()

        with pytest.raises(OnexError) as exc_info:
            doc.get_id()

        assert "must have a valid ID field" in str(exc_info.value)

    def test_get_metadata_protocol(self):
        """Test get_metadata protocol method."""
        doc = ModelFunctionDocumentation()

        metadata = doc.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata_protocol(self):
        """Test set_metadata protocol method."""
        doc = ModelFunctionDocumentation()

        result = doc.set_metadata({"docstring": "New docstring"})
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        doc = ModelFunctionDocumentation(docstring="Test docstring")

        serialized = doc.serialize()
        assert isinstance(serialized, dict)
        assert "docstring" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        doc = ModelFunctionDocumentation()

        assert doc.validate_instance() is True

    def test_model_config_extra_ignore(self):
        """Test that model ignores extra fields."""
        # Should not raise error with extra fields
        doc = ModelFunctionDocumentation(
            docstring="Test",
            extra_field="ignored",
        )
        assert doc.docstring == "Test"

    def test_model_config_validate_assignment(self):
        """Test that model validates on assignment."""
        doc = ModelFunctionDocumentation()

        # Should validate new assignments
        doc.docstring = "New docstring"
        assert doc.docstring == "New docstring"

    def test_examples_list_mutation(self):
        """Test that examples list can be modified."""
        doc = ModelFunctionDocumentation()

        doc.examples.append("example1")
        assert "example1" in doc.examples

    def test_notes_list_mutation(self):
        """Test that notes list can be modified."""
        doc = ModelFunctionDocumentation()

        doc.notes.append("note1")
        assert "note1" in doc.notes
