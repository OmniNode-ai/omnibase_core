# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Container-resolved private-vocabulary resolution.

The only file reads are the source-file gather EFFECT node's. ``build_container`` loads the
packaged vocabulary contract through the node runtime's DI composition root.
``resolve_private_vocabulary`` plans with the handler, reads with the effect and judges with
the handler; the caller captures the environment and the clock at the process boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Final, cast

from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.private_vocabulary import (
    ModelPrivateVocabularyFileFact,
    ModelPrivateVocabularyRequest,
    ModelPrivateVocabularyResolution,
)
from omnibase_core.nodes.node_source_file_gather_effect._private_vocabulary_interface import (
    PrivateVocabularyInterface,
)
from omnibase_core.nodes.node_source_file_gather_effect._source_file_gather_interface import (
    SourceFileGatherInterface,
)

__all__ = [
    "PACKAGED_CONTRACT",
    "build_container",
    "capture_environment",
    "read_file_fact",
    "resolve_private_vocabulary",
]

PACKAGED_CONTRACT: Final[Path] = (
    Path(__file__).parent.parent / "contracts" / "private_vocabularies.yaml"
)

# These protocol classes are registry keys, never constructors.
_READER_TOKEN = cast(
    "type[SourceFileGatherInterface]", cast(object, SourceFileGatherInterface)
)
_HANDLER_TOKEN = cast(
    "type[PrivateVocabularyInterface]", cast(object, PrivateVocabularyInterface)
)


def _failed(path: Path, reason: str) -> ModelPrivateVocabularyFileFact:
    return ModelPrivateVocabularyFileFact(
        path=path,
        is_file=False,
        text=None,
        error=" ".join(f"{path}: {reason}".splitlines()),
    )


def read_file_fact(
    reader: SourceFileGatherInterface, path: Path
) -> ModelPrivateVocabularyFileFact:
    """Ask the gather effect for exactly ``path`` and report what it observed."""
    try:
        gathered = reader.handle(
            ModelSourceFileGatherInput(
                root=str(path.parent),
                explicit_paths=[str(path)],
                include_patterns=["*"],
            )
        )
    except OSError as exc:
        return _failed(path, f"cannot inspect private vocabulary: {exc}")
    if gathered.files:
        return ModelPrivateVocabularyFileFact(
            path=path, is_file=True, text=gathered.files[0].source, error=None
        )
    failure = next(
        (s.reason for s in gathered.skipped if s.reason.startswith("read error")), None
    )
    if failure is not None:
        return _failed(path, f"cannot read private vocabulary: {failure}")
    return ModelPrivateVocabularyFileFact(
        path=path, is_file=False, text=None, error=None
    )


def build_container(
    contract_path: Path = PACKAGED_CONTRACT,
    *,
    reader: SourceFileGatherInterface | None = None,
    handler: PrivateVocabularyInterface | None = None,
) -> ModelONEXContainer:
    """Delegate bootstrap to the source-file gather node's composition root."""
    from omnibase_core.nodes.node_source_file_gather_effect.runtime_private_vocabulary import (
        build_container as build_runtime_container,
    )

    return build_runtime_container(contract_path, reader=reader, handler=handler)


def capture_environment(container: ModelONEXContainer) -> dict[str, str]:
    """Capture the process environment keys the vocabulary contract declares."""
    handler = container.get_service(_HANDLER_TOKEN)
    captured = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=handler.declared_environment_keys()
    )
    return dict(captured.environment.values)


def resolve_private_vocabulary(
    container: ModelONEXContainer,
    name: str,
    *,
    environment: Mapping[str, str],
    now: datetime,
    explicit_path: Path | None = None,
) -> ModelPrivateVocabularyResolution:
    """Plan with the handler, read with the effect, judge with the handler."""
    handler = container.get_service(_HANDLER_TOKEN)
    reader = container.get_service(_READER_TOKEN)
    request = ModelPrivateVocabularyRequest(
        vocabulary_name=name,
        explicit_path=explicit_path,
        environment=dict(environment),
        now=now,
    )
    candidate = handler.plan(request)
    if candidate is None:
        return handler.handle(request)
    fact = read_file_fact(reader, candidate.path)
    return handler.handle(request.model_copy(update={"file_fact": fact}))
