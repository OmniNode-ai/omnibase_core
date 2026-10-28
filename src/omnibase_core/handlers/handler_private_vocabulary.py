# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolve operator-private vocabularies by contract name (OMN-21433).

The handler reads files using the environment and time supplied in its request.
The CLI bootstrap captures those inputs from the process.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_private_vocabulary_source import (
    EnumPrivateVocabularySource,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.private_vocabulary import (
    ModelPrivateVocabularyContract,
    ModelPrivateVocabularyEntry,
    ModelPrivateVocabularyRequest,
    ModelPrivateVocabularyResolution,
)
from omnibase_core.utils.util_safe_yaml_loader import (
    load_yaml_content_as_model,
    load_yaml_mapping_no_duplicates,
)

__all__ = [
    "DEFAULT_CONTRACT",
    "HandlerPrivateVocabulary",
    "load_contract",
    "main",
    "request_from_process",
]

DEFAULT_CONTRACT: Final[Path] = (
    Path(__file__).parent.parent / "contracts" / "private_vocabularies.yaml"
)


def _refusal(message: str, error_code: EnumCoreErrorCode) -> ModelOnexError:
    """Keep every refusal on one line, including file and parser diagnostics."""
    return ModelOnexError(message=" ".join(message.splitlines()), error_code=error_code)


def load_contract(path: Path = DEFAULT_CONTRACT) -> ModelPrivateVocabularyContract:
    """Read the vocabulary resolution contract at ``path``."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise _refusal(
            f"{path}: cannot read private vocabulary contract: {exc}",
            EnumCoreErrorCode.FILE_READ_ERROR,
        ) from exc
    try:
        return load_yaml_content_as_model(text, ModelPrivateVocabularyContract)
    except ModelOnexError as exc:
        raise _refusal(
            f"{path}: private vocabulary contract is invalid: {exc.message}",
            EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        ) from exc


def _age_days(text: str, path: Path, key: str, now: datetime) -> int | None:
    """Read the declared resolution timestamp, when present, as UTC."""
    try:
        document = load_yaml_mapping_no_duplicates(text, source=str(path))
    except (yaml.YAMLError, ValueError) as exc:
        raise _refusal(
            f"{path}: cannot parse private vocabulary timestamp {key!r}: {exc}",
            EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        ) from exc
    if key not in document:
        return None
    value: object = document[key]
    if isinstance(value, datetime):
        resolved = value
    elif isinstance(value, str):
        try:
            resolved = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise _refusal(
                f"{path}: timestamp {key!r} is invalid: {exc}",
                EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            ) from exc
    else:
        raise _refusal(
            f"{path}: timestamp {key!r} is invalid: expected an ISO 8601 string",
            EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
        )
    if resolved.tzinfo is None:
        resolved = resolved.replace(tzinfo=UTC)
    return (now - resolved).days


class HandlerPrivateVocabulary:
    """Resolve and read a vocabulary using only explicit request inputs."""

    def __init__(self, contract: ModelPrivateVocabularyContract | None = None) -> None:
        self._contract = contract if contract is not None else load_contract()

    def handle(
        self, request: ModelPrivateVocabularyRequest
    ) -> ModelPrivateVocabularyResolution:
        """Return content and provenance, refusing invalid or required missing input."""
        entry = next(
            (
                e
                for e in self._contract.vocabularies
                if e.name == request.vocabulary_name
            ),
            None,
        )
        if entry is None:
            known = ", ".join(e.name for e in self._contract.vocabularies)
            raise _refusal(
                f"unknown private vocabulary {request.vocabulary_name!r}; known names: {known}",
                EnumCoreErrorCode.INVALID_INPUT,
            )
        path, source = self._candidate(request, entry)
        if path is not None:
            try:
                is_file = path.is_file()
            except OSError as exc:
                raise _refusal(
                    f"{path}: cannot inspect private vocabulary: {exc}",
                    EnumCoreErrorCode.FILE_READ_ERROR,
                ) from exc
            if not is_file:
                if source is not EnumPrivateVocabularySource.WORKSPACE_CONFIG_ROOT:
                    setting = (
                        f" from {entry.env_var}"
                        if source is EnumPrivateVocabularySource.ENVIRONMENT
                        else ""
                    )
                    raise _refusal(
                        f"{path}: private vocabulary{setting} is not a readable file",
                        EnumCoreErrorCode.FILE_NOT_FOUND,
                    )
                path = None
        if path is None:
            if entry.required:
                root_setting = self._contract.workspace_config_root.env_var
                override = (
                    f"set {entry.env_var} (or pass an explicit path), or "
                    if entry.env_var is not None
                    else ""
                )
                raise _refusal(
                    f"private vocabulary {entry.name!r} is not set: {override}"
                    f"place {entry.relative_path} under {root_setting}",
                    EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
                )
            return ModelPrivateVocabularyResolution(
                vocabulary_name=entry.name,
                found=False,
                path=None,
                source=None,
                text=None,
                age_days=None,
                max_age_days=None,
                age_exceeded=False,
            )
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise _refusal(
                f"{path}: cannot read private vocabulary: {exc}",
                EnumCoreErrorCode.FILE_READ_ERROR,
            ) from exc
        age = (
            _age_days(text, path, entry.resolved_at_key, request.now)
            if entry.resolved_at_key is not None
            else None
        )
        maximum = entry.max_age_days if age is not None else None
        return ModelPrivateVocabularyResolution(
            vocabulary_name=entry.name,
            found=True,
            path=path,
            source=source,
            text=text,
            age_days=age,
            max_age_days=maximum,
            age_exceeded=age is not None and maximum is not None and age > maximum,
        )

    def _candidate(
        self, request: ModelPrivateVocabularyRequest, entry: ModelPrivateVocabularyEntry
    ) -> tuple[Path | None, EnumPrivateVocabularySource | None]:
        """Choose one path in the contract's precedence order."""
        if request.explicit_path is not None:
            return request.explicit_path, EnumPrivateVocabularySource.EXPLICIT
        if entry.env_var is not None:
            configured = request.environment.get(entry.env_var, "").strip()
            if configured:
                return Path(configured), EnumPrivateVocabularySource.ENVIRONMENT
        settings = self._contract.workspace_config_root
        configured_root = request.environment.get(settings.env_var, "").strip()
        home = request.environment.get(settings.home_env_var, "").strip()
        if configured_root:
            root = Path(configured_root)
        elif home:
            root = Path(home) / ".." / settings.home_sibling
        else:
            return None, None
        return (
            root / entry.relative_path,
            EnumPrivateVocabularySource.WORKSPACE_CONFIG_ROOT,
        )


def request_from_process(
    name: str, explicit_path: Path | None = None
) -> ModelPrivateVocabularyRequest:
    """Capture only contract-declared environment keys and the current UTC time."""
    contract = load_contract()
    root = contract.workspace_config_root
    declared_keys = {root.env_var, root.home_env_var}
    declared_keys.update(
        entry.env_var for entry in contract.vocabularies if entry.env_var is not None
    )
    captured = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=declared_keys
    )
    return ModelPrivateVocabularyRequest(
        vocabulary_name=name,
        explicit_path=explicit_path,
        environment=dict(captured.environment.values),
        now=datetime.now(UTC),
    )


def main(argv: list[str] | None = None) -> int:
    """Print the resolved path, or one refusal line on stderr."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Contract vocabulary name.")
    parser.add_argument("--path", type=Path, help="Explicit vocabulary path.")
    args = parser.parse_args(argv)
    try:
        resolution = HandlerPrivateVocabulary().handle(
            request_from_process(args.name, args.path)
        )
    except ModelOnexError as exc:
        sys.stderr.write(f"{exc.message}\n")
        return 1
    if resolution.found:
        sys.stdout.write(f"{resolution.path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
