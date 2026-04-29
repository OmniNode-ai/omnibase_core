# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for Gate 5 — banned **kwargs: object / **kwargs: Any in Protocol methods."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.cli.substrate_gates.protocol_kwargs_object import (
    ProtocolKwargsObjectGate,
    main,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def gate() -> ProtocolKwargsObjectGate:
    return ProtocolKwargsObjectGate()


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


class TestProtocolKwargsObjectGate:
    def test_violation_file_flags_all_banned_methods(
        self, gate: ProtocolKwargsObjectGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "kwargs_violation.py"])
        # 6 violating methods: execute(**kwargs:object), run(**kwargs:Any),
        # call(*args:object), invoke(*args:Any), dispatch(*both:Any x2), process(*both:object x2)
        assert len(violations) == 8
        messages = [v.message for v in violations]
        assert any("**kwargs: object" in m for m in messages)
        assert any("**kwargs: Any" in m for m in messages)
        assert any("*args: object" in m for m in messages)
        assert any("*args: Any" in m for m in messages)

    def test_clean_file_has_no_violations(
        self, gate: ProtocolKwargsObjectGate, fixtures_dir: Path
    ) -> None:
        violations = gate.run([fixtures_dir / "kwargs_clean.py"])
        assert violations == []

    def test_empty_input_returns_empty(self, gate: ProtocolKwargsObjectGate) -> None:
        assert gate.run([]) == []

    def test_non_protocol_class_ignored(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "non_protocol.py"
        f.write_text(
            "from typing import Any\n"
            "class Foo:\n"
            "    def run(self, **kwargs: Any) -> None: ...\n"
        )
        assert gate.run([f]) == []

    def test_protocol_kwargs_object_flagged(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text(
            "from typing import Protocol\n"
            "class MyProto(Protocol):\n"
            "    def execute(self, **kwargs: object) -> None: ...\n"
        )
        violations = gate.run([f])
        assert len(violations) == 1
        assert "**kwargs: object" in violations[0].message
        assert "execute" in violations[0].message

    def test_protocol_kwargs_any_flagged(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text(
            "from typing import Any, Protocol\n"
            "class MyProto(Protocol):\n"
            "    def run(self, **kwargs: Any) -> None: ...\n"
        )
        violations = gate.run([f])
        assert len(violations) == 1
        assert "**kwargs: Any" in violations[0].message

    def test_protocol_args_object_flagged(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text(
            "from typing import Protocol\n"
            "class MyProto(Protocol):\n"
            "    def call(self, *args: object) -> None: ...\n"
        )
        violations = gate.run([f])
        assert len(violations) == 1
        assert "*args: object" in violations[0].message

    def test_protocol_args_any_flagged(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text(
            "from typing import Any, Protocol\n"
            "class MyProto(Protocol):\n"
            "    def invoke(self, *args: Any) -> None: ...\n"
        )
        violations = gate.run([f])
        assert len(violations) == 1
        assert "*args: Any" in violations[0].message

    def test_both_args_and_kwargs_both_banned_flagged(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text(
            "from typing import Any, Protocol\n"
            "class MyProto(Protocol):\n"
            "    def dispatch(self, *args: Any, **kwargs: Any) -> None: ...\n"
        )
        violations = gate.run([f])
        assert len(violations) == 2

    def test_allow_annotation_suppresses(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "allowed.py"
        f.write_text(
            "from typing import Protocol\n"
            "class MyProto(Protocol):\n"
            "    def execute(self, **kwargs: object) -> None: ...  # substrate-allow: vestigial\n"
        )
        assert gate.run([f]) == []

    def test_typed_kwargs_not_flagged(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "ok.py"
        f.write_text(
            "from typing import Protocol\n"
            "class MyProto(Protocol):\n"
            "    def run(self, **kwargs: str) -> None: ...\n"
        )
        assert gate.run([f]) == []

    def test_untyped_varargs_not_flagged(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "ok.py"
        f.write_text(
            "from typing import Protocol\n"
            "class MyProto(Protocol):\n"
            "    def run(self, *args, **kwargs) -> None: ...\n"
        )
        assert gate.run([f]) == []

    def test_typing_extensions_protocol_flagged(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text(
            "import typing_extensions\n"
            "class MyProto(typing_extensions.Protocol):\n"
            "    def run(self, **kwargs: object) -> None: ...\n"
        )
        violations = gate.run([f])
        assert len(violations) == 1

    def test_violation_line_number_correct(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text(
            "from typing import Protocol\n"
            "\n"
            "class MyProto(Protocol):\n"
            "    def execute(self, **kwargs: object) -> None: ...\n"
        )
        violations = gate.run([f])
        assert len(violations) == 1
        assert violations[0].line == 4

    def test_syntax_error_reported_as_violation(
        self, gate: ProtocolKwargsObjectGate, tmp_path: Path
    ) -> None:
        f = tmp_path / "broken.py"
        f.write_text("def foo(\n")
        violations = gate.run([f])
        assert len(violations) == 1
        assert "syntax error" in violations[0].message.lower()


class TestMain:
    def test_clean_file_exits_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "ok.py"
        f.write_text("x = 1\n")
        assert main([str(f)]) == 0

    def test_violation_exits_one(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text(
            "from typing import Protocol\n"
            "class P(Protocol):\n"
            "    def run(self, **kwargs: object) -> None: ...\n"
        )
        assert main([str(f)]) == 1

    def test_no_args_exits_zero(self) -> None:
        assert main([]) == 0
