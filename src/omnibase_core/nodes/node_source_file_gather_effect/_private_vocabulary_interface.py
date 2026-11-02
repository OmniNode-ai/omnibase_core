# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Planning and judgement port for private-vocabulary resolution."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.models.private_vocabulary import (
    ModelPrivateVocabularyCandidate,
    ModelPrivateVocabularyRequest,
    ModelPrivateVocabularyResolution,
)


@runtime_checkable
class PrivateVocabularyInterface(Protocol):
    """Plan a vocabulary read and judge the resulting file fact."""

    def declared_environment_keys(self) -> frozenset[str]:
        """Return environment keys declared by the vocabulary contract."""
        ...

    def plan(
        self, request: ModelPrivateVocabularyRequest
    ) -> ModelPrivateVocabularyCandidate | None:
        """Choose the candidate path before any file read."""
        ...

    def handle(
        self, request: ModelPrivateVocabularyRequest
    ) -> ModelPrivateVocabularyResolution:
        """Judge the request and its observed file fact."""
        ...
