# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for NodeTextFileWriteEffect (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.text_file_write.model_text_file_write_input import (
    ModelTextFileWriteInput,
)
from omnibase_core.nodes.node_text_file_write_effect.handler import (
    NodeTextFileWriteEffect,
)

pytestmark = pytest.mark.unit


def test_writes_text_and_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "packet.json"
    output = NodeTextFileWriteEffect().handle(
        ModelTextFileWriteInput(path=str(target), text='{"ok": true}\n')
    )
    assert target.read_text(encoding="utf-8") == '{"ok": true}\n'
    assert output.path == str(target)
    assert output.bytes_written == len(b'{"ok": true}\n')


def test_counts_bytes_not_characters(tmp_path: Path) -> None:
    target = tmp_path / "unicode.txt"
    output = NodeTextFileWriteEffect().handle(
        ModelTextFileWriteInput(path=str(target), text="é—")
    )
    assert output.bytes_written == 5
    assert target.read_text(encoding="utf-8") == "é—"


def test_overwrites_an_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    target.write_text("old contents that are longer", encoding="utf-8")
    NodeTextFileWriteEffect().handle(
        ModelTextFileWriteInput(path=str(target), text="new")
    )
    assert target.read_text(encoding="utf-8") == "new"
