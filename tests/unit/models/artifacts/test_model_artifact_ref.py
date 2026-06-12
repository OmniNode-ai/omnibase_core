# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelArtifactRef content-addressed artifact reference (OMN-13091)."""

from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from omnibase_core.models.artifacts.model_artifact_ref import ModelArtifactRef

_VALID_HEX = "a" * 64
_VALID_REF = f"sha256:{_VALID_HEX}"


@pytest.mark.unit
class TestModelArtifactRefConstruction:
    """Valid construction paths."""

    def test_valid_ref_accepted(self) -> None:
        ref = ModelArtifactRef(ref=_VALID_REF)
        assert ref.ref == _VALID_REF

    def test_real_digest_accepted(self) -> None:
        digest = hashlib.sha256(b"payload").hexdigest()
        ref = ModelArtifactRef(ref=f"sha256:{digest}")
        assert ref.hex_digest == digest

    def test_from_bytes_computes_sha256(self) -> None:
        data = b"hello artifact store"
        ref = ModelArtifactRef.from_bytes(data)
        assert ref.ref == f"sha256:{hashlib.sha256(data).hexdigest()}"

    def test_from_bytes_is_deterministic(self) -> None:
        assert ModelArtifactRef.from_bytes(b"x") == ModelArtifactRef.from_bytes(b"x")

    def test_hex_digest_strips_prefix(self) -> None:
        ref = ModelArtifactRef(ref=_VALID_REF)
        assert ref.hex_digest == _VALID_HEX


@pytest.mark.unit
class TestModelArtifactRefValidation:
    """Rejection of malformed refs."""

    @pytest.mark.parametrize(
        "bad_ref",
        [
            "",
            _VALID_HEX,  # missing prefix
            f"sha512:{_VALID_HEX}",  # wrong algorithm
            f"sha256:{'A' * 64}",  # uppercase hex
            f"sha256:{'a' * 63}",  # too short
            f"sha256:{'a' * 65}",  # too long
            f"sha256:{'g' * 64}",  # non-hex chars
            f" sha256:{_VALID_HEX}",  # leading whitespace
            f"sha256:{_VALID_HEX} ",  # trailing whitespace
            "sha256:",
        ],
    )
    def test_invalid_ref_rejected(self, bad_ref: str) -> None:
        with pytest.raises(ValidationError):
            ModelArtifactRef(ref=bad_ref)


@pytest.mark.unit
class TestModelArtifactRefContract:
    """Model contract: frozen, extra forbidden, serialization round-trip."""

    def test_frozen(self) -> None:
        ref = ModelArtifactRef(ref=_VALID_REF)
        with pytest.raises(ValidationError):
            ref.ref = f"sha256:{'b' * 64}"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelArtifactRef(ref=_VALID_REF, media_type="text/plain")  # type: ignore[call-arg]

    def test_json_round_trip(self) -> None:
        ref = ModelArtifactRef(ref=_VALID_REF)
        restored = ModelArtifactRef.model_validate_json(ref.model_dump_json())
        assert restored == ref

    def test_equality_by_value(self) -> None:
        assert ModelArtifactRef(ref=_VALID_REF) == ModelArtifactRef(ref=_VALID_REF)
