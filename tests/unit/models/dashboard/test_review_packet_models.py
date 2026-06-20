# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelReviewPacket and ModelOmniStudioEvidenceBundle (OMN-13387).

Covers: frozen immutability, ``extra="forbid"``, required fields, sha256-ref
validation, typed ``receipt_gate_result``, and — critically — the determinism
of ``compute_packet_hash`` and the order-independence of
``compute_bundle_fingerprint``.
"""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.ticket.model_receipt_gate_result import (
    ModelReceiptGateResult,
)
from omnibase_core.models.dashboard import (
    ModelOmniStudioEvidenceBundle,
    ModelReviewPacket,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _sha256_ref(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _make_packet(
    *,
    source: bytes = b"contract",
    ir: bytes = b"ir",
    patch: bytes = b"patch",
    passed: bool = True,
) -> ModelReviewPacket:
    return ModelReviewPacket(
        source_contract_hash=_sha256_ref(source),
        ir_hash=_sha256_ref(ir),
        patch_hash=_sha256_ref(patch),
        validation_pipeline_version=ModelSemVer(major=1, minor=2, patch=3),
        receipt_gate_result=ModelReceiptGateResult(passed=passed, message="ok"),
    )


# --------------------------------------------------------------------------- #
# ModelReviewPacket
# --------------------------------------------------------------------------- #


def test_review_packet_required_fields_and_types() -> None:
    packet = _make_packet()
    assert packet.source_contract_hash.startswith("sha256:")
    assert packet.ir_hash.startswith("sha256:")
    assert packet.patch_hash.startswith("sha256:")
    assert isinstance(packet.validation_pipeline_version, ModelSemVer)
    assert isinstance(packet.receipt_gate_result, ModelReceiptGateResult)
    assert packet.receipt_gate_result.passed is True


def test_review_packet_is_frozen() -> None:
    packet = _make_packet()
    with pytest.raises(ValidationError):
        packet.ir_hash = _sha256_ref(b"other")  # type: ignore[misc]


def test_review_packet_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ModelReviewPacket(
            source_contract_hash=_sha256_ref(b"a"),
            ir_hash=_sha256_ref(b"b"),
            patch_hash=_sha256_ref(b"c"),
            validation_pipeline_version=ModelSemVer(major=1, minor=0, patch=0),
            receipt_gate_result=ModelReceiptGateResult(passed=True),
            extra_field="nope",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize(
    "bad_hash",
    [
        "not-a-hash",
        "sha256:tooshort",
        "md5:" + "0" * 32,
        "sha256:" + "X" * 64,  # uppercase / non-hex
        "sha256:" + "0" * 63,  # one char short
        "",
    ],
)
def test_review_packet_rejects_malformed_hash(bad_hash: str) -> None:
    with pytest.raises(ValidationError):
        ModelReviewPacket(
            source_contract_hash=bad_hash,
            ir_hash=_sha256_ref(b"b"),
            patch_hash=_sha256_ref(b"c"),
            validation_pipeline_version=ModelSemVer(major=1, minor=0, patch=0),
            receipt_gate_result=ModelReceiptGateResult(passed=True),
        )


def test_review_packet_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        ModelReviewPacket(  # type: ignore[call-arg]
            ir_hash=_sha256_ref(b"b"),
            patch_hash=_sha256_ref(b"c"),
            validation_pipeline_version=ModelSemVer(major=1, minor=0, patch=0),
            receipt_gate_result=ModelReceiptGateResult(passed=True),
        )


def test_packet_hash_is_sha256_prefixed() -> None:
    packet = _make_packet()
    digest = packet.compute_packet_hash()
    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64


def test_packet_hash_is_deterministic_across_instances() -> None:
    # Two independently constructed packets with identical fields must hash equal.
    a = _make_packet()
    b = _make_packet()
    assert a.compute_packet_hash() == b.compute_packet_hash()


def test_packet_hash_is_stable_across_repeated_calls() -> None:
    packet = _make_packet()
    assert packet.compute_packet_hash() == packet.compute_packet_hash()


def test_packet_hash_changes_when_any_field_changes() -> None:
    base = _make_packet().compute_packet_hash()
    assert _make_packet(source=b"different").compute_packet_hash() != base
    assert _make_packet(ir=b"different").compute_packet_hash() != base
    assert _make_packet(patch=b"different").compute_packet_hash() != base
    assert _make_packet(passed=False).compute_packet_hash() != base


def test_packet_hash_changes_with_pipeline_version() -> None:
    a = _make_packet()
    b = ModelReviewPacket(
        source_contract_hash=a.source_contract_hash,
        ir_hash=a.ir_hash,
        patch_hash=a.patch_hash,
        validation_pipeline_version=ModelSemVer(major=9, minor=9, patch=9),
        receipt_gate_result=a.receipt_gate_result,
    )
    assert a.compute_packet_hash() != b.compute_packet_hash()


# --------------------------------------------------------------------------- #
# ModelOmniStudioEvidenceBundle
# --------------------------------------------------------------------------- #


def test_bundle_required_fields_and_defaults() -> None:
    bundle = ModelOmniStudioEvidenceBundle(session_id="sess-1")
    assert bundle.session_id == "sess-1"
    assert bundle.packets == ()


def test_bundle_is_frozen() -> None:
    bundle = ModelOmniStudioEvidenceBundle(session_id="sess-1")
    with pytest.raises(ValidationError):
        bundle.session_id = "other"  # type: ignore[misc]


def test_bundle_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ModelOmniStudioEvidenceBundle(
            session_id="sess-1",
            extra="nope",  # type: ignore[call-arg]
        )


def test_bundle_rejects_empty_session_id() -> None:
    with pytest.raises(ValidationError):
        ModelOmniStudioEvidenceBundle(session_id="")


def test_bundle_fingerprint_is_sha256_prefixed() -> None:
    bundle = ModelOmniStudioEvidenceBundle(
        session_id="sess-1", packets=(_make_packet(),)
    )
    fp = bundle.compute_bundle_fingerprint()
    assert fp.startswith("sha256:")
    assert len(fp) == len("sha256:") + 64


def test_bundle_fingerprint_is_order_independent() -> None:
    p1 = _make_packet(source=b"one")
    p2 = _make_packet(source=b"two")
    p3 = _make_packet(source=b"three")
    forward = ModelOmniStudioEvidenceBundle(session_id="s", packets=(p1, p2, p3))
    reversed_ = ModelOmniStudioEvidenceBundle(session_id="s", packets=(p3, p2, p1))
    assert (
        forward.compute_bundle_fingerprint() == reversed_.compute_bundle_fingerprint()
    )


def test_bundle_fingerprint_is_deterministic_across_instances() -> None:
    a = ModelOmniStudioEvidenceBundle(session_id="s", packets=(_make_packet(),))
    b = ModelOmniStudioEvidenceBundle(session_id="s", packets=(_make_packet(),))
    assert a.compute_bundle_fingerprint() == b.compute_bundle_fingerprint()


def test_bundle_fingerprint_changes_with_session_id() -> None:
    packets = (_make_packet(),)
    a = ModelOmniStudioEvidenceBundle(session_id="s1", packets=packets)
    b = ModelOmniStudioEvidenceBundle(session_id="s2", packets=packets)
    assert a.compute_bundle_fingerprint() != b.compute_bundle_fingerprint()


def test_bundle_fingerprint_changes_with_packet_set() -> None:
    one = ModelOmniStudioEvidenceBundle(
        session_id="s", packets=(_make_packet(source=b"one"),)
    )
    two = ModelOmniStudioEvidenceBundle(
        session_id="s",
        packets=(_make_packet(source=b"one"), _make_packet(source=b"two")),
    )
    assert one.compute_bundle_fingerprint() != two.compute_bundle_fingerprint()


def test_empty_bundle_fingerprint_is_stable() -> None:
    a = ModelOmniStudioEvidenceBundle(session_id="s")
    b = ModelOmniStudioEvidenceBundle(session_id="s")
    assert a.compute_bundle_fingerprint() == b.compute_bundle_fingerprint()
