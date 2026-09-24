# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19385: the provider-boundary evidence keeps the raw provider response.

The D1 output-only bar (OMN-18932) judges two byte strings: what the provider
returned and what the caller received. Until this carrier existed only the
second reached the caller, so a JSON answer followed by prose could not be told
apart from a clean one. These tests pin the carrier's shape: exact text under a
bound, a hash and a byte count always, and nothing on the wire when unset.
"""

from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_delegation_output_shape import EnumDelegationOutputShape
from omnibase_core.models.delegation.wire import (
    MAX_RAW_RESPONSE_UTF8_BYTES,
    ModelDelegationContractEvidence,
    ModelDelegationRawResponse,
    ModelDelegationResult,
)

_SOURCE = "choices[0].message.content"
_CONTRACT_SHA = "a" * 64


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _evidence(**overrides: object) -> ModelDelegationContractEvidence:
    fields: dict[str, object] = {
        "conveyed": True,
        "validated": False,
        "output_shape": EnumDelegationOutputShape.JSON,
        "contract_sha256": _CONTRACT_SHA,
        "channel": "messages[0].content",
    }
    fields.update(overrides)
    return ModelDelegationContractEvidence.model_validate(fields)


@pytest.mark.unit
def test_from_provider_content_keeps_the_exact_text_hash_and_length() -> None:
    raw = '  {"score": 0.9}\n\nThat is my assessment.\n'

    carrier = ModelDelegationRawResponse.from_provider_content(
        raw, source_field=_SOURCE
    )

    assert carrier.text == raw
    assert carrier.sha256 == _sha(raw)
    assert carrier.utf8_bytes == len(raw.encode("utf-8"))
    assert carrier.source_field == _SOURCE
    assert carrier.retained is True


@pytest.mark.unit
def test_multibyte_text_is_measured_in_utf8_bytes_not_characters() -> None:
    raw = "résumé ✓"

    carrier = ModelDelegationRawResponse.from_provider_content(
        raw, source_field=_SOURCE
    )

    assert carrier.utf8_bytes == len(raw.encode("utf-8"))
    assert carrier.utf8_bytes > len(raw)


@pytest.mark.unit
def test_over_the_bound_keeps_the_hash_and_length_and_drops_the_text() -> None:
    raw = "x" * (MAX_RAW_RESPONSE_UTF8_BYTES + 1)

    carrier = ModelDelegationRawResponse.from_provider_content(
        raw, source_field=_SOURCE
    )

    assert carrier.text is None
    assert carrier.retained is False
    assert carrier.sha256 == _sha(raw)
    assert carrier.utf8_bytes == MAX_RAW_RESPONSE_UTF8_BYTES + 1


@pytest.mark.unit
def test_exactly_at_the_bound_is_retained() -> None:
    raw = "y" * MAX_RAW_RESPONSE_UTF8_BYTES

    carrier = ModelDelegationRawResponse.from_provider_content(
        raw, source_field=_SOURCE
    )

    assert carrier.text == raw


@pytest.mark.unit
def test_text_that_does_not_hash_to_its_sha256_is_refused() -> None:
    with pytest.raises(ValidationError, match="sha256"):
        ModelDelegationRawResponse(
            source_field=_SOURCE,
            sha256=_sha("the original"),
            utf8_bytes=len(b"a forgery!!!"),
            text="a forgery!!!",
        )


@pytest.mark.unit
def test_text_whose_length_disagrees_with_utf8_bytes_is_refused() -> None:
    raw = "abc"
    with pytest.raises(ValidationError, match="utf8_bytes"):
        ModelDelegationRawResponse(
            source_field=_SOURCE, sha256=_sha(raw), utf8_bytes=4, text=raw
        )


@pytest.mark.unit
def test_dropping_text_under_the_bound_is_refused() -> None:
    """A carrier may only omit text it was not allowed to keep."""
    with pytest.raises(ValidationError, match="bound"):
        ModelDelegationRawResponse(
            source_field=_SOURCE, sha256=_sha("abc"), utf8_bytes=3, text=None
        )


@pytest.mark.unit
def test_text_over_the_bound_is_refused() -> None:
    raw = "z" * (MAX_RAW_RESPONSE_UTF8_BYTES + 1)
    with pytest.raises(ValidationError, match="bound"):
        ModelDelegationRawResponse(
            source_field=_SOURCE,
            sha256=_sha(raw),
            utf8_bytes=len(raw.encode("utf-8")),
            text=raw,
        )


@pytest.mark.unit
def test_uppercase_sha256_is_refused() -> None:
    raw = "abc"
    with pytest.raises(ValidationError):
        ModelDelegationRawResponse(
            source_field=_SOURCE, sha256=_sha(raw).upper(), utf8_bytes=3, text=raw
        )


@pytest.mark.unit
def test_the_carrier_has_exactly_four_fields_and_forbids_extras() -> None:
    """Only the message content and its identity: no headers, no body fields."""
    assert set(ModelDelegationRawResponse.model_fields) == {
        "source_field",
        "sha256",
        "utf8_bytes",
        "text",
    }
    raw = "abc"
    with pytest.raises(ValidationError):
        ModelDelegationRawResponse.model_validate(
            {
                "source_field": _SOURCE,
                "sha256": _sha(raw),
                "utf8_bytes": 3,
                "text": raw,
                "headers": {},
            }
        )


@pytest.mark.unit
def test_unset_carrier_leaves_the_evidence_wire_shape_unchanged() -> None:
    """Consumer-first: a producer that sets nothing emits the pre-OMN-19385 keys."""
    dumped = _evidence().model_dump(mode="json")

    assert "raw_response" not in dumped
    assert set(dumped) == {
        "conveyed",
        "validated",
        "output_shape",
        "contract_sha256",
        "channel",
    }


@pytest.mark.unit
def test_the_gate_update_keeps_the_raw_response() -> None:
    raw = '{"score": 0.9}\nDone.'
    evidence = _evidence(
        raw_response=ModelDelegationRawResponse.from_provider_content(
            raw, source_field=_SOURCE
        )
    )

    validated = evidence.model_copy(update={"validated": True})

    assert validated.raw_response is not None
    assert validated.raw_response.text == raw


@pytest.mark.unit
def test_the_raw_response_rides_the_terminal_through_a_json_round_trip() -> None:
    raw = '{"score": 0.9}\n\nI double-checked the rubric.'
    terminal = ModelDelegationResult(
        correlation_id=uuid4(),
        task_type="document",
        model_used="provider/model",
        endpoint_url="https://example.invalid/v1",
        content='{"score": 0.9}',
        quality_passed=True,
        quality_score=1.0,
        latency_ms=1,
        prompt_tokens=1,
        completion_tokens=1,
        total_tokens=2,
        fallback_to_claude=False,
        response_contract_evidence=_evidence(
            validated=True,
            raw_response=ModelDelegationRawResponse.from_provider_content(
                raw, source_field=_SOURCE
            ),
        ),
    )

    decoded = ModelDelegationResult.model_validate_json(terminal.model_dump_json())

    evidence = decoded.response_contract_evidence
    assert evidence is not None
    assert evidence.raw_response is not None
    assert evidence.raw_response.text == raw
    assert evidence.raw_response.sha256 == _sha(raw)
