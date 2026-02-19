# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelEffectInput including effect_type consistency validation.

This module tests the ModelEffectInput model, particularly the effect_type
consistency validator that ensures parent and nested effect_type fields match
when using typed ModelEffectInputData.

Test Coverage:
    - Basic ModelEffectInput construction with dict operation_data
    - Typed ModelEffectInputData construction with matching effect_types
    - Validation error when effect_types mismatch
    - All EnumEffectType combinations for consistency checks
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumEffectType
from omnibase_core.models.context import ModelEffectInputData
from omnibase_core.models.effect.model_effect_input import ModelEffectInput


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestModelEffectInputEffectTypeConsistency:
    """Test suite for effect_type consistency validation in ModelEffectInput."""

    def test_dict_operation_data_no_validation(self) -> None:
        """Verify dict operation_data skips effect_type consistency check.

        When operation_data is a plain dict (not ModelEffectInputData),
        no consistency validation is performed since there's no nested effect_type.
        """
        # Arrange & Act - dict has no effect_type field
        input_model = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"url": "https://api.example.com", "method": "POST"},
        )

        # Assert
        assert input_model.effect_type == EnumEffectType.API_CALL
        assert input_model.operation_data == {
            "url": "https://api.example.com",
            "method": "POST",
        }

    def test_typed_operation_data_matching_effect_types_valid(self) -> None:
        """Verify ModelEffectInputData with matching effect_type is valid.

        When operation_data is ModelEffectInputData and both effect_types match,
        the model should be constructed successfully.
        """
        # Arrange & Act
        input_model = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_path="https://api.example.com/users",
                target_system="user-service",
                operation_name="create_user",
            ),
        )

        # Assert
        assert input_model.effect_type == EnumEffectType.API_CALL
        assert isinstance(input_model.operation_data, ModelEffectInputData)
        assert input_model.operation_data.effect_type == EnumEffectType.API_CALL

    def test_typed_operation_data_mismatched_effect_types_raises(self) -> None:
        """Verify ModelEffectInputData with mismatched effect_type raises error.

        When operation_data is ModelEffectInputData and effect_types differ,
        a ValidationError should be raised with a descriptive message.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInput(
                effect_type=EnumEffectType.API_CALL,
                operation_data=ModelEffectInputData(
                    effect_type=EnumEffectType.DATABASE_OPERATION,
                    resource_path="users",
                    target_system="postgres",
                ),
            )

        # Verify error message contains helpful information
        error_message = str(exc_info.value)
        assert "effect_type mismatch" in error_message.lower()
        assert "api_call" in error_message.lower()
        assert "database_operation" in error_message.lower()

    @pytest.mark.parametrize(
        "effect_type",
        [
            EnumEffectType.FILE_OPERATION,
            EnumEffectType.DATABASE_OPERATION,
            EnumEffectType.API_CALL,
            EnumEffectType.EVENT_EMISSION,
            EnumEffectType.DIRECTORY_OPERATION,
            EnumEffectType.TICKET_STORAGE,
            EnumEffectType.METRICS_COLLECTION,
        ],
    )
    def test_all_effect_types_matching_valid(self, effect_type: EnumEffectType) -> None:
        """Verify all EnumEffectType values work with matching operation_data.

        Parametrized test ensuring every effect_type enum value can be used
        with a matching ModelEffectInputData.effect_type.
        """
        # Arrange & Act
        input_model = ModelEffectInput(
            effect_type=effect_type,
            operation_data=ModelEffectInputData(
                effect_type=effect_type,
                resource_path="/test/path",
                target_system="test-system",
            ),
        )

        # Assert
        assert input_model.effect_type == effect_type
        assert isinstance(input_model.operation_data, ModelEffectInputData)
        assert input_model.operation_data.effect_type == effect_type

    def test_all_mismatch_combinations_raise(self) -> None:
        """Verify any effect_type mismatch raises validation error.

        Tests a sample of mismatched combinations to ensure the validator
        catches all mismatch cases.
        """
        mismatched_pairs = [
            (EnumEffectType.API_CALL, EnumEffectType.DATABASE_OPERATION),
            (EnumEffectType.FILE_OPERATION, EnumEffectType.API_CALL),
            (EnumEffectType.DATABASE_OPERATION, EnumEffectType.EVENT_EMISSION),
            (EnumEffectType.EVENT_EMISSION, EnumEffectType.FILE_OPERATION),
        ]

        for parent_type, child_type in mismatched_pairs:
            with pytest.raises(ValidationError) as exc_info:
                ModelEffectInput(
                    effect_type=parent_type,
                    operation_data=ModelEffectInputData(
                        effect_type=child_type,
                        resource_path="/test",
                    ),
                )

            error_message = str(exc_info.value)
            assert "effect_type mismatch" in error_message.lower(), (
                f"Expected 'effect_type mismatch' in error for "
                f"parent={parent_type}, child={child_type}"
            )


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestModelEffectInputBasicConstruction:
    """Test suite for basic ModelEffectInput construction and defaults."""

    def test_minimal_construction(self) -> None:
        """Verify ModelEffectInput can be created with minimal required fields."""
        input_model = ModelEffectInput(effect_type=EnumEffectType.API_CALL)

        assert input_model.effect_type == EnumEffectType.API_CALL
        assert input_model.operation_data == {}
        assert input_model.transaction_enabled is True
        assert input_model.retry_enabled is True
        assert input_model.max_retries == 3
        assert input_model.timeout_ms == 30000

    def test_all_fields_populated(self) -> None:
        """Verify ModelEffectInput accepts all optional fields."""
        from uuid import uuid4

        from omnibase_core.models.effect.model_effect_metadata import (
            ModelEffectMetadata,
        )

        operation_id = uuid4()
        input_model = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data={"query": "SELECT * FROM users"},
            operation_id=operation_id,
            transaction_enabled=False,
            retry_enabled=False,
            max_retries=5,
            retry_delay_ms=2000,
            circuit_breaker_enabled=True,
            timeout_ms=60000,
            metadata=ModelEffectMetadata(
                correlation_id="test-correlation",
                trace_id="test-trace",
            ),
        )

        assert input_model.effect_type == EnumEffectType.DATABASE_OPERATION
        assert input_model.operation_id == operation_id
        assert input_model.transaction_enabled is False
        assert input_model.retry_enabled is False
        assert input_model.max_retries == 5
        assert input_model.retry_delay_ms == 2000
        assert input_model.circuit_breaker_enabled is True
        assert input_model.timeout_ms == 60000
        assert input_model.metadata.correlation_id == "test-correlation"


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestModelEffectInputExport:
    """Test that ModelEffectInput is properly exported."""

    def test_import_from_effect_module(self) -> None:
        """Test model can be imported from effect module."""
        from omnibase_core.models.effect import ModelEffectInput as ModuleImport

        assert ModuleImport is ModelEffectInput

    def test_model_in_all(self) -> None:
        """Test model is in __all__."""
        from omnibase_core.models.effect import model_effect_input

        assert "ModelEffectInput" in model_effect_input.__all__
