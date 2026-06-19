# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ValidatorNodePurity (OMN-13283)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.validator_node_purity import (
    EnumNodePurityRule,
    ValidatorNodePurity,
    main,
)

pytestmark = pytest.mark.unit


def _write_node(tmp_path: Path, name: str, body: str) -> Path:
    nodes_dir = tmp_path / "src" / "pkg" / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    target = nodes_dir / name
    target.write_text(body, encoding="utf-8")
    return target


def _write_non_node(tmp_path: Path, name: str, body: str) -> Path:
    other = tmp_path / "src" / "pkg" / "handlers"
    other.mkdir(parents=True, exist_ok=True)
    target = other / name
    target.write_text(body, encoding="utf-8")
    return target


def test_clean_node_has_no_violations(tmp_path: Path) -> None:
    f = _write_node(
        tmp_path, "node_clean.py", "def compute(x: int) -> int:\n    return x + 1\n"
    )
    assert ValidatorNodePurity().check_file(f) == []


def test_net_client_import_flagged(tmp_path: Path) -> None:
    f = _write_node(tmp_path, "node_bad.py", "import httpx\n")
    violations = ValidatorNodePurity().check_file(f)
    assert len(violations) == 1
    assert violations[0].rule is EnumNodePurityRule.NET_CLIENT


def test_env_getenv_flagged(tmp_path: Path) -> None:
    f = _write_node(tmp_path, "node_bad.py", "import os\n\nx = os.getenv('X')\n")
    violations = ValidatorNodePurity().check_file(f)
    assert any(v.rule is EnumNodePurityRule.ENV_ACCESS for v in violations)


def test_environ_subscript_flagged(tmp_path: Path) -> None:
    f = _write_node(tmp_path, "node_bad.py", "import os\n\nx = os.environ['X']\n")
    violations = ValidatorNodePurity().check_file(f)
    assert any(v.rule is EnumNodePurityRule.ENV_ACCESS for v in violations)


def test_open_call_flagged(tmp_path: Path) -> None:
    f = _write_node(tmp_path, "node_bad.py", "data = open('/etc/passwd').read()\n")
    violations = ValidatorNodePurity().check_file(f)
    assert any(v.rule is EnumNodePurityRule.FILE_IO for v in violations)


def test_pathlib_read_text_flagged(tmp_path: Path) -> None:
    body = (
        "from pathlib import Path\n\nfile_path = Path('a')\nx = file_path.read_text()\n"
    )
    f = _write_node(tmp_path, "node_bad.py", body)
    violations = ValidatorNodePurity().check_file(f)
    assert any(v.rule is EnumNodePurityRule.FILE_IO for v in violations)


def test_non_node_file_is_not_checked(tmp_path: Path) -> None:
    # Same forbidden content, but outside a 'nodes' directory -> not a node, skipped.
    f = _write_non_node(tmp_path, "handler_io.py", "import httpx\n")
    assert ValidatorNodePurity().check_file(f) == []


def test_type_checking_import_allowed(tmp_path: Path) -> None:
    body = "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    import httpx\n"
    f = _write_node(tmp_path, "node_tc.py", body)
    assert ValidatorNodePurity().check_file(f) == []


def test_inline_suppression_marker(tmp_path: Path) -> None:
    f = _write_node(
        tmp_path,
        "node_boundary.py",
        "import os\n\nx = os.getenv('X')  # node-purity-ok: bootstrap shim\n",
    )
    assert ValidatorNodePurity().check_file(f) == []


def test_cli_returns_zero_on_clean(tmp_path: Path) -> None:
    f = _write_node(tmp_path, "node_clean.py", "def f() -> int:\n    return 1\n")
    assert main([str(f), "--quiet"]) == 0


def test_cli_returns_one_on_violation(tmp_path: Path) -> None:
    f = _write_node(tmp_path, "node_bad.py", "import asyncpg\n")
    assert main([str(f), "--quiet"]) == 1
