# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for Gate 2 — loose_typing_in_internal gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.cli.substrate_gates.loose_typing_in_internal import (
    LooseTypingInInternalGate,
)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def gate() -> LooseTypingInInternalGate:
    return LooseTypingInInternalGate()


class TestPydanticFieldViolations:
    def test_dict_str_any_field_detected(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_violation.py"])
        messages = [v.message for v in violations]
        assert any("dict[str, Any]" in m for m in messages)

    def test_any_field_detected(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_violation.py"])
        messages = [v.message for v in violations]
        assert any("Any" in m and "field annotation" in m for m in messages)

    def test_mapping_str_any_field_detected(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_violation.py"])
        messages = [v.message for v in violations]
        assert any("Mapping[str, Any]" in m for m in messages)


class TestProtocolMethodViolations:
    def test_protocol_any_arg_detected(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_violation.py"])
        messages = [v.message for v in violations]
        assert any("Any" in m and "argument" in m for m in messages)

    def test_protocol_dict_str_any_arg_detected(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_violation.py"])
        messages = [v.message for v in violations]
        assert any("dict[str, Any]" in m and "argument" in m for m in messages)


class TestKwargsViolations:
    def test_kwargs_any_detected(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_violation.py"])
        messages = [v.message for v in violations]
        assert any("**kwargs" in m and "Any" in m for m in messages)

    def test_kwargs_object_detected(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_violation.py"])
        messages = [v.message for v in violations]
        assert any("**kwargs" in m and "object" in m for m in messages)


class TestAllowAnnotationSuppression:
    def test_substrate_allow_suppresses(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_clean.py"])
        # ModelWithAllowAnnotation has dict[str, Any] with substrate-allow — must not appear
        lines = [v.line for v in violations]
        clean_src = (fixtures_dir / "loose_typing_clean.py").read_text()
        allow_lineno = next(
            i + 1
            for i, line in enumerate(clean_src.splitlines())
            if "substrate-allow" in line
        )
        assert allow_lineno not in lines

    def test_onex_exclude_compat(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_clean.py"])
        clean_src = (fixtures_dir / "loose_typing_clean.py").read_text()
        exclude_lineno = next(
            i + 1
            for i, line in enumerate(clean_src.splitlines())
            if "ONEX_EXCLUDE" in line
        )
        assert exclude_lineno not in [v.line for v in violations]

    def test_ai_slop_ok_compat(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_clean.py"])
        clean_src = (fixtures_dir / "loose_typing_clean.py").read_text()
        slop_lineno = next(
            i + 1
            for i, line in enumerate(clean_src.splitlines())
            if "ai-slop-ok" in line
        )
        assert slop_lineno not in [v.line for v in violations]


class TestCleanFilesProduceNoViolations:
    def test_clean_file_no_violations(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_clean.py"])
        assert violations == []

    def test_typed_dict_str_str_field_clean(
        self, gate: LooseTypingInInternalGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "clean_dict.py"
        f.write_text(
            "from pydantic import BaseModel\n"
            "class M(BaseModel):\n"
            "    tags: dict[str, str]\n"
        )
        assert gate.run([f]) == []

    def test_typed_basemodel_field_clean(
        self, gate: LooseTypingInInternalGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "typed_field.py"
        f.write_text(
            "from uuid import UUID\n"
            "from pydantic import BaseModel\n"
            "class M(BaseModel):\n"
            "    session_id: UUID\n"
        )
        assert gate.run([f]) == []

    def test_empty_input_returns_empty(self, gate: LooseTypingInInternalGate) -> None:
        assert gate.run([]) == []


class TestViolationCount:
    def test_violation_file_has_multiple_violations(
        self, gate: LooseTypingInInternalGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "loose_typing_violation.py"])
        # Violation file has: dict[str, Any] field, Any field, Mapping[str, Any] field,
        # Protocol Any arg, Protocol dict[str, Any] arg, **kwargs: Any, **kwargs: object
        assert len(violations) >= 7
