# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for PayloadHTTP.

This module tests the PayloadHTTP model for HTTP request intents, verifying:
1. Field validation (url, method, headers, body, etc.)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import PayloadHTTP


@pytest.mark.unit
class TestPayloadHTTPInstantiation:
    """Test PayloadHTTP instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = PayloadHTTP(url="https://example.com")
        assert payload.url == "https://example.com"
        assert payload.intent_type == "http_request"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        payload = PayloadHTTP(
            url="https://api.example.com/v1/resource",
            method="POST",
            headers={
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            },
            body={"key": "value"},
            query_params={"page": "1"},
            timeout_seconds=60,
            retry_count=3,
            follow_redirects=False,
        )
        assert payload.url == "https://api.example.com/v1/resource"
        assert payload.method == "POST"
        assert payload.headers == {
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
        }
        assert payload.body == {"key": "value"}
        assert payload.query_params == {"page": "1"}
        assert payload.timeout_seconds == 60
        assert payload.retry_count == 3
        assert payload.follow_redirects is False


@pytest.mark.unit
class TestPayloadHTTPDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'http_request'."""
        payload = PayloadHTTP(url="https://example.com")
        assert payload.intent_type == "http_request"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = PayloadHTTP(url="https://example.com")
        data = payload.model_dump()
        assert data["intent_type"] == "http_request"


@pytest.mark.unit
class TestPayloadHTTPMethodValidation:
    """Test method field validation."""

    def test_valid_methods(self) -> None:
        """Test all valid HTTP methods."""
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        for method in valid_methods:
            payload = PayloadHTTP(url="https://example.com", method=method)
            assert payload.method == method

    def test_invalid_method_rejected(self) -> None:
        """Test that invalid method is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP(url="https://example.com", method="TRACE")  # type: ignore[arg-type]
        assert "method" in str(exc_info.value)

    def test_lowercase_method_rejected(self) -> None:
        """Test that lowercase method is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP(url="https://example.com", method="get")  # type: ignore[arg-type]
        assert "method" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadHTTPURLValidation:
    """Test URL field validation."""

    def test_url_required(self) -> None:
        """Test that url is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP()  # type: ignore[call-arg]
        assert "url" in str(exc_info.value)

    def test_url_min_length(self) -> None:
        """Test url minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP(url="")
        assert "url" in str(exc_info.value)

    def test_url_max_length(self) -> None:
        """Test url maximum length validation."""
        long_url = "https://example.com/" + "a" * 2040
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP(url=long_url)
        assert "url" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadHTTPDefaultValues:
    """Test default values."""

    def test_default_method(self) -> None:
        """Test default method is GET."""
        payload = PayloadHTTP(url="https://example.com")
        assert payload.method == "GET"

    def test_default_headers(self) -> None:
        """Test default headers is empty dict."""
        payload = PayloadHTTP(url="https://example.com")
        assert payload.headers == {}

    def test_default_body(self) -> None:
        """Test default body is None."""
        payload = PayloadHTTP(url="https://example.com")
        assert payload.body is None

    def test_default_query_params(self) -> None:
        """Test default query_params is empty dict."""
        payload = PayloadHTTP(url="https://example.com")
        assert payload.query_params == {}

    def test_default_timeout_seconds(self) -> None:
        """Test default timeout_seconds is 30."""
        payload = PayloadHTTP(url="https://example.com")
        assert payload.timeout_seconds == 30

    def test_default_retry_count(self) -> None:
        """Test default retry_count is 0."""
        payload = PayloadHTTP(url="https://example.com")
        assert payload.retry_count == 0

    def test_default_follow_redirects(self) -> None:
        """Test default follow_redirects is True."""
        payload = PayloadHTTP(url="https://example.com")
        assert payload.follow_redirects is True


@pytest.mark.unit
class TestPayloadHTTPTimeoutValidation:
    """Test timeout_seconds field validation."""

    def test_timeout_minimum(self) -> None:
        """Test timeout minimum value."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP(url="https://example.com", timeout_seconds=0)
        assert "timeout_seconds" in str(exc_info.value)

    def test_timeout_maximum(self) -> None:
        """Test timeout maximum value."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP(url="https://example.com", timeout_seconds=301)
        assert "timeout_seconds" in str(exc_info.value)

    def test_valid_timeout_range(self) -> None:
        """Test valid timeout values."""
        for timeout in [1, 30, 60, 300]:
            payload = PayloadHTTP(url="https://example.com", timeout_seconds=timeout)
            assert payload.timeout_seconds == timeout


@pytest.mark.unit
class TestPayloadHTTPRetryCountValidation:
    """Test retry_count field validation."""

    def test_retry_count_minimum(self) -> None:
        """Test retry_count minimum value."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP(url="https://example.com", retry_count=-1)
        assert "retry_count" in str(exc_info.value)

    def test_retry_count_maximum(self) -> None:
        """Test retry_count maximum value."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP(url="https://example.com", retry_count=11)
        assert "retry_count" in str(exc_info.value)

    def test_valid_retry_range(self) -> None:
        """Test valid retry count values."""
        for count in [0, 5, 10]:
            payload = PayloadHTTP(url="https://example.com", retry_count=count)
            assert payload.retry_count == count


@pytest.mark.unit
class TestPayloadHTTPBodyTypes:
    """Test body field with various value types."""

    def test_body_as_dict(self) -> None:
        """Test body as dictionary."""
        payload = PayloadHTTP(url="https://example.com", body={"key": "value"})
        assert payload.body == {"key": "value"}

    def test_body_as_string(self) -> None:
        """Test body as string."""
        payload = PayloadHTTP(url="https://example.com", body="raw body content")
        assert payload.body == "raw body content"

    def test_body_as_none(self) -> None:
        """Test body as None."""
        payload = PayloadHTTP(url="https://example.com", body=None)
        assert payload.body is None


@pytest.mark.unit
class TestPayloadHTTPImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_url(self) -> None:
        """Test that url cannot be modified after creation."""
        payload = PayloadHTTP(url="https://example.com")
        with pytest.raises(ValidationError):
            payload.url = "https://other.com"  # type: ignore[misc]

    def test_cannot_modify_method(self) -> None:
        """Test that method cannot be modified after creation."""
        payload = PayloadHTTP(url="https://example.com")
        with pytest.raises(ValidationError):
            payload.method = "POST"  # type: ignore[misc]


@pytest.mark.unit
class TestPayloadHTTPSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = PayloadHTTP(
            url="https://api.example.com",
            method="POST",
            headers={"Accept": "application/json"},
            body={"data": "test"},
            timeout_seconds=60,
        )
        data = original.model_dump()
        restored = PayloadHTTP.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = PayloadHTTP(url="https://example.com")
        json_str = original.model_dump_json()
        restored = PayloadHTTP.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = PayloadHTTP(url="https://example.com")
        data = payload.model_dump()
        expected_keys = {
            "intent_type",
            "url",
            "method",
            "headers",
            "body",
            "query_params",
            "timeout_seconds",
            "retry_count",
            "follow_redirects",
        }
        assert set(data.keys()) == expected_keys


@pytest.mark.unit
class TestPayloadHTTPExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadHTTP(
                url="https://example.com",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)
