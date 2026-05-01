# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelZonePolicy — per-zone QA gate configuration (OMN-10354)."""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_file_zone import EnumFileZone
from omnibase_core.models.validation.model_zone_policy import ModelZonePolicy


@pytest.mark.unit
class TestModelZonePolicy:
    def test_zone_policy_is_frozen(self) -> None:
        p = ModelZonePolicy(
            zone=EnumFileZone.PRODUCTION,
            qa_depth="full",
            requires_lint=True,
            requires_test=True,
            requires_review=True,
            requires_security_scan=True,
        )
        with pytest.raises(Exception):
            p.requires_lint = False  # type: ignore[misc]

    def test_zone_policy_qa_depth_validated(self) -> None:
        with pytest.raises(Exception):
            ModelZonePolicy(
                zone=EnumFileZone.DOCS,
                qa_depth="bogus",  # type: ignore[arg-type]
                requires_lint=False,
                requires_test=False,
                requires_review=False,
                requires_security_scan=False,
            )

    def test_zone_policy_valid_qa_depths(self) -> None:
        for depth in ("full", "standard", "light", "skip"):
            p = ModelZonePolicy(
                zone=EnumFileZone.TEST,
                qa_depth=depth,  # type: ignore[arg-type]
                requires_lint=False,
                requires_test=False,
                requires_review=False,
                requires_security_scan=False,
            )
            assert p.qa_depth == depth

    def test_zone_policy_all_zones_accepted(self) -> None:
        for zone in EnumFileZone:
            p = ModelZonePolicy(
                zone=zone,
                qa_depth="standard",
                requires_lint=True,
                requires_test=True,
                requires_review=False,
                requires_security_scan=False,
            )
            assert p.zone == zone

    def test_zone_policy_fields_accessible(self) -> None:
        p = ModelZonePolicy(
            zone=EnumFileZone.GENERATED,
            qa_depth="skip",
            requires_lint=False,
            requires_test=False,
            requires_review=False,
            requires_security_scan=False,
        )
        assert p.zone == EnumFileZone.GENERATED
        assert p.qa_depth == "skip"
        assert p.requires_lint is False
        assert p.requires_test is False
        assert p.requires_review is False
        assert p.requires_security_scan is False

    def test_zone_policy_zone_is_enum_file_zone(self) -> None:
        p = ModelZonePolicy(
            zone=EnumFileZone.CONFIG,
            qa_depth="light",
            requires_lint=True,
            requires_test=False,
            requires_review=False,
            requires_security_scan=False,
        )
        assert isinstance(p.zone, EnumFileZone)
