# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire-contract controls for customer-to-cloud ingest."""

import inspect

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts import model_ingest_contract
from omnibase_core.models.contracts.model_ingest_contract import (
    CLIENT_HEADER_SET,
    HEADER_BUDGET_MARGIN,
    IDENTITY_HEADERS,
    SLUG_GRAMMAR,
    ModelIngestOverlay,
    canonical_topic,
    compute_event_id,
)

_TOPIC = "onex.evt.test.record.v1"

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("key", "headers", "expected"),
    [
        (
            None,
            (),
            (
                b"\xe6\x0e\x2a\x5c\x58\xe6\x62\xc2\x06\x3d\xb3\xd1\xf4\x34\x98\x16"
                b"\xda\xd8\x61\x74\x55\x4f\x4e\x14\x9f\xa6\x93\xae\x86\x29\xdc\x01"
            ),
        ),
        (
            b"",
            (("message-id", b""),),
            (
                b"\x26\x90\xe5\xf2\x0f\x62\x81\xbd\x90\x64\xf5\xc8\x7a\xcc\xd1\x68"
                b"\xf3\x94\xd1\xcf\x96\x57\x6e\xeb\xc2\xe2\x1e\xb2\x9a\xa7\xc2\x91"
            ),
        ),
        (
            b"\xffkey",
            (("message-id", b"\x02\xff"),),
            (
                b"\x59\x96\x24\x2c\xb1\xf7\x3a\x91\x96\x32\x94\x2e\x3c\xef\x04\x03"
                b"\xcf\x62\x92\x15\x1a\x4c\x11\x13\x92\xe6\xc0\x26\xec\x5f\x03\xf1"
            ),
        ),
    ],
)
def test_event_identity_pinned_vectors(
    key: bytes | None, headers: tuple[tuple[str, bytes], ...], expected: bytes
) -> None:
    assert compute_event_id(_TOPIC, key, b"\x00\xff", headers) == expected.hex()


def test_event_identity_key_presence_and_bytes() -> None:
    identities = {
        compute_event_id(_TOPIC, key, b"value", ()) for key in (None, b"", b"a", b"b")
    }
    assert len(identities) == 4


def test_event_identity_header_presence_and_bytes() -> None:
    identities = {
        compute_event_id(_TOPIC, None, b"value", headers)
        for headers in (
            {},
            {"message-id": b""},
            {"message-id": b"a"},
            {"message-id": b"b"},
        )
    }
    assert len(identities) == 4


def test_event_identity_header_case_and_non_identity_headers() -> None:
    assert IDENTITY_HEADERS == ("message-id",)
    expected = compute_event_id(_TOPIC, None, b"value", {"message-id": b"a"})
    assert expected == compute_event_id(
        _TOPIC,
        None,
        b"value",
        (("source", b"unhashed"), ("message_id", b"unhashed"), ("Message-ID", b"a")),
    )


def test_event_identity_refuses_repeated_identity_header() -> None:
    with pytest.raises(ValueError, match=r"^identity-header-duplicate$"):
        compute_event_id(
            _TOPIC, None, b"value", (("message-id", b"a"), ("Message-ID", b"a"))
        )


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (("evt", b"a\x01b", b"v", b"h"), ("evt\x01a", b"b", b"v", b"h")),
        (("evt", b"a", b"bc", b"h"), ("evt", b"ab", b"c", b"h")),
        (
            ("evt", b"k", b"v", b"amessage-id\x01b"),
            ("evt", b"k", b"vmessage-id\x01a", b"b"),
        ),
    ],
    ids=["topic-key", "key-value", "value-header"],
)
def test_event_identity_field_boundaries(
    first: tuple[str, bytes, bytes, bytes], second: tuple[str, bytes, bytes, bytes]
) -> None:
    topic_a, key_a, value_a, header_a = first
    topic_b, key_b, value_b, header_b = second
    assert compute_event_id(
        topic_a, key_a, value_a, {"message-id": header_a}
    ) != compute_event_id(topic_b, key_b, value_b, {"message-id": header_b})


def test_event_identity_single_export_list() -> None:
    functions = {"canonical_topic", "compute_event_id"}
    assert set(model_ingest_contract.__all__) == functions | {
        "CLIENT_HEADER_SET",
        "HEADER_BUDGET_MARGIN",
        "IDENTITY_HEADERS",
        "SLUG_GRAMMAR",
        "ModelIngestOverlay",
    }
    assert {
        name
        for name, member in inspect.getmembers(
            model_ingest_contract, inspect.isfunction
        )
        if not name.startswith("_")
    } == functions


def test_event_identity_single_overlay_refuses_identity() -> None:
    class _ExampleOverlay(ModelIngestOverlay):
        max_batch_records: int

    assert (
        _ExampleOverlay.model_validate({"max_batch_records": 1}).max_batch_records == 1
    )
    for model in (ModelIngestOverlay, _ExampleOverlay):
        fields = {"max_batch_records": 1} if model is _ExampleOverlay else {}
        with pytest.raises(ValidationError) as error:
            model.model_validate({**fields, "identity": "envelope_payload"})
        assert [(item["loc"], item["type"]) for item in error.value.errors()] == [
            (("identity",), "extra_forbidden")
        ]


@pytest.mark.parametrize("slug", ["0", "a-b9", "a" + "-" * 30 + "0"])
def test_topic_normalization_accepts_slug(slug: str) -> None:
    assert SLUG_GRAMMAR.fullmatch(slug)
    assert canonical_topic(f"tenant-{slug}.{_TOPIC}") == _TOPIC


@pytest.mark.parametrize(
    "topic",
    [
        "tenant-a",
        "tenant-.evt",
        "tenant-A.evt",
        "tenant-\N{KELVIN SIGN}.evt",
        "tenant-a_b.evt",
        "tenant-a/b.evt",
        "tenant-a%2db.evt",
        "tenant--a.evt",
        "tenant-a-.evt",
        "tenant-a\n.evt",
        "tenant-a .evt",
        f"tenant-{'a' * 33}.evt",
    ],
)
def test_topic_normalization_rejects_malformed_prefix(topic: str) -> None:
    with pytest.raises(ValueError, match=r"^topic-malformed$"):
        canonical_topic(topic)
    with pytest.raises(ValueError, match=r"^topic-malformed$"):
        compute_event_id(topic, None, b"value", ())


def test_topic_normalization_removes_one_prefix() -> None:
    assert canonical_topic(f"tenant-a.tenant-b.{_TOPIC}") == f"tenant-b.{_TOPIC}"


@pytest.mark.parametrize("topic", [_TOPIC, " onex.EVT.%2E..é ", "TENANT-a.evt"])
def test_topic_normalization_keeps_other_text_verbatim(topic: str) -> None:
    assert canonical_topic(topic) == topic
    assert canonical_topic(f"tenant-a.{topic}") == topic


def test_topic_normalization_wire_and_canonical_hash_match() -> None:
    expected = (
        b"\x24\xca\xb0\x87\x17\xa8\xc7\xfa\xe3\xbf\xe4\x37\x64\xb6\x95\xf6"
        b"\xe7\x23\x4d\x70\x56\x49\xf8\x68\x08\x58\x79\x45\x4d\xdc\x2b\x50"
    )
    headers = {"message-id": b"record-a"}
    assert compute_event_id(_TOPIC, b"key", b"value", headers) == expected.hex()
    assert (
        compute_event_id(f"tenant-a.{_TOPIC}", b"key", b"value", headers)
        == expected.hex()
    )


def test_event_identity_client_header_budget() -> None:
    assert CLIENT_HEADER_SET == {
        "host": 260,
        "authorization": "max_authorization_bytes",
        "idempotency-key": 64,
        "content-type": 16,
        "content-length": 20,
    }
    assert HEADER_BUDGET_MARGIN == (4, 25)
