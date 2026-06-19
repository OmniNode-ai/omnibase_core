# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ValidatorTransportImport (OMN-13283)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.validator_transport_import import (
    ValidatorTransportImport,
    main,
)

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, name: str, body: str) -> Path:
    target = tmp_path / name
    target.write_text(body, encoding="utf-8")
    return target


def test_clean_file_has_no_violations(tmp_path: Path) -> None:
    f = _write(
        tmp_path,
        "node_clean.py",
        "from __future__ import annotations\n\nimport json\n\nx = json.dumps({})\n",
    )
    assert ValidatorTransportImport().check_file(f) == []


def test_direct_import_is_flagged(tmp_path: Path) -> None:
    f = _write(tmp_path, "node_bad.py", "import httpx\n")
    violations = ValidatorTransportImport().check_file(f)
    assert len(violations) == 1
    assert violations[0].module_name == "httpx"
    assert violations[0].line == 1


def test_from_import_is_flagged(tmp_path: Path) -> None:
    f = _write(tmp_path, "node_bad.py", "from aiokafka import AIOKafkaProducer\n")
    violations = ValidatorTransportImport().check_file(f)
    assert len(violations) == 1
    assert violations[0].module_name == "aiokafka"


def test_dotted_submodule_is_flagged(tmp_path: Path) -> None:
    f = _write(tmp_path, "node_bad.py", "import redis.asyncio as r\n")
    violations = ValidatorTransportImport().check_file(f)
    assert len(violations) == 1
    assert violations[0].module_name == "redis"


def test_type_checking_guard_is_allowed(tmp_path: Path) -> None:
    body = (
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n\n"
        "if TYPE_CHECKING:\n"
        "    import httpx\n"
    )
    f = _write(tmp_path, "node_tc.py", body)
    assert ValidatorTransportImport().check_file(f) == []


def test_aliased_type_checking_guard_is_allowed(tmp_path: Path) -> None:
    body = (
        "from typing import TYPE_CHECKING as TC\n\n"
        "if TC:\n"
        "    from asyncpg import Connection\n"
    )
    f = _write(tmp_path, "node_tc.py", body)
    assert ValidatorTransportImport().check_file(f) == []


def test_inline_suppression_marker(tmp_path: Path) -> None:
    f = _write(
        tmp_path,
        "node_boundary.py",
        "import httpx  # transport-import-ok: infra boundary file\n",
    )
    assert ValidatorTransportImport().check_file(f) == []


def test_non_python_file_skipped(tmp_path: Path) -> None:
    f = _write(tmp_path, "notes.md", "import httpx\n")
    assert ValidatorTransportImport().check_file(f) == []


def test_syntax_error_is_not_a_violation(tmp_path: Path) -> None:
    f = _write(tmp_path, "node_broken.py", "import (((\n")
    assert ValidatorTransportImport().check_file(f) == []


def test_check_paths_recurses_directory(tmp_path: Path) -> None:
    _write(tmp_path, "node_a.py", "import requests\n")
    sub = tmp_path / "nested"
    sub.mkdir()
    _write(sub, "node_b.py", "import json\n")
    violations = ValidatorTransportImport().check_paths([tmp_path])
    assert len(violations) == 1
    assert violations[0].module_name == "requests"


def test_cli_returns_zero_on_clean(tmp_path: Path) -> None:
    f = _write(tmp_path, "node_clean.py", "import json\n")
    assert main([str(f), "--quiet"]) == 0


def test_cli_returns_one_on_violation(tmp_path: Path) -> None:
    f = _write(tmp_path, "node_bad.py", "import httpx\n")
    assert main([str(f), "--quiet"]) == 1
