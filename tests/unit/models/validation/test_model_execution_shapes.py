"""
Test suite for execution shape validation models.

Tests ModelExecutionShape, ModelExecutionShapeValidation, and ModelShapeValidationResult.
"""

import pytest

# Module-level pytest marker for all tests in this file
pytestmark = pytest.mark.unit

from pydantic import ValidationError

from omnibase_core.enums.enum_execution_shape import (
    EnumExecutionShape,
    EnumMessageCategory,
)
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.validation.model_execution_shape import ModelExecutionShape
from omnibase_core.models.validation.model_execution_shape_validation import (
    ModelExecutionShapeValidation,
)
from omnibase_core.models.validation.model_shape_validation_result import (
    ModelShapeValidationResult,
)


class TestModelExecutionShapeCreation:
    """Test ModelExecutionShape instantiation and fields."""

    def test_create_with_all_required_fields(self):
        """Test model creation with all required fields."""
        shape = ModelExecutionShape(
            shape=EnumExecutionShape.EVENT_TO_ORCHESTRATOR,
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
            description="Events routed to orchestrators",
        )

        assert shape.shape == EnumExecutionShape.EVENT_TO_ORCHESTRATOR
        assert shape.source_category == EnumMessageCategory.EVENT
        assert shape.target_node_kind == EnumNodeKind.ORCHESTRATOR
        assert shape.description == "Events routed to orchestrators"

    def test_create_with_default_description(self):
        """Test model creation uses empty string for description by default."""
        shape = ModelExecutionShape(
            shape=EnumExecutionShape.INTENT_TO_EFFECT,
            source_category=EnumMessageCategory.INTENT,
            target_node_kind=EnumNodeKind.EFFECT,
        )

        assert shape.description == ""

    def test_create_missing_required_field_raises_error(self):
        """Test model creation fails when required fields are missing."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionShape(
                shape=EnumExecutionShape.EVENT_TO_ORCHESTRATOR,
                source_category=EnumMessageCategory.EVENT,
                # missing target_node_kind
            )

        assert "target_node_kind" in str(exc_info.value)


class TestModelExecutionShapeModelConfig:
    """Test ModelExecutionShape model configuration."""

    def test_model_is_frozen(self):
        """Test model is immutable (frozen=True)."""
        shape = ModelExecutionShape(
            shape=EnumExecutionShape.EVENT_TO_ORCHESTRATOR,
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )

        with pytest.raises(ValidationError):
            shape.shape = EnumExecutionShape.INTENT_TO_EFFECT

    def test_extra_fields_forbidden(self):
        """Test extra fields are forbidden (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionShape(
                shape=EnumExecutionShape.EVENT_TO_ORCHESTRATOR,
                source_category=EnumMessageCategory.EVENT,
                target_node_kind=EnumNodeKind.ORCHESTRATOR,
                extra_field="not_allowed",
            )

        assert "extra_field" in str(exc_info.value)


class TestModelExecutionShapeFromShape:
    """Test ModelExecutionShape.from_shape() classmethod."""

    def test_from_shape_event_to_orchestrator(self):
        """Test from_shape for EVENT_TO_ORCHESTRATOR."""
        shape = ModelExecutionShape.from_shape(EnumExecutionShape.EVENT_TO_ORCHESTRATOR)

        assert shape.shape == EnumExecutionShape.EVENT_TO_ORCHESTRATOR
        assert shape.source_category == EnumMessageCategory.EVENT
        assert shape.target_node_kind == EnumNodeKind.ORCHESTRATOR
        assert "orchestrator" in shape.description.lower()

    def test_from_shape_event_to_reducer(self):
        """Test from_shape for EVENT_TO_REDUCER."""
        shape = ModelExecutionShape.from_shape(EnumExecutionShape.EVENT_TO_REDUCER)

        assert shape.shape == EnumExecutionShape.EVENT_TO_REDUCER
        assert shape.source_category == EnumMessageCategory.EVENT
        assert shape.target_node_kind == EnumNodeKind.REDUCER
        assert "reducer" in shape.description.lower()

    def test_from_shape_intent_to_effect(self):
        """Test from_shape for INTENT_TO_EFFECT."""
        shape = ModelExecutionShape.from_shape(EnumExecutionShape.INTENT_TO_EFFECT)

        assert shape.shape == EnumExecutionShape.INTENT_TO_EFFECT
        assert shape.source_category == EnumMessageCategory.INTENT
        assert shape.target_node_kind == EnumNodeKind.EFFECT
        assert "effect" in shape.description.lower()

    def test_from_shape_command_to_orchestrator(self):
        """Test from_shape for COMMAND_TO_ORCHESTRATOR."""
        shape = ModelExecutionShape.from_shape(
            EnumExecutionShape.COMMAND_TO_ORCHESTRATOR
        )

        assert shape.shape == EnumExecutionShape.COMMAND_TO_ORCHESTRATOR
        assert shape.source_category == EnumMessageCategory.COMMAND
        assert shape.target_node_kind == EnumNodeKind.ORCHESTRATOR
        assert "orchestrator" in shape.description.lower()

    def test_from_shape_command_to_effect(self):
        """Test from_shape for COMMAND_TO_EFFECT."""
        shape = ModelExecutionShape.from_shape(EnumExecutionShape.COMMAND_TO_EFFECT)

        assert shape.shape == EnumExecutionShape.COMMAND_TO_EFFECT
        assert shape.source_category == EnumMessageCategory.COMMAND
        assert shape.target_node_kind == EnumNodeKind.EFFECT
        assert "effect" in shape.description.lower()

    @pytest.mark.parametrize(
        "enum_shape",
        list(EnumExecutionShape),
    )
    def test_from_shape_all_enum_values(self, enum_shape: EnumExecutionShape):
        """Test from_shape works for all EnumExecutionShape values."""
        shape = ModelExecutionShape.from_shape(enum_shape)

        assert shape.shape == enum_shape
        assert shape.source_category is not None
        assert shape.target_node_kind is not None
        assert isinstance(shape.description, str)


class TestModelExecutionShapeGetAllShapes:
    """Test ModelExecutionShape.get_all_shapes() classmethod."""

    def test_get_all_shapes_returns_list(self):
        """Test get_all_shapes returns a list."""
        shapes = ModelExecutionShape.get_all_shapes()
        assert isinstance(shapes, list)

    def test_get_all_shapes_count_matches_enum(self):
        """Test get_all_shapes returns all enum values."""
        shapes = ModelExecutionShape.get_all_shapes()
        assert len(shapes) == len(EnumExecutionShape)

    def test_get_all_shapes_contains_all_enum_values(self):
        """Test get_all_shapes contains models for all enum values."""
        shapes = ModelExecutionShape.get_all_shapes()
        shape_enums = {s.shape for s in shapes}

        for enum_shape in EnumExecutionShape:
            assert enum_shape in shape_enums

    def test_get_all_shapes_returns_model_instances(self):
        """Test get_all_shapes returns ModelExecutionShape instances."""
        shapes = ModelExecutionShape.get_all_shapes()

        for shape in shapes:
            assert isinstance(shape, ModelExecutionShape)


# =============================================================================
# ModelExecutionShapeValidation Tests
# =============================================================================


class TestModelExecutionShapeValidationCreation:
    """Test ModelExecutionShapeValidation instantiation."""

    def test_create_with_all_fields(self):
        """Test model creation with all fields."""
        validation = ModelExecutionShapeValidation(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
            is_allowed=True,
            matched_shape=EnumExecutionShape.EVENT_TO_ORCHESTRATOR,
            rationale="Matches canonical EVENT_TO_ORCHESTRATOR shape",
        )

        assert validation.source_category == EnumMessageCategory.EVENT
        assert validation.target_node_kind == EnumNodeKind.ORCHESTRATOR
        assert validation.is_allowed is True
        assert validation.matched_shape == EnumExecutionShape.EVENT_TO_ORCHESTRATOR
        assert "EVENT_TO_ORCHESTRATOR" in validation.rationale

    def test_create_with_defaults(self):
        """Test model creation with default values."""
        validation = ModelExecutionShapeValidation(
            source_category=EnumMessageCategory.INTENT,
            target_node_kind=EnumNodeKind.COMPUTE,
        )

        assert validation.is_allowed is False
        assert validation.matched_shape is None
        assert validation.rationale == ""


class TestModelExecutionShapeValidationModelConfig:
    """Test ModelExecutionShapeValidation model configuration."""

    def test_model_is_frozen(self):
        """Test model is immutable (frozen=True)."""
        validation = ModelExecutionShapeValidation(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
            is_allowed=True,
        )

        with pytest.raises(ValidationError):
            validation.is_allowed = False

    def test_extra_fields_forbidden(self):
        """Test extra fields are forbidden (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionShapeValidation(
                source_category=EnumMessageCategory.EVENT,
                target_node_kind=EnumNodeKind.ORCHESTRATOR,
                unknown_field="value",
            )

        assert "unknown_field" in str(exc_info.value)


class TestModelExecutionShapeValidationValidateShapeAllowed:
    """Test validate_shape() for allowed shapes."""

    def test_validate_shape_event_to_orchestrator(self):
        """Test EVENT -> ORCHESTRATOR is allowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )

        assert validation.is_allowed is True
        assert validation.matched_shape == EnumExecutionShape.EVENT_TO_ORCHESTRATOR
        assert "canonical" in validation.rationale.lower()

    def test_validate_shape_event_to_reducer(self):
        """Test EVENT -> REDUCER is allowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.REDUCER,
        )

        assert validation.is_allowed is True
        assert validation.matched_shape == EnumExecutionShape.EVENT_TO_REDUCER
        assert validation.rationale != ""

    def test_validate_shape_intent_to_effect(self):
        """Test INTENT -> EFFECT is allowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.INTENT,
            target_node_kind=EnumNodeKind.EFFECT,
        )

        assert validation.is_allowed is True
        assert validation.matched_shape == EnumExecutionShape.INTENT_TO_EFFECT
        assert validation.rationale != ""

    def test_validate_shape_command_to_orchestrator(self):
        """Test COMMAND -> ORCHESTRATOR is allowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.COMMAND,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )

        assert validation.is_allowed is True
        assert validation.matched_shape == EnumExecutionShape.COMMAND_TO_ORCHESTRATOR
        assert validation.rationale != ""

    def test_validate_shape_command_to_effect(self):
        """Test COMMAND -> EFFECT is allowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.COMMAND,
            target_node_kind=EnumNodeKind.EFFECT,
        )

        assert validation.is_allowed is True
        assert validation.matched_shape == EnumExecutionShape.COMMAND_TO_EFFECT
        assert validation.rationale != ""


class TestModelExecutionShapeValidationValidateShapeDisallowed:
    """Test validate_shape() for disallowed shapes."""

    def test_validate_shape_event_to_compute_disallowed(self):
        """Test EVENT -> COMPUTE is disallowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.COMPUTE,
        )

        assert validation.is_allowed is False
        assert validation.matched_shape is None
        assert "no canonical shape" in validation.rationale.lower()

    def test_validate_shape_event_to_effect_disallowed(self):
        """Test EVENT -> EFFECT is disallowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.EFFECT,
        )

        assert validation.is_allowed is False
        assert validation.matched_shape is None

    def test_validate_shape_intent_to_reducer_disallowed(self):
        """Test INTENT -> REDUCER is disallowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.INTENT,
            target_node_kind=EnumNodeKind.REDUCER,
        )

        assert validation.is_allowed is False
        assert validation.matched_shape is None
        assert "no canonical shape" in validation.rationale.lower()

    def test_validate_shape_intent_to_compute_disallowed(self):
        """Test INTENT -> COMPUTE is disallowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.INTENT,
            target_node_kind=EnumNodeKind.COMPUTE,
        )

        assert validation.is_allowed is False
        assert validation.matched_shape is None

    def test_validate_shape_intent_to_orchestrator_disallowed(self):
        """Test INTENT -> ORCHESTRATOR is disallowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.INTENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )

        assert validation.is_allowed is False
        assert validation.matched_shape is None

    def test_validate_shape_command_to_compute_disallowed(self):
        """Test COMMAND -> COMPUTE is disallowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.COMMAND,
            target_node_kind=EnumNodeKind.COMPUTE,
        )

        assert validation.is_allowed is False
        assert validation.matched_shape is None
        assert "no canonical shape" in validation.rationale.lower()

    def test_validate_shape_command_to_reducer_disallowed(self):
        """Test COMMAND -> REDUCER is disallowed."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.COMMAND,
            target_node_kind=EnumNodeKind.REDUCER,
        )

        assert validation.is_allowed is False
        assert validation.matched_shape is None

    def test_validate_shape_to_runtime_host_disallowed(self):
        """Test any category -> RUNTIME_HOST is disallowed."""
        for category in EnumMessageCategory:
            validation = ModelExecutionShapeValidation.validate_shape(
                source_category=category,
                target_node_kind=EnumNodeKind.RUNTIME_HOST,
            )

            assert validation.is_allowed is False
            assert validation.matched_shape is None


class TestModelExecutionShapeValidationRationale:
    """Test rationale field content."""

    def test_allowed_shape_rationale_contains_shape_name(self):
        """Test allowed shape rationale contains the matched shape name."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )

        assert "event_to_orchestrator" in validation.rationale.lower()

    def test_disallowed_shape_rationale_explains_why(self):
        """Test disallowed shape rationale explains the violation."""
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.COMPUTE,
        )

        # Should mention both the source category and target node kind
        assert "event" in validation.rationale.lower()
        assert "compute" in validation.rationale.lower()


# =============================================================================
# ModelShapeValidationResult Tests
# =============================================================================


class TestModelShapeValidationResultCreation:
    """Test ModelShapeValidationResult instantiation."""

    def test_create_with_defaults(self):
        """Test model creation with default values."""
        result = ModelShapeValidationResult()

        assert result.validations == []
        assert result.total_validated == 0
        assert result.allowed_count == 0
        assert result.disallowed_count == 0
        assert result.is_fully_compliant is True
        assert result.errors == []
        assert result.warnings == []

    def test_create_with_all_fields(self):
        """Test model creation with all fields specified."""
        validation = ModelExecutionShapeValidation(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
            is_allowed=True,
        )

        result = ModelShapeValidationResult(
            validations=[validation],
            total_validated=1,
            allowed_count=1,
            disallowed_count=0,
            is_fully_compliant=True,
            errors=[],
            warnings=["Test warning"],
        )

        assert len(result.validations) == 1
        assert result.total_validated == 1
        assert result.allowed_count == 1
        assert result.disallowed_count == 0
        assert result.is_fully_compliant is True
        assert result.errors == []
        assert result.warnings == ["Test warning"]


class TestModelShapeValidationResultModelConfig:
    """Test ModelShapeValidationResult model configuration."""

    def test_model_is_frozen(self):
        """Test model is immutable (frozen=True)."""
        result = ModelShapeValidationResult()

        with pytest.raises(ValidationError):
            result.is_fully_compliant = False

    def test_extra_fields_forbidden(self):
        """Test extra fields are forbidden (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelShapeValidationResult(extra_field="not_allowed")

        assert "extra_field" in str(exc_info.value)


class TestModelShapeValidationResultFromValidations:
    """Test ModelShapeValidationResult.from_validations() classmethod."""

    def test_from_validations_all_valid(self):
        """Test from_validations with all valid shapes returns compliant result."""
        validations = [
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR
            ),
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.REDUCER
            ),
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.INTENT, EnumNodeKind.EFFECT
            ),
        ]

        result = ModelShapeValidationResult.from_validations(validations)

        assert result.is_fully_compliant is True
        assert result.total_validated == 3
        assert result.allowed_count == 3
        assert result.disallowed_count == 0
        assert result.errors == []

    def test_from_validations_all_invalid(self):
        """Test from_validations with all invalid shapes returns non-compliant result."""
        validations = [
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.COMPUTE
            ),
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.INTENT, EnumNodeKind.REDUCER
            ),
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.COMMAND, EnumNodeKind.COMPUTE
            ),
        ]

        result = ModelShapeValidationResult.from_validations(validations)

        assert result.is_fully_compliant is False
        assert result.total_validated == 3
        assert result.allowed_count == 0
        assert result.disallowed_count == 3
        assert len(result.errors) == 3

    def test_from_validations_mixed(self):
        """Test from_validations with mixed valid/invalid shapes."""
        validations = [
            # Valid
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR
            ),
            # Invalid
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.COMPUTE
            ),
            # Valid
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.COMMAND, EnumNodeKind.EFFECT
            ),
        ]

        result = ModelShapeValidationResult.from_validations(validations)

        assert result.is_fully_compliant is False
        assert result.total_validated == 3
        assert result.allowed_count == 2
        assert result.disallowed_count == 1
        assert len(result.errors) == 1

    def test_from_validations_empty_list(self):
        """Test from_validations with empty list returns compliant result."""
        result = ModelShapeValidationResult.from_validations([])

        assert result.is_fully_compliant is True
        assert result.total_validated == 0
        assert result.allowed_count == 0
        assert result.disallowed_count == 0
        assert result.errors == []

    def test_from_validations_preserves_validations(self):
        """Test from_validations preserves the validation list."""
        validation = ModelExecutionShapeValidation.validate_shape(
            EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR
        )

        result = ModelShapeValidationResult.from_validations([validation])

        assert len(result.validations) == 1
        assert result.validations[0] is validation


class TestModelShapeValidationResultCounts:
    """Test count calculations in ModelShapeValidationResult."""

    def test_counts_match_validations(self):
        """Test counts match the number of allowed/disallowed validations."""
        # Create a mix of 5 validations: 3 allowed, 2 disallowed
        validations = [
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR
            ),  # allowed
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.REDUCER
            ),  # allowed
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.INTENT, EnumNodeKind.EFFECT
            ),  # allowed
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.COMPUTE
            ),  # disallowed
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.COMMAND, EnumNodeKind.COMPUTE
            ),  # disallowed
        ]

        result = ModelShapeValidationResult.from_validations(validations)

        assert result.total_validated == 5
        assert result.allowed_count == 3
        assert result.disallowed_count == 2
        assert result.allowed_count + result.disallowed_count == result.total_validated


class TestModelShapeValidationResultErrors:
    """Test error list in ModelShapeValidationResult."""

    def test_errors_populated_from_disallowed_rationales(self):
        """Test errors list is populated from disallowed validation rationales."""
        validations = [
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.COMPUTE
            ),
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.INTENT, EnumNodeKind.REDUCER
            ),
        ]

        result = ModelShapeValidationResult.from_validations(validations)

        assert len(result.errors) == 2
        # Each error should contain the rationale from the disallowed validation
        assert all("no canonical shape" in error.lower() for error in result.errors)

    def test_no_errors_when_all_allowed(self):
        """Test errors list is empty when all validations are allowed."""
        validations = [
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR
            ),
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.COMMAND, EnumNodeKind.EFFECT
            ),
        ]

        result = ModelShapeValidationResult.from_validations(validations)

        assert result.errors == []


class TestModelShapeValidationResultCompliance:
    """Test is_fully_compliant calculation."""

    def test_fully_compliant_when_no_disallowed(self):
        """Test is_fully_compliant is True when no disallowed shapes."""
        validations = [
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR
            ),
        ]

        result = ModelShapeValidationResult.from_validations(validations)

        assert result.is_fully_compliant is True

    def test_not_compliant_when_any_disallowed(self):
        """Test is_fully_compliant is False when any shape is disallowed."""
        validations = [
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR
            ),  # allowed
            ModelExecutionShapeValidation.validate_shape(
                EnumMessageCategory.EVENT, EnumNodeKind.COMPUTE
            ),  # disallowed
        ]

        result = ModelShapeValidationResult.from_validations(validations)

        assert result.is_fully_compliant is False

    def test_compliant_with_empty_validations(self):
        """Test is_fully_compliant is True with empty validations (vacuous truth)."""
        result = ModelShapeValidationResult.from_validations([])

        assert result.is_fully_compliant is True


# =============================================================================
# Integration / Cross-Model Tests
# =============================================================================


class TestExecutionShapeModelsIntegration:
    """Integration tests across execution shape models."""

    def test_all_canonical_shapes_validate_as_allowed(self):
        """Test all canonical shapes from get_all_shapes() validate as allowed."""
        all_shapes = ModelExecutionShape.get_all_shapes()

        for shape_model in all_shapes:
            validation = ModelExecutionShapeValidation.validate_shape(
                source_category=shape_model.source_category,
                target_node_kind=shape_model.target_node_kind,
            )

            assert validation.is_allowed is True, (
                f"Shape {shape_model.shape} should be allowed but is not"
            )
            assert validation.matched_shape == shape_model.shape

    def test_comprehensive_validation_result(self):
        """Test creating a comprehensive validation result with mixed shapes."""
        # Validate all possible combinations and collect results
        validations = []
        for category in EnumMessageCategory:
            for node_kind in EnumNodeKind:
                validation = ModelExecutionShapeValidation.validate_shape(
                    source_category=category,
                    target_node_kind=node_kind,
                )
                validations.append(validation)

        result = ModelShapeValidationResult.from_validations(validations)

        # Total should be 3 categories * 5 node kinds = 15
        assert result.total_validated == 15

        # Should have exactly 5 allowed shapes
        assert result.allowed_count == 5

        # Should have 10 disallowed shapes
        assert result.disallowed_count == 10

        # Should not be fully compliant
        assert result.is_fully_compliant is False

    def test_from_shape_round_trip(self):
        """Test that from_shape and validate_shape are consistent."""
        for enum_shape in EnumExecutionShape:
            shape_model = ModelExecutionShape.from_shape(enum_shape)

            validation = ModelExecutionShapeValidation.validate_shape(
                source_category=shape_model.source_category,
                target_node_kind=shape_model.target_node_kind,
            )

            assert validation.is_allowed is True
            assert validation.matched_shape == enum_shape
