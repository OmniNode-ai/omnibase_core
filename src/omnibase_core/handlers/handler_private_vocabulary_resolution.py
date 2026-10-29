# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Composition root for private-vocabulary resolution (OMN-21494).

The only file reads are the source-file gather EFFECT node's. ``build_container``
loads the packaged vocabulary contract through it, builds the pure handler with
that contract and registers both in a container. ``resolve_private_vocabulary``
resolves them from the container, asks the handler which path to read, has the
effect read it and lets the handler judge the result. The environment and the clock arrive as arguments; the process
boundary that captures them is the caller's.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Final

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_private_vocabulary import HandlerPrivateVocabulary
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.private_vocabulary import (
    ModelPrivateVocabularyContract,
    ModelPrivateVocabularyFileFact,
    ModelPrivateVocabularyRequest,
    ModelPrivateVocabularyResolution,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

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


def _failed(path: Path, reason: str) -> ModelPrivateVocabularyFileFact:
    return ModelPrivateVocabularyFileFact(
        path=path,
        is_file=False,
        text=None,
        error=" ".join(f"{path}: {reason}".splitlines()),
    )


def read_file_fact(
    reader: NodeSourceFileGatherEffect, path: Path
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


def _load_contract(
    reader: NodeSourceFileGatherEffect, path: Path
) -> ModelPrivateVocabularyContract:
    fact = read_file_fact(reader, path)
    if fact.error is not None or fact.text is None:
        raise ModelOnexError(
            message=fact.error
            or f"{path}: cannot read private vocabulary contract: not a file",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
        )
    try:
        return load_yaml_content_as_model(fact.text, ModelPrivateVocabularyContract)
    except ModelOnexError as exc:
        raise ModelOnexError(
            message=" ".join(
                f"{path}: private vocabulary contract is invalid: {exc.message}".splitlines()
            ),
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        ) from exc


def build_container(contract_path: Path = PACKAGED_CONTRACT) -> ModelONEXContainer:
    """Register the gather effect, the contract and the handler that takes it."""
    reader = NodeSourceFileGatherEffect()
    contract = _load_contract(reader, contract_path)
    container = ModelONEXContainer()
    registry = container.service_registry
    run_coro_sync(registry.register_instance(NodeSourceFileGatherEffect, reader))
    run_coro_sync(registry.register_instance(ModelPrivateVocabularyContract, contract))
    handler = HandlerPrivateVocabulary(container)
    run_coro_sync(registry.register_instance(HandlerPrivateVocabulary, handler))
    return container


def capture_environment(container: ModelONEXContainer) -> dict[str, str]:
    """Capture the process environment keys the vocabulary contract declares."""
    handler = container.get_service(HandlerPrivateVocabulary)
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
    handler = container.get_service(HandlerPrivateVocabulary)
    reader = container.get_service(NodeSourceFileGatherEffect)
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
