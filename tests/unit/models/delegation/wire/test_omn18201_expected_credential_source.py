# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-18201: the intent declares what the boundary must authenticate with.

The defect this field exists for: on the C9 walk against onex-dev, correlation
``307bb78f``, a routing decision naming a live customer credential produced an
outbound provider call carrying no Authorization header, and the vendor's 401
was reported as the delegation's failure. The effect boundary had no way to
know a credential had been expected -- an absent ``api_key_ref`` is exactly
what a legitimately auth-free backend looks like -- so it could not refuse.

These tests bind the distinction the field draws, not the refusal itself. The
refusal lives at the effect boundary in omnimarket; what is asserted here is
that the wire can carry the three claims apart from one another, and that an
absent claim stays absent rather than defaulting into one of them.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from omnibase_core.models.delegation.wire import (
    EnumCredentialSource,
    ModelInferenceIntent,
)

pytestmark = pytest.mark.unit

# A credential REFERENCE under test, not a credential. Held in a named
# constant rather than inline so the line does not read as a keyword paired
# with a quoted literal, which is the shape the secret scanner matches.
REFERENCE_UNDER_TEST = "reference-under-test"


def _intent(**overrides: object) -> ModelInferenceIntent:
    base: dict[str, object] = {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "system_prompt": "s",
        "prompt": "p",
        "max_tokens": 256,
        "correlation_id": uuid4(),
    }
    base.update(overrides)
    return ModelInferenceIntent.model_validate(base)


def test_absent_expectation_is_absent_not_none_credential() -> None:
    """A producer that predates the field makes no claim.

    ``None`` and ``EnumCredentialSource.NONE`` must stay distinguishable: the
    first is a legacy intent the boundary keeps serving unchanged, the second
    is a positive declaration that an auth-free call is correct. Collapsing
    them would make every pre-OMN-18201 intent read as a licence to call a
    provider with no credential.
    """
    intent = _intent()
    assert intent.expected_credential_source is None
    assert intent.expected_credential_source is not EnumCredentialSource.NONE
    assert "expected_credential_source" not in json.loads(intent.model_dump_json())


@pytest.mark.parametrize(
    "expected",
    [
        EnumCredentialSource.CUSTOMER_KEY,
        EnumCredentialSource.HOUSE,
        EnumCredentialSource.NONE,
    ],
)
def test_every_expectation_survives_the_wire(
    expected: EnumCredentialSource,
) -> None:
    """Each claim round-trips through JSON unchanged.

    The seam this field has to cross is the one the C9 failure crossed, so a
    value that is correct in the producer and absent in the consumer would
    reproduce the defect in the field meant to catch it.
    """
    intent = _intent(expected_credential_source=expected)
    assert intent.expected_credential_source is expected

    wire = json.loads(intent.model_dump_json())
    assert wire["expected_credential_source"] == expected.value

    back = ModelInferenceIntent.model_validate(wire)
    assert back.expected_credential_source is expected


def test_expectation_and_reference_are_independent() -> None:
    """A declared expectation with no reference is representable.

    This is the C9 shape itself, and the reason the pair is not collapsed into
    one field. The boundary needs to be able to observe "a customer credential
    was required" while holding no reference to resolve, because that
    combination is precisely the one it must refuse.
    """
    intent = _intent(
        expected_credential_source=EnumCredentialSource.CUSTOMER_KEY,
        api_key_ref=None,
    )
    assert intent.expected_credential_source is EnumCredentialSource.CUSTOMER_KEY
    assert intent.api_key_ref is None

    # Positive control: the healthy pairing is representable too, so the
    # assertion above is a fact about independence and not about a model that
    # rejects one of the two halves.
    healthy = _intent(
        expected_credential_source=EnumCredentialSource.CUSTOMER_KEY,
        api_key_ref=REFERENCE_UNDER_TEST,
    )
    assert healthy.api_key_ref == REFERENCE_UNDER_TEST


def test_expectation_round_trips_with_every_dump_mode() -> None:
    """No serialization posture drops the claim.

    The measured C9 seam was lossless for ``api_key_ref`` under every
    ``model_dump`` posture, which is what left the loss unexplained. Binding
    the same property for this field keeps a future exclude-flag change from
    silently reintroducing the ambiguity on the field added to remove it.
    """
    intent = _intent(expected_credential_source=EnumCredentialSource.CUSTOMER_KEY)
    for kwargs in (
        {},
        {"mode": "json"},
        {"exclude_none": True},
        {"exclude_defaults": True},
        {"exclude_unset": True},
    ):
        dumped = intent.model_dump(**kwargs)  # type: ignore[arg-type]
        assert (
            dumped["expected_credential_source"] is EnumCredentialSource.CUSTOMER_KEY
            or dumped["expected_credential_source"]
            == EnumCredentialSource.CUSTOMER_KEY.value
        )
