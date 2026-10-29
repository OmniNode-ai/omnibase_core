# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure resolution of operator-private vocabularies by contract name (OMN-21494).

The handler performs no I/O. It takes its vocabulary contract from the container,
chooses the path to read in the contract's precedence order (``plan``), and judges
what the source-file gather effect observed there (``handle``). The environment,
the clock and the file facts arrive on the request.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_private_vocabulary_source import (
    EnumPrivateVocabularySource,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.private_vocabulary import (
    ModelPrivateVocabularyCandidate,
    ModelPrivateVocabularyContract,
    ModelPrivateVocabularyEntry,
    ModelPrivateVocabularyRequest,
    ModelPrivateVocabularyResolution,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

__all__ = ["HandlerPrivateVocabulary"]


def _refusal(message: str, error_code: EnumCoreErrorCode) -> ModelOnexError:
    """Keep every refusal on one line, including file and parser diagnostics."""
    return ModelOnexError(message=" ".join(message.splitlines()), error_code=error_code)


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
    """Resolve a vocabulary from explicit request inputs and the container's contract."""

    def __init__(self, container: ModelONEXContainer) -> None:
        self._contract = container.get_service(ModelPrivateVocabularyContract)

    def declared_environment_keys(self) -> frozenset[str]:
        """Environment keys the contract reads; a bootstrap captures only these."""
        root = self._contract.workspace_config_root
        return frozenset(
            {root.env_var, root.home_env_var}
            | {e.env_var for e in self._contract.vocabularies if e.env_var is not None}
        )

    def plan(
        self, request: ModelPrivateVocabularyRequest
    ) -> ModelPrivateVocabularyCandidate | None:
        """Choose the one path to read in the contract's precedence order."""
        return self._candidate(request, self._entry(request.vocabulary_name))

    def handle(
        self, request: ModelPrivateVocabularyRequest
    ) -> ModelPrivateVocabularyResolution:
        """Return content and provenance, refusing invalid or required missing input."""
        entry = self._entry(request.vocabulary_name)
        candidate = self._candidate(request, entry)
        if candidate is None:
            return self._absent(entry)
        fact = request.file_fact
        if fact is None or fact.path != candidate.path:
            raise _refusal(
                f"{candidate.path}: the read effect has not observed this private vocabulary path",
                EnumCoreErrorCode.INVALID_INPUT,
            )
        if fact.error is not None:
            raise _refusal(fact.error, EnumCoreErrorCode.FILE_READ_ERROR)
        if not fact.is_file or fact.text is None:
            if candidate.source is EnumPrivateVocabularySource.WORKSPACE_CONFIG_ROOT:
                return self._absent(entry)
            setting = (
                f" from {entry.env_var}"
                if candidate.source is EnumPrivateVocabularySource.ENVIRONMENT
                else ""
            )
            raise _refusal(
                f"{candidate.path}: private vocabulary{setting} is not a readable file",
                EnumCoreErrorCode.FILE_NOT_FOUND,
            )
        age = (
            _age_days(fact.text, candidate.path, entry.resolved_at_key, request.now)
            if entry.resolved_at_key is not None
            else None
        )
        maximum = entry.max_age_days if age is not None else None
        return ModelPrivateVocabularyResolution(
            vocabulary_name=entry.name,
            found=True,
            path=candidate.path,
            source=candidate.source,
            text=fact.text,
            age_days=age,
            max_age_days=maximum,
            age_exceeded=age is not None and maximum is not None and age > maximum,
        )

    def _entry(self, name: str) -> ModelPrivateVocabularyEntry:
        entry = next((e for e in self._contract.vocabularies if e.name == name), None)
        if entry is None:
            known = ", ".join(e.name for e in self._contract.vocabularies)
            raise _refusal(
                f"unknown private vocabulary {name!r}; known names: {known}",
                EnumCoreErrorCode.INVALID_INPUT,
            )
        return entry

    def _absent(
        self, entry: ModelPrivateVocabularyEntry
    ) -> ModelPrivateVocabularyResolution:
        """A vocabulary no setting supplied: refused when required, else not found."""
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

    def _candidate(
        self, request: ModelPrivateVocabularyRequest, entry: ModelPrivateVocabularyEntry
    ) -> ModelPrivateVocabularyCandidate | None:
        if request.explicit_path is not None:
            return ModelPrivateVocabularyCandidate(
                path=request.explicit_path, source=EnumPrivateVocabularySource.EXPLICIT
            )
        if entry.env_var is not None:
            configured = request.environment.get(entry.env_var, "").strip()
            if configured:
                return ModelPrivateVocabularyCandidate(
                    path=Path(configured),
                    source=EnumPrivateVocabularySource.ENVIRONMENT,
                )
        settings = self._contract.workspace_config_root
        configured_root = request.environment.get(settings.env_var, "").strip()
        home = request.environment.get(settings.home_env_var, "").strip()
        if configured_root:
            root = Path(configured_root)
        elif home:
            root = Path(home) / ".." / settings.home_sibling
        else:
            return None
        return ModelPrivateVocabularyCandidate(
            path=root / entry.relative_path,
            source=EnumPrivateVocabularySource.WORKSPACE_CONFIG_ROOT,
        )
