# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumPrEvidenceSourceKind (OMN-14187)."""

from __future__ import annotations

from enum import Enum, StrEnum

import pytest

from omnibase_core.enums.enum_pr_evidence_source_kind import EnumPrEvidenceSourceKind


@pytest.mark.unit
class TestEnumPrEvidenceSourceKind:
    def test_members_exist_with_expected_values(self) -> None:
        assert EnumPrEvidenceSourceKind.OCC_PR == "occ_pr"
        assert EnumPrEvidenceSourceKind.COMMIT_SHA == "commit_sha"

    def test_exactly_two_members(self) -> None:
        assert {member.value for member in EnumPrEvidenceSourceKind} == {
            "occ_pr",
            "commit_sha",
        }

    def test_strenum_inheritance(self) -> None:
        assert issubclass(EnumPrEvidenceSourceKind, StrEnum)
        assert issubclass(EnumPrEvidenceSourceKind, str)
        assert issubclass(EnumPrEvidenceSourceKind, Enum)

    def test_string_equality_with_plain_strings(self) -> None:
        # StrEnum members compare equal to their plain-string value.
        assert EnumPrEvidenceSourceKind.OCC_PR == "occ_pr"
        assert EnumPrEvidenceSourceKind("occ_pr") is EnumPrEvidenceSourceKind.OCC_PR
        assert str(EnumPrEvidenceSourceKind.COMMIT_SHA) == "commit_sha"
