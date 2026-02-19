# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelSupportClassificationResult."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumSentiment, EnumSupportCategory
from omnibase_core.models.demo.model_validate import (
    ModelSupportClassificationResult,
)


class TestModelSupportClassificationResultCreation:
    """Test ModelSupportClassificationResult creation and validation."""

    def test_create_valid_result(self, valid_classification_data: dict) -> None:
        """Test creating a valid classification result."""
        result = ModelSupportClassificationResult.model_validate(
            valid_classification_data
        )

        assert result.ticket_id == "TKT-TEST-001"
        assert result.category == EnumSupportCategory.BILLING_REFUND
        assert result.confidence == 0.95
        assert result.sentiment == EnumSentiment.NEUTRAL
        assert "refund" in result.summary.lower()
        assert result.latency_ms == 1250
        assert result.model_id == "gpt-4-turbo-2024-04-09"
        assert result.reason_codes is None
        assert result.invariant_tags is None

    def test_create_full_result(self, valid_classification_data_full: dict) -> None:
        """Test creating a result with all fields populated."""
        result = ModelSupportClassificationResult.model_validate(
            valid_classification_data_full
        )

        assert result.category == EnumSupportCategory.TECHNICAL_BUG
        assert result.sentiment == EnumSentiment.NEGATIVE
        assert result.reason_codes == ["app_crash", "ios_specific"]
        assert result.invariant_tags == ["technical_domain", "mobile_platform"]


class TestModelSupportClassificationResultFrozen:
    """Test that ModelSupportClassificationResult is immutable."""

    def test_model_is_frozen(self, valid_classification_data: dict) -> None:
        """Test that the model is frozen (immutable)."""
        result = ModelSupportClassificationResult.model_validate(
            valid_classification_data
        )

        with pytest.raises(ValidationError):
            # NOTE(OMN-TBD): mypy flags assignment to frozen model attribute. Safe because
            # this is test code verifying frozen behavior and the assignment is expected to raise.
            result.confidence = 0.50  # type: ignore[misc]

    def test_model_is_hashable(self, valid_classification_data: dict) -> None:
        """Test that frozen model is hashable."""
        result = ModelSupportClassificationResult.model_validate(
            valid_classification_data
        )

        # Should not raise - frozen models are hashable
        hash_value = hash(result)
        assert isinstance(hash_value, int)


class TestModelSupportClassificationResultValidation:
    """Test ModelSupportClassificationResult field validation."""

    def test_confidence_min_bound(self, valid_classification_data: dict) -> None:
        """Test that confidence below 0.0 raises validation error."""
        valid_classification_data["confidence"] = -0.1

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportClassificationResult.model_validate(valid_classification_data)

        assert "confidence" in str(exc_info.value)

    def test_confidence_max_bound(self, valid_classification_data: dict) -> None:
        """Test that confidence above 1.0 raises validation error."""
        valid_classification_data["confidence"] = 1.1

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportClassificationResult.model_validate(valid_classification_data)

        assert "confidence" in str(exc_info.value)

    def test_confidence_at_bounds(self, valid_classification_data: dict) -> None:
        """Test that confidence at bounds (0.0, 1.0) is valid."""
        valid_classification_data["confidence"] = 0.0
        result = ModelSupportClassificationResult.model_validate(
            valid_classification_data
        )
        assert result.confidence == 0.0

        valid_classification_data["confidence"] = 1.0
        result = ModelSupportClassificationResult.model_validate(
            valid_classification_data
        )
        assert result.confidence == 1.0

    def test_negative_latency(self, valid_classification_data: dict) -> None:
        """Test that negative latency_ms raises validation error."""
        valid_classification_data["latency_ms"] = -100

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportClassificationResult.model_validate(valid_classification_data)

        assert "latency_ms" in str(exc_info.value)

    def test_invalid_category(self, valid_classification_data: dict) -> None:
        """Test that invalid category raises validation error."""
        valid_classification_data["category"] = "invalid_category"

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportClassificationResult.model_validate(valid_classification_data)

        assert "category" in str(exc_info.value)

    def test_invalid_sentiment(self, valid_classification_data: dict) -> None:
        """Test that invalid sentiment raises validation error."""
        valid_classification_data["sentiment"] = "angry"

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportClassificationResult.model_validate(valid_classification_data)

        assert "sentiment" in str(exc_info.value)

    def test_extra_fields_forbidden(self, valid_classification_data: dict) -> None:
        """Test that extra fields are forbidden."""
        valid_classification_data["extra_field"] = "not allowed"

        with pytest.raises(ValidationError) as exc_info:
            ModelSupportClassificationResult.model_validate(valid_classification_data)

        assert "extra_field" in str(exc_info.value)


class TestModelSupportClassificationResultEnumValues:
    """Test enum value handling in ModelSupportClassificationResult."""

    def test_all_category_values(self, valid_classification_data: dict) -> None:
        """Test that all category enum values are accepted."""
        categories = [
            "billing_refund",
            "billing_payment",
            "account_access",
            "account_profile",
            "technical_bug",
            "technical_howto",
        ]

        for category in categories:
            valid_classification_data["category"] = category
            result = ModelSupportClassificationResult.model_validate(
                valid_classification_data
            )
            assert result.category.value == category

    def test_all_sentiment_values(self, valid_classification_data: dict) -> None:
        """Test that all sentiment enum values are accepted."""
        sentiments = ["positive", "neutral", "negative"]

        for sentiment in sentiments:
            valid_classification_data["sentiment"] = sentiment
            result = ModelSupportClassificationResult.model_validate(
                valid_classification_data
            )
            assert result.sentiment.value == sentiment


class TestModelSupportClassificationResultSerialization:
    """Test serialization of ModelSupportClassificationResult."""

    def test_model_dump(self, valid_classification_data: dict) -> None:
        """Test that model_dump produces valid dictionary."""
        result = ModelSupportClassificationResult.model_validate(
            valid_classification_data
        )
        dumped = result.model_dump()

        assert dumped["ticket_id"] == "TKT-TEST-001"
        assert dumped["confidence"] == 0.95
        assert dumped["latency_ms"] == 1250

    def test_model_dump_json(self, valid_classification_data: dict) -> None:
        """Test that model_dump_json produces valid JSON string."""
        result = ModelSupportClassificationResult.model_validate(
            valid_classification_data
        )
        json_str = result.model_dump_json()

        assert "TKT-TEST-001" in json_str
        assert "0.95" in json_str
        assert "billing_refund" in json_str
