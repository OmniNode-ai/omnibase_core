# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for node_normalization_symmetry_check_compute (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.normalization_symmetry_check.model_normalization_symmetry_check_input import (
    ModelNormalizationSymmetryCheckInput,
)
from omnibase_core.nodes.node_normalization_symmetry_check_compute.handler import (
    NodeNormalizationSymmetryCheckCompute,
)
from omnibase_core.nodes.node_normalization_symmetry_check_compute.runtime_normalization_symmetry_check import (
    main,
)

pytestmark = pytest.mark.unit

PRODUCER = (
    "from omnibase_core.topics import TopicBase\n\n\n"
    "class P:\n    def emit(self) -> None:\n"
    "        self._bus.send(TopicBase.SESSION_STARTED.strip(), {})\n"
)
CONSUMER = (
    "from omnibase_core.topics import TopicBase\n\n\n"
    "class C:\n    def register(self) -> None:\n"
    "        self._bus.subscribe([TopicBase.SESSION_STARTED])\n"
)
CONSUMER_STRIP = CONSUMER.replace(
    "TopicBase.SESSION_STARTED]", "TopicBase.SESSION_STARTED.strip()]"
)


def _input(consumer: str) -> ModelNormalizationSymmetryCheckInput:
    return ModelNormalizationSymmetryCheckInput(
        root="src",
        files=(
            ModelSourceFile(path="src/p.py", source=PRODUCER),
            ModelSourceFile(path="src/c.py", source=consumer),
        ),
    )


def test_handle_pass_and_fail() -> None:
    handler = NodeNormalizationSymmetryCheckCompute()
    assert handler.handle(_input(CONSUMER_STRIP)).messages == ()
    bad = handler.handle(_input(CONSUMER))
    assert len(bad.messages) == 1
    assert "TopicBase.SESSION_STARTED" in bad.messages[0]
    assert "producer applies [strip]" in bad.messages[0]


def test_main_exit_codes(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "p.py").write_text(PRODUCER)
    (src / "c.py").write_text(CONSUMER_STRIP)
    assert main([str(src)]) == 0
    (src / "c.py").write_text(CONSUMER)
    assert main([str(src)]) == 1
