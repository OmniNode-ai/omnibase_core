# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum

import pytest

from omnibase_core.enums.enum_file_zone import EnumFileZone


@pytest.mark.unit
class TestEnumFileZone:
    def test_enum_members(self) -> None:
        assert {z.value for z in EnumFileZone} == {
            "production",
            "test",
            "config",
            "generated",
            "docs",
            "build",
        }

    def test_enum_is_str_enum(self) -> None:
        assert EnumFileZone.PRODUCTION.value == "production"
        assert isinstance(EnumFileZone.PRODUCTION, str)
        assert issubclass(EnumFileZone, str)
        assert issubclass(EnumFileZone, Enum)

    def test_enum_string_behavior(self) -> None:
        assert str(EnumFileZone.TEST) == "test"
        assert EnumFileZone.DOCS == "docs"

    def test_enum_iteration(self) -> None:
        values = list(EnumFileZone)
        assert len(values) == 6

    def test_enum_membership(self) -> None:
        assert EnumFileZone.CONFIG in EnumFileZone
        assert "config" in [e.value for e in EnumFileZone]

    def test_enum_deserialization(self) -> None:
        assert EnumFileZone("production") == EnumFileZone.PRODUCTION
        assert EnumFileZone("generated") == EnumFileZone.GENERATED

    def test_enum_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            EnumFileZone("extension")  # EnumFileType domain, not zone

    def test_all_members_accessible(self) -> None:
        assert EnumFileZone.PRODUCTION == "production"
        assert EnumFileZone.TEST == "test"
        assert EnumFileZone.CONFIG == "config"
        assert EnumFileZone.GENERATED == "generated"
        assert EnumFileZone.DOCS == "docs"
        assert EnumFileZone.BUILD == "build"
