# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The console script ``resolve-private-vocabulary`` (OMN-21494).

It hands its arguments to the composition root and prints the resolved path, or
one refusal line naming the setting.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers.handler_private_vocabulary_resolution import (
    PACKAGED_CONTRACT,
)
from omnibase_core.nodes.node_source_file_gather_effect import (
    runtime_private_vocabulary as runtime,
)

pytestmark = pytest.mark.unit

_HYGIENE = "public_repo_hygiene"
_HYGIENE_ENV = "OMNI_HYGIENE_VOCAB_PATH"
_ROOT_ENV = "ONEX_WORKSPACE_CONFIG_ROOT"


def test_cli_prints_the_resolved_path_with_the_variable_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    contract = yaml.safe_load(PACKAGED_CONTRACT.read_text(encoding="utf-8"))
    relative = next(
        v["relative_path"] for v in contract["vocabularies"] if v["name"] == _HYGIENE
    )
    root = tmp_path / "root"
    placed = root / relative
    placed.parent.mkdir(parents=True)
    placed.write_text("schema_version: 1\n", encoding="utf-8")
    monkeypatch.delenv(_HYGIENE_ENV, raising=False)
    monkeypatch.setenv(_ROOT_ENV, str(root))
    assert runtime.main(["--name", _HYGIENE]) == 0
    assert capsys.readouterr().out.strip() == str(placed)


def test_cli_unset_required_vocabulary_is_one_refusal_line_naming_the_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(_HYGIENE_ENV, raising=False)
    monkeypatch.setenv(_ROOT_ENV, str(tmp_path / "empty-root"))
    assert runtime.main(["--name", _HYGIENE]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert len(lines) == 1
    assert _HYGIENE_ENV in lines[0]
