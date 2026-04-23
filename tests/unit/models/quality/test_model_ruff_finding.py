# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelRuffFinding (ADK eval spike, P2)."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.quality.model_ruff_finding import ModelRuffFinding


@pytest.mark.unit
class TestModelRuffFinding:
    def test_valid_minimal(self) -> None:
        f = ModelRuffFinding(
            file="src/omnibase_core/foo.py",
            line=42,
            column=7,
            rule="F401",
            message="'os' imported but unused",
            fix_available=True,
        )
        assert f.rule == "F401"
        assert f.fix_available is True

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelRuffFinding(
                file="src/foo.py",
                line=1,
                column=1,
                rule="E501",
                message="line too long",
                fix_available=False,
                surprise="boom",  # type: ignore[call-arg]
            )

    def test_frozen(self) -> None:
        f = ModelRuffFinding(
            file="src/foo.py",
            line=1,
            column=1,
            rule="E501",
            message="line too long",
            fix_available=False,
        )
        with pytest.raises(ValidationError):
            f.fix_available = True  # type: ignore[misc]
