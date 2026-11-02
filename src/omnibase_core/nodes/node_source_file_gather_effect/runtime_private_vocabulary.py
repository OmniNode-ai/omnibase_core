# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Console caller of the source-file gather node for private vocabularies (OMN-21494).

The console script ``resolve-private-vocabulary`` hands its arguments to the
composition root and prints the resolved path, or one refusal line. The process
environment and the clock are captured once, here, at the process boundary, and
travel on the request.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from dependency_injector import providers

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_private_vocabulary_resolution import (
    PACKAGED_CONTRACT,
    capture_environment,
    read_file_fact,
    resolve_private_vocabulary,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.private_vocabulary import ModelPrivateVocabularyContract
from omnibase_core.nodes.node_source_file_gather_effect._private_vocabulary_interface import (
    PrivateVocabularyInterface,
)
from omnibase_core.nodes.node_source_file_gather_effect._source_file_gather_interface import (
    SourceFileGatherInterface,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler_private_vocabulary import (
    HandlerPrivateVocabulary,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["build_container", "main"]

# These protocol classes are registry keys, never constructors.
_READER_TOKEN = cast(
    "type[SourceFileGatherInterface]", cast(object, SourceFileGatherInterface)
)
_HANDLER_TOKEN = cast(
    "type[PrivateVocabularyInterface]", cast(object, PrivateVocabularyInterface)
)


def _load_contract(
    reader: SourceFileGatherInterface, path: Path
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


def build_container(
    contract_path: Path = PACKAGED_CONTRACT,
    *,
    reader: SourceFileGatherInterface | None = None,
    handler: PrivateVocabularyInterface | None = None,
) -> ModelONEXContainer:
    """Bind the node's declared ports using DI providers and explicit overrides."""
    container = ModelONEXContainer()
    registry = container.service_registry
    reader_provider = providers.Singleton(NodeSourceFileGatherEffect)
    if reader is not None:
        reader_provider.override(providers.Object(reader))
    run_coro_sync(registry.register_instance(_READER_TOKEN, reader_provider()))
    contract = _load_contract(container.get_service(_READER_TOKEN), contract_path)
    run_coro_sync(registry.register_instance(ModelPrivateVocabularyContract, contract))
    handler_provider = providers.Singleton(HandlerPrivateVocabulary, container)
    if handler is not None:
        handler_provider.override(providers.Object(handler))
    run_coro_sync(registry.register_instance(_HANDLER_TOKEN, handler_provider()))
    return container


def main(argv: list[str] | None = None) -> int:
    """Print the resolved path, or one refusal line on stderr."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Contract vocabulary name.")
    parser.add_argument("--path", type=Path, help="Explicit vocabulary path.")
    args = parser.parse_args(argv)
    try:
        container = build_container()
        resolution = resolve_private_vocabulary(
            container,
            args.name,
            environment=capture_environment(container),
            now=datetime.now(UTC),
            explicit_path=args.path,
        )
    except ModelOnexError as exc:
        sys.stderr.write(f"{exc.message}\n")
        return 1
    if resolution.found:
        sys.stdout.write(f"{resolution.path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
