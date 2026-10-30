# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for the transport-import check node (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.transport_import_check.model_transport_import_check_input import (
    ModelTransportImportCheckInput,
)
from omnibase_core.nodes.node_transport_import_check_compute.handler import (
    NodeTransportImportCheckCompute,
)
from omnibase_core.nodes.node_transport_import_check_compute.runtime_transport_import_check import (
    main,
)

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def test_handle_passes_clean_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "clean.py", "import os\n")
    result = NodeTransportImportCheckCompute().handle(
        ModelTransportImportCheckInput(paths=(str(path),))
    )
    assert result.findings == ()


def test_handle_flags_banned_import(tmp_path: Path) -> None:
    path = _write(tmp_path, "bad.py", "import httpx\n")
    result = NodeTransportImportCheckCompute().handle(
        ModelTransportImportCheckInput(paths=(str(path),))
    )
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert (finding.file, finding.line, finding.module_name) == (str(path), 1, "httpx")
    assert finding.context == "import httpx"
    assert finding.message == f"{path}:1: banned transport import: httpx"


def test_main_exit_zero_on_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, "clean.py", "import os\n")
    assert main([str(path)]) == 0
    assert capsys.readouterr().out == "No transport-import violations found.\n"


def test_main_exit_one_on_violation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, "bad.py", "import httpx\n")
    assert main([str(path)]) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"{path}:1: banned transport import: httpx\n  import httpx\n")
    assert "1 transport-import violation(s)." in out
