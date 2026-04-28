# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDodCheck merged fields (OMN-10066 Part A).

Verifies that core's ModelDodCheck absorbs the two OCC-side fields
(check_type, check_value) so OCC can re-export from core and delete its
local definition.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.ticket.model_dod_check import ModelDodCheck


@pytest.mark.unit
class TestModelDodCheckMergedFields:
    def test_occ_style_construction_succeeds(self) -> None:
        check = ModelDodCheck(check_type="command", check_value="uv run pytest")
        assert check.check_type == "command"
        assert check.check_value == "uv run pytest"

    def test_check_type_defaults_to_empty_string(self) -> None:
        check = ModelDodCheck()
        assert check.check_type == ""

    def test_check_value_defaults_to_empty_string(self) -> None:
        check = ModelDodCheck()
        assert check.check_value == ""

    def test_both_fields_optional_no_args(self) -> None:
        check = ModelDodCheck()
        assert isinstance(check, ModelDodCheck)

    def test_check_type_rejects_non_string(self) -> None:
        with pytest.raises(ValidationError):
            ModelDodCheck(  # NOTE(OMN-10066): intentional non-str input to assert validation
                check_type=123,  # type: ignore[arg-type]
                check_value="some value",
            )

    def test_check_value_rejects_non_string(self) -> None:
        with pytest.raises(ValidationError):
            ModelDodCheck(  # NOTE(OMN-10066): intentional non-str input to assert validation
                check_type="command",
                check_value=42,  # type: ignore[arg-type]
            )

    def test_behavior_proven_construction(self) -> None:
        check = ModelDodCheck(check_type="behavior_proven", check_value="test_name")
        assert check.check_type == "behavior_proven"
        assert check.check_value == "test_name"
