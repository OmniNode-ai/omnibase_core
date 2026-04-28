# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for Gate 1 — banned T | None = None on identity field names."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.cli.substrate_gates.identity_field_optionality import (
    IdentityFieldOptionalityCheck,
)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


class TestIdentityFieldOptionalityCheck:
    def test_violation_file_emits_violations(self, fixtures_dir: Path) -> None:
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([fixtures_dir / "identity_violation.py"])
        assert len(violations) >= 1, (
            "Expected at least one violation in identity_violation.py"
        )

    def test_clean_file_emits_no_violations(self, fixtures_dir: Path) -> None:
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([fixtures_dir / "identity_clean.py"])
        assert violations == [], (
            f"Unexpected violations in identity_clean.py: {violations}"
        )

    def test_pydantic_field_violation_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "model.py"
        f.write_text(
            "from __future__ import annotations\n"
            "from uuid import UUID\n"
            "from pydantic import BaseModel\n"
            "class M(BaseModel):\n"
            "    correlation_id: UUID | None = None\n"
        )
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([f])
        assert any("correlation_id" in v.message for v in violations)

    def test_function_arg_violation_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "handler.py"
        f.write_text(
            "from __future__ import annotations\n"
            "from uuid import UUID\n"
            "def handle(session_id: UUID | None = None) -> None: ...\n"
        )
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([f])
        assert any("session_id" in v.message for v in violations)

    def test_async_function_arg_violation_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "async_handler.py"
        f.write_text(
            "from __future__ import annotations\n"
            "from uuid import UUID\n"
            "async def handle(trace_id: str | None = None) -> None: ...\n"
        )
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([f])
        assert any("trace_id" in v.message for v in violations)

    def test_optional_syntax_violation_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "optional_model.py"
        f.write_text(
            "from __future__ import annotations\n"
            "from typing import Optional\n"
            "from uuid import UUID\n"
            "from pydantic import BaseModel\n"
            "class M(BaseModel):\n"
            "    tenant_id: Optional[UUID] = None\n"
        )
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([f])
        assert any("tenant_id" in v.message for v in violations)

    def test_substrate_allow_suppresses_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "allowed.py"
        f.write_text(
            "from __future__ import annotations\n"
            "from uuid import UUID\n"
            "from pydantic import BaseModel\n"
            "class M(BaseModel):\n"
            "    correlation_id: UUID | None = None  # substrate-allow: bootstrap-sentinel\n"
        )
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([f])
        assert violations == []

    def test_onex_exclude_suppresses_violation(self, tmp_path: Path) -> None:
        f = tmp_path / "excluded.py"
        f.write_text(
            "from __future__ import annotations\n"
            "from uuid import UUID\n"
            "def handle(run_id: UUID | None = None) -> None: ...  # ONEX_EXCLUDE: legacy\n"
        )
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([f])
        assert violations == []

    def test_parent_span_id_not_in_banned_list(self, tmp_path: Path) -> None:
        f = tmp_path / "parent_span.py"
        f.write_text(
            "from __future__ import annotations\n"
            "from uuid import UUID\n"
            "from pydantic import BaseModel\n"
            "class M(BaseModel):\n"
            "    parent_span_id: UUID | None = None\n"
        )
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([f])
        assert violations == [], "parent_span_id must NOT trip the gate"

    def test_non_identity_field_optional_not_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "non_identity.py"
        f.write_text(
            "from __future__ import annotations\n"
            "from pydantic import BaseModel\n"
            "class M(BaseModel):\n"
            "    description: str | None = None\n"
            "    metadata: dict | None = None\n"
        )
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([f])
        assert violations == []

    def test_identity_field_required_not_flagged(self, tmp_path: Path) -> None:
        f = tmp_path / "required.py"
        f.write_text(
            "from __future__ import annotations\n"
            "from uuid import UUID\n"
            "from pydantic import BaseModel\n"
            "class M(BaseModel):\n"
            "    correlation_id: UUID\n"
            "    session_id: str\n"
        )
        gate = IdentityFieldOptionalityCheck()
        violations = gate.run([f])
        assert violations == []

    def test_empty_input_returns_empty(self) -> None:
        gate = IdentityFieldOptionalityCheck()
        assert gate.run([]) == []

    def test_violation_file_exits_1(self, fixtures_dir: Path) -> None:
        from omnibase_core.cli.substrate_gates._base import main_for_gate

        result = main_for_gate(
            IdentityFieldOptionalityCheck(),
            [str(fixtures_dir / "identity_violation.py")],
        )
        assert result == 1

    def test_clean_file_exits_0(self, fixtures_dir: Path) -> None:
        from omnibase_core.cli.substrate_gates._base import main_for_gate

        result = main_for_gate(
            IdentityFieldOptionalityCheck(),
            [str(fixtures_dir / "identity_clean.py")],
        )
        assert result == 0
