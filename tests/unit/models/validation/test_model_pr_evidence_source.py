# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelPrEvidenceSource (OMN-14187)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_pr_evidence_source_kind import EnumPrEvidenceSourceKind
from omnibase_core.models.validation.model_pr_evidence_source import (
    ModelPrEvidenceSource,
)

_VALID_SHA_40 = "a" * 40
_VALID_SHA_7 = "0123abc"


@pytest.mark.unit
class TestModelPrEvidenceSource:
    def test_valid_occ_pr_variant(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.OCC_PR, occ_pr_number=123
        )
        assert src.occ_pr_number == 123
        assert src.commit_sha is None

    def test_valid_commit_sha_variant(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.COMMIT_SHA, commit_sha=_VALID_SHA_40
        )
        assert src.commit_sha == _VALID_SHA_40
        assert src.occ_pr_number is None

    def test_occ_pr_with_commit_sha_also_set_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrEvidenceSource(
                kind=EnumPrEvidenceSourceKind.OCC_PR,
                occ_pr_number=123,
                commit_sha=_VALID_SHA_40,
            )

    def test_occ_pr_without_number_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrEvidenceSource(kind=EnumPrEvidenceSourceKind.OCC_PR)

    def test_commit_sha_without_sha_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrEvidenceSource(kind=EnumPrEvidenceSourceKind.COMMIT_SHA)

    def test_commit_sha_kind_with_occ_number_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrEvidenceSource(
                kind=EnumPrEvidenceSourceKind.COMMIT_SHA,
                commit_sha=_VALID_SHA_40,
                occ_pr_number=5,
            )

    def test_occ_pr_number_zero_raises_ge1(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrEvidenceSource(kind=EnumPrEvidenceSourceKind.OCC_PR, occ_pr_number=0)

    @pytest.mark.parametrize(
        "bad_sha",
        [
            "z" * 40,  # invalid hex chars
            "abc",  # too short (<7)
            "a" * 41,  # too long (>40)
            "ABCDEF0",  # uppercase not permitted by [0-9a-f]
        ],
    )
    def test_invalid_commit_sha_pattern_raises(self, bad_sha: str) -> None:
        with pytest.raises(ValidationError):
            ModelPrEvidenceSource(
                kind=EnumPrEvidenceSourceKind.COMMIT_SHA, commit_sha=bad_sha
            )

    def test_valid_short_sha_boundary_7(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.COMMIT_SHA, commit_sha=_VALID_SHA_7
        )
        assert src.commit_sha == _VALID_SHA_7

    def test_render_token_occ_pr(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.OCC_PR, occ_pr_number=123
        )
        assert src.render_token() == "OCC#123"

    def test_render_token_commit_sha(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.COMMIT_SHA, commit_sha=_VALID_SHA_40
        )
        assert src.render_token() == _VALID_SHA_40

    def test_url_optional_field(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.OCC_PR,
            occ_pr_number=7,
            url="https://github.com/OmniNode-ai/onex_change_control/pull/7",
        )
        assert src.url is not None

    def test_roundtrip_model_dump(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.OCC_PR, occ_pr_number=999
        )
        restored = ModelPrEvidenceSource.model_validate(src.model_dump())
        assert restored == src

    def test_roundtrip_model_dump_json(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.COMMIT_SHA, commit_sha=_VALID_SHA_40
        )
        restored = ModelPrEvidenceSource.model_validate_json(src.model_dump_json())
        assert restored == src

    def test_frozen_attribute_mutation_raises(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.OCC_PR, occ_pr_number=1
        )
        with pytest.raises(ValidationError):
            src.occ_pr_number = 2  # type: ignore[misc]

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrEvidenceSource(
                kind=EnumPrEvidenceSourceKind.OCC_PR,
                occ_pr_number=1,
                bogus="x",  # type: ignore[call-arg]
            )

    def test_to_json_deterministic(self) -> None:
        src = ModelPrEvidenceSource(
            kind=EnumPrEvidenceSourceKind.OCC_PR, occ_pr_number=42
        )
        assert src.to_json() == src.to_json()
        assert '"kind":"occ_pr"' in src.to_json()
