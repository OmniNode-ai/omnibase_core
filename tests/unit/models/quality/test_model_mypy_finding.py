# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelMypyFinding + EnumLintSeverity (ADK eval spike, P2)."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_lint_severity import EnumLintSeverity
from omnibase_core.models.quality.model_mypy_finding import ModelMypyFinding


@pytest.mark.unit
class TestEnumLintSeverity:
    def test_values(self) -> None:
        assert EnumLintSeverity.ERROR.value == "error"
        assert EnumLintSeverity.NOTE.value == "note"
        assert EnumLintSeverity.WARNING.value == "warning"


@pytest.mark.unit
class TestModelMypyFinding:
    def test_valid_minimal(self) -> None:
        f = ModelMypyFinding(
            file="src/omnibase_core/foo.py",
            line=12,
            column=4,
            severity=EnumLintSeverity.ERROR,
            error_code="no-untyped-def",
            message="Function is missing a return type annotation",
        )
        assert f.file == "src/omnibase_core/foo.py"
        assert f.line == 12
        assert f.column == 4
        assert f.severity == EnumLintSeverity.ERROR
        assert f.error_code == "no-untyped-def"

    def test_column_optional(self) -> None:
        f = ModelMypyFinding(
            file="src/foo.py",
            line=10,
            column=None,
            severity=EnumLintSeverity.NOTE,
            error_code="note",
            message="See previous error",
        )
        assert f.column is None

    def test_invalid_severity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelMypyFinding(
                file="src/foo.py",
                line=1,
                column=1,
                severity="bogus",  # type: ignore[arg-type]
                error_code="x",
                message="y",
            )

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelMypyFinding(
                file="src/foo.py",
                line=1,
                column=1,
                severity=EnumLintSeverity.ERROR,
                error_code="x",
                message="y",
                unexpected="boom",  # type: ignore[call-arg]
            )

    def test_frozen(self) -> None:
        f = ModelMypyFinding(
            file="src/foo.py",
            line=1,
            column=1,
            severity=EnumLintSeverity.ERROR,
            error_code="x",
            message="y",
        )
        with pytest.raises(ValidationError):
            f.line = 2  # type: ignore[misc]

    def test_line_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            ModelMypyFinding(
                file="src/foo.py",
                line=0,
                column=0,
                severity=EnumLintSeverity.ERROR,
                error_code="x",
                message="y",
            )
