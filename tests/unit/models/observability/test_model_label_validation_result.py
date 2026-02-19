# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelLabelValidationResult."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_label_violation_type import EnumLabelViolationType
from omnibase_core.models.observability.model_label_validation_result import (
    ModelLabelValidationResult,
)
from omnibase_core.models.observability.model_label_violation import ModelLabelViolation


class TestModelLabelValidationResult:
    """Tests for ModelLabelValidationResult model."""

    def test_create_valid_result(self) -> None:
        """Test creating a valid result with no violations."""
        result = ModelLabelValidationResult(
            is_valid=True,
            violations=[],
            sanitized_labels={"method": "GET", "status": "200"},
        )
        assert result.is_valid is True
        assert result.violations == []
        assert result.sanitized_labels == {"method": "GET", "status": "200"}

    def test_create_invalid_result(self) -> None:
        """Test creating an invalid result with violations."""
        violation = ModelLabelViolation(
            violation_type=EnumLabelViolationType.FORBIDDEN_KEY,
            key="envelope_id",
            message="Forbidden key",
        )
        result = ModelLabelValidationResult(
            is_valid=False,
            violations=[violation],
            sanitized_labels={"method": "GET"},
        )
        assert result.is_valid is False
        assert len(result.violations) == 1
        assert result.violations[0].key == "envelope_id"

    def test_sanitized_labels_can_be_none(self) -> None:
        """Test that sanitized_labels can be None."""
        result = ModelLabelValidationResult(
            is_valid=False,
            violations=[
                ModelLabelViolation(
                    violation_type=EnumLabelViolationType.FORBIDDEN_KEY,
                    key="envelope_id",
                    message="Forbidden",
                )
            ],
            sanitized_labels=None,
        )
        assert result.sanitized_labels is None

    def test_default_violations_is_empty_list(self) -> None:
        """Test that violations defaults to empty list."""
        result = ModelLabelValidationResult(is_valid=True)
        assert result.violations == []

    def test_is_valid_required(self) -> None:
        """Test that is_valid is required."""
        with pytest.raises(ValidationError):
            ModelLabelValidationResult()  # type: ignore[call-arg]

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable."""
        result = ModelLabelValidationResult(is_valid=True)
        with pytest.raises(ValidationError):
            result.is_valid = False  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLabelValidationResult(is_valid=True, extra="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()

    def test_multiple_violations(self) -> None:
        """Test result with multiple violations."""
        violations = [
            ModelLabelViolation(
                violation_type=EnumLabelViolationType.FORBIDDEN_KEY,
                key="envelope_id",
                message="Forbidden",
            ),
            ModelLabelViolation(
                violation_type=EnumLabelViolationType.VALUE_TOO_LONG,
                key="description",
                value="x" * 200,
                message="Too long",
            ),
        ]
        result = ModelLabelValidationResult(
            is_valid=False,
            violations=violations,
            sanitized_labels={"method": "GET"},
        )
        assert len(result.violations) == 2
