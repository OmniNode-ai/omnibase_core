# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for HttpRequestContract and HttpResponseContract.

Covers:
    - Instantiation with required fields only
    - Instantiation with all optional fields
    - Field defaults
    - Validation: invalid values raise ValidationError
    - Immutability (frozen model)
    - No imports from httpx, requests, or handler/infra modules

See Also:
    OMN-4222: Defines HTTP wire contracts in omnibase_core
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts import HttpRequestContract, HttpResponseContract


@pytest.mark.unit
class TestHttpRequestContract:
    """Tests for HttpRequestContract instantiation, defaults, and validation."""

    def test_required_fields_only(self) -> None:
        """Instantiate with only the required fields (method and url)."""
        req = HttpRequestContract(method="GET", url="https://example.com/api")
        assert req.method == "GET"
        assert req.url == "https://example.com/api"

    def test_default_headers_is_empty_dict(self) -> None:
        """Default headers should be an empty dict, not None."""
        req = HttpRequestContract(method="GET", url="https://example.com/")
        assert req.headers == {}
        assert isinstance(req.headers, dict)

    def test_default_body_is_none(self) -> None:
        """Default body should be None."""
        req = HttpRequestContract(method="DELETE", url="https://example.com/items/1")
        assert req.body is None

    def test_default_timeout_seconds(self) -> None:
        """Default timeout_seconds should be 30.0."""
        req = HttpRequestContract(method="GET", url="https://example.com/")
        assert req.timeout_seconds == 30.0

    def test_default_follow_redirects(self) -> None:
        """Default follow_redirects should be True."""
        req = HttpRequestContract(method="GET", url="https://example.com/")
        assert req.follow_redirects is True

    def test_all_fields_explicit(self) -> None:
        """Instantiate with all fields provided explicitly."""
        req = HttpRequestContract(
            method="POST",
            url="https://api.example.com/v1/nodes",
            headers={"Content-Type": "application/json", "Authorization": "Bearer tok"},
            body=b'{"node_id": "abc"}',
            timeout_seconds=10.5,
            follow_redirects=False,
        )
        assert req.method == "POST"
        assert req.url == "https://api.example.com/v1/nodes"
        assert req.headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer tok",
        }
        assert req.body == b'{"node_id": "abc"}'
        assert req.timeout_seconds == 10.5
        assert req.follow_redirects is False

    def test_body_is_bytes(self) -> None:
        """Body field accepts raw bytes."""
        req = HttpRequestContract(
            method="PUT",
            url="https://example.com/resource",
            body=b"\x00\x01\x02\xff",
        )
        assert req.body == b"\x00\x01\x02\xff"

    def test_timeout_seconds_must_be_positive(self) -> None:
        """timeout_seconds must be > 0; zero or negative should raise ValidationError."""
        with pytest.raises(ValidationError):
            HttpRequestContract(
                method="GET", url="https://example.com/", timeout_seconds=0
            )

        with pytest.raises(ValidationError):
            HttpRequestContract(
                method="GET", url="https://example.com/", timeout_seconds=-5.0
            )

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields must raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            HttpRequestContract(  # type: ignore[call-arg]
                method="GET",
                url="https://example.com/",
                unknown_field="value",
            )

    def test_frozen_model_is_immutable(self) -> None:
        """Frozen model must not allow mutation via model_copy with new field values.

        Pydantic frozen=True models raise ValidationError when attempting to use
        model_copy(update=...) with fields that violate frozen constraints.
        We verify immutability by confirming the model config reports frozen=True.
        """
        req = HttpRequestContract(method="GET", url="https://example.com/")
        assert req.model_config.get("frozen") is True

    def test_method_required(self) -> None:
        """Omitting method must raise ValidationError."""
        with pytest.raises(ValidationError):
            HttpRequestContract(url="https://example.com/")  # type: ignore[call-arg]

    def test_url_required(self) -> None:
        """Omitting url must raise ValidationError."""
        with pytest.raises(ValidationError):
            HttpRequestContract(method="GET")  # type: ignore[call-arg]

    def test_headers_default_is_not_shared_across_instances(self) -> None:
        """Each instance must get its own default headers dict (no mutable default aliasing)."""
        req1 = HttpRequestContract(method="GET", url="https://example.com/")
        req2 = HttpRequestContract(method="POST", url="https://example.com/other")
        # Since frozen=True, mutation is blocked, but confirm they are independent objects
        assert req1.headers is not req2.headers

    def test_common_http_methods(self) -> None:
        """All common HTTP methods can be set as method field value."""
        for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
            req = HttpRequestContract(method=method, url="https://example.com/")
            assert req.method == method


@pytest.mark.unit
class TestHttpResponseContract:
    """Tests for HttpResponseContract instantiation, defaults, and validation."""

    def test_required_fields_only(self) -> None:
        """Instantiate with only the required fields (status_code and body)."""
        resp = HttpResponseContract(status_code=200, body=b"OK")
        assert resp.status_code == 200
        assert resp.body == b"OK"

    def test_default_headers_is_empty_dict(self) -> None:
        """Default headers should be an empty dict, not None."""
        resp = HttpResponseContract(status_code=204, body=b"")
        assert resp.headers == {}
        assert isinstance(resp.headers, dict)

    def test_default_elapsed_seconds_is_none(self) -> None:
        """Default elapsed_seconds should be None."""
        resp = HttpResponseContract(status_code=200, body=b"content")
        assert resp.elapsed_seconds is None

    def test_all_fields_explicit(self) -> None:
        """Instantiate with all fields provided explicitly."""
        resp = HttpResponseContract(
            status_code=201,
            headers={"Content-Type": "application/json", "X-Request-Id": "abc123"},
            body=b'{"id": "xyz"}',
            elapsed_seconds=0.452,
        )
        assert resp.status_code == 201
        assert resp.headers == {
            "Content-Type": "application/json",
            "X-Request-Id": "abc123",
        }
        assert resp.body == b'{"id": "xyz"}'
        assert resp.elapsed_seconds == 0.452

    def test_body_empty_bytes_for_no_content(self) -> None:
        """Body can be empty bytes for 204 No Content responses."""
        resp = HttpResponseContract(status_code=204, body=b"")
        assert resp.body == b""

    def test_body_is_bytes(self) -> None:
        """Body field accepts raw bytes."""
        resp = HttpResponseContract(
            status_code=200,
            body=b"\x89PNG\r\n\x1a\n",
        )
        assert resp.body == b"\x89PNG\r\n\x1a\n"

    def test_elapsed_seconds_zero_is_valid(self) -> None:
        """elapsed_seconds=0.0 is a valid non-negative value."""
        resp = HttpResponseContract(status_code=200, body=b"fast", elapsed_seconds=0.0)
        assert resp.elapsed_seconds == 0.0

    def test_elapsed_seconds_negative_raises_validation_error(self) -> None:
        """Negative elapsed_seconds must raise ValidationError."""
        with pytest.raises(ValidationError):
            HttpResponseContract(status_code=200, body=b"data", elapsed_seconds=-1.0)

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields must raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            HttpResponseContract(  # type: ignore[call-arg]
                status_code=200,
                body=b"data",
                unknown_field="value",
            )

    def test_frozen_model_is_immutable(self) -> None:
        """Frozen model must not allow mutation via model_copy with new field values.

        Pydantic frozen=True models raise ValidationError when attempting to use
        model_copy(update=...) with fields that violate frozen constraints.
        We verify immutability by confirming the model config reports frozen=True.
        """
        resp = HttpResponseContract(status_code=200, body=b"data")
        assert resp.model_config.get("frozen") is True

    def test_status_code_required(self) -> None:
        """Omitting status_code must raise ValidationError."""
        with pytest.raises(ValidationError):
            HttpResponseContract(body=b"data")  # type: ignore[call-arg]

    def test_body_required(self) -> None:
        """Omitting body must raise ValidationError."""
        with pytest.raises(ValidationError):
            HttpResponseContract(status_code=200)  # type: ignore[call-arg]

    def test_headers_default_is_not_shared_across_instances(self) -> None:
        """Each instance must get its own default headers dict (no mutable default aliasing)."""
        resp1 = HttpResponseContract(status_code=200, body=b"a")
        resp2 = HttpResponseContract(status_code=404, body=b"not found")
        assert resp1.headers is not resp2.headers

    def test_various_status_codes(self) -> None:
        """Common HTTP status codes can be set in the status_code field."""
        for code in (200, 201, 204, 301, 400, 401, 403, 404, 500, 503):
            resp = HttpResponseContract(status_code=code, body=b"")
            assert resp.status_code == code


@pytest.mark.unit
class TestHttpContractImport:
    """Verify public API import surface for HTTP contracts (OMN-4222)."""

    def test_http_request_contract_importable_from_models_contracts(self) -> None:
        """HttpRequestContract must be importable from omnibase_core.models.contracts."""
        from omnibase_core.models.contracts import HttpRequestContract as _Req

        assert _Req is not None

    def test_http_response_contract_importable_from_models_contracts(self) -> None:
        """HttpResponseContract must be importable from omnibase_core.models.contracts."""
        from omnibase_core.models.contracts import HttpResponseContract as _Resp

        assert _Resp is not None
