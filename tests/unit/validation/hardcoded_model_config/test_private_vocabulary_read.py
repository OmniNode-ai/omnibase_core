# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The model-config gate reads its private denylist through the core handler
(OMN-21494, plan task T0.1), not through a loader of its own."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from omnibase_core.handlers.handler_private_vocabulary import (
    HandlerPrivateVocabulary,
)
from omnibase_core.validation.hardcoded_model_config import (
    runtime_hardcoded_model_config as runtime,
)

if TYPE_CHECKING:
    from omnibase_core.models.private_vocabulary import (
        ModelPrivateVocabularyRequest,
        ModelPrivateVocabularyResolution,
    )

pytestmark = pytest.mark.unit

_DENYLIST = "hardcoded_model_config_lab_denylist"
_DEAD = "198.51.100.9:8101"


def test_the_gate_asks_the_handler_for_its_denylist_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[ModelPrivateVocabularyRequest] = []
    original = HandlerPrivateVocabulary.handle

    def spy(
        self: HandlerPrivateVocabulary, request: ModelPrivateVocabularyRequest
    ) -> ModelPrivateVocabularyResolution:
        asked.append(request)
        return original(self, request)

    monkeypatch.setattr(HandlerPrivateVocabulary, "handle", spy)
    monkeypatch.setenv("ONEX_WORKSPACE_CONFIG_ROOT", str(tmp_path))
    runtime.load_policy()
    assert [r.vocabulary_name for r in asked] == [_DENYLIST]


def test_the_gate_keeps_no_loader_of_its_own() -> None:
    assert not hasattr(runtime, "_workspace_config_root")
    assert not hasattr(runtime, "_LAB_DENYLIST_REL")


def test_a_denylist_at_the_config_root_still_extends_the_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "vocabularies" / "hardcoded_model_config_lab_denylist.yaml"
    target.parent.mkdir(parents=True)
    target.write_text(
        f'schema_version: 1\nretired_values:\n  - "{_DEAD}"\n', encoding="utf-8"
    )
    monkeypatch.setenv("ONEX_WORKSPACE_CONFIG_ROOT", str(tmp_path))
    assert _DEAD in runtime.load_policy().retired_values
