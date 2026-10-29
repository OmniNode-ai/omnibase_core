# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for node_node_purity_check_compute."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.node_purity_check.model_node_purity_check_input import (
    ModelNodePurityCheckInput,
)
from omnibase_core.nodes.node_node_purity_check_compute.handler import (
    NodeNodePurityCheckCompute,
)
from omnibase_core.nodes.node_node_purity_check_compute.runtime_node_purity_check import (
    main,
)

pytestmark = pytest.mark.unit


def test_handle_reports_net_client_import_in_node_file() -> None:
    output = NodeNodePurityCheckCompute().handle(
        ModelNodePurityCheckInput(
            files=[
                ModelSourceFile(
                    path="src/pkg/nodes/node_bad.py", source="import asyncpg\n"
                ),
                ModelSourceFile(
                    path="src/pkg/other/not_a_node.py", source="import asyncpg\n"
                ),
            ]
        )
    )
    assert [(v.file, v.line, v.rule) for v in output.violations] == [
        ("src/pkg/nodes/node_bad.py", 1, "net-client")
    ]
    assert not output.is_clean


def test_handle_clean_node_file_is_clean() -> None:
    output = NodeNodePurityCheckCompute().handle(
        ModelNodePurityCheckInput(
            files=[
                ModelSourceFile(
                    path="src/pkg/nodes/node_ok.py",
                    source="def f() -> int:\n    return 1\n",
                )
            ]
        )
    )
    assert output.violations == ()
    assert output.is_clean


def test_main_exit_codes(tmp_path: Path) -> None:
    nodes_dir = tmp_path / "src" / "pkg" / "nodes"
    nodes_dir.mkdir(parents=True)
    clean = nodes_dir / "node_clean.py"
    clean.write_text("def f() -> int:\n    return 1\n", encoding="utf-8")
    bad = nodes_dir / "node_bad.py"
    bad.write_text("import asyncpg\n", encoding="utf-8")
    assert main([str(clean), "--quiet"]) == 0
    assert main([str(bad), "--quiet"]) == 1
