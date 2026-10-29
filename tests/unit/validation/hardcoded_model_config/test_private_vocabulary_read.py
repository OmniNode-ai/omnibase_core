# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The model-config gate reads its private denylist through the core handler,
resolved from the container together with the gather effect (OMN-21494, plan
task T0.1), not through a loader of its own."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from omnibase_core.handlers.handler_private_vocabulary_resolution import (
    build_container,
    resolve_private_vocabulary,
)
from omnibase_core.models.private_vocabulary import (
    ModelPrivateVocabularyRequest,
    ModelPrivateVocabularyResolution,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler_private_vocabulary import (
    HandlerPrivateVocabulary,
)
from omnibase_core.validation.hardcoded_model_config import (
    runtime_hardcoded_model_config as runtime,
)

pytestmark = pytest.mark.unit

_DENYLIST = "hardcoded_model_config_lab_denylist"
_DEAD = "198.51.100.9:8101"
_ROOT_ENV = "ONEX_WORKSPACE_CONFIG_ROOT"


def test_the_gate_resolves_the_handler_and_the_effect_from_the_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    container = build_container()
    resolved: list[type] = []
    real_get_service = container.get_service

    def spy_get_service(protocol_type: type, service_name: str | None = None) -> object:
        resolved.append(protocol_type)
        return real_get_service(protocol_type, service_name)

    monkeypatch.setattr(container, "get_service", spy_get_service)
    handler = real_get_service(HandlerPrivateVocabulary)
    asked: list[ModelPrivateVocabularyRequest] = []
    original = handler.handle

    def recording(
        request: ModelPrivateVocabularyRequest,
    ) -> ModelPrivateVocabularyResolution:
        asked.append(request)
        return original(request)

    monkeypatch.setattr(handler, "handle", recording)
    resolution = resolve_private_vocabulary(
        container,
        _DENYLIST,
        environment={_ROOT_ENV: str(tmp_path)},
        now=datetime.now(UTC),
    )
    runtime.load_policy(resolution)
    assert HandlerPrivateVocabulary in resolved
    assert NodeSourceFileGatherEffect in resolved
    assert [r.vocabulary_name for r in asked] == [_DENYLIST]


def test_the_gate_keeps_no_loader_of_its_own() -> None:
    assert not hasattr(runtime, "_workspace_config_root")
    assert not hasattr(runtime, "_LAB_DENYLIST_REL")


def test_the_gate_never_builds_the_handler_or_reads_the_environment() -> None:
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    assert "HandlerPrivateVocabulary(" not in source
    assert "request_from_process" not in source
    assert "os.environ" not in source


def test_a_denylist_at_the_config_root_still_extends_the_policy(
    tmp_path: Path,
) -> None:
    target = tmp_path / "vocabularies" / "hardcoded_model_config_lab_denylist.yaml"
    target.parent.mkdir(parents=True)
    target.write_text(
        f'schema_version: 1\nretired_values:\n  - "{_DEAD}"\n', encoding="utf-8"
    )
    resolution = resolve_private_vocabulary(
        build_container(),
        _DENYLIST,
        environment={_ROOT_ENV: str(tmp_path)},
        now=datetime.now(UTC),
    )
    assert _DEAD in runtime.load_policy(resolution).retired_values
