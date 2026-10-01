# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Repository identity helpers shared by durable partition keys."""

from __future__ import annotations

import re

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

_REPOSITORY_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*",
    re.ASCII,
)


def canonical_repository_partition_key(repository: str) -> str:
    """Return the ASCII-lowercase partition key for a canonical ``owner/repo``.

    The repository string remains the display and signed identity. Callers use
    this derived value only when forming case-insensitive storage partitions.
    Its accepted shape matches the PostgreSQL check on durable goal-attempt
    tables; rejecting non-ASCII input keeps Python ``lower`` aligned with SQL
    ``lower(repository)`` for every accepted value.
    """
    if not isinstance(repository, str) or not _REPOSITORY_PATTERN.fullmatch(repository):
        raise ModelOnexError(
            "repository must be canonical ASCII owner/repository",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return repository.lower()
