# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelValidatorHomeHookFact — one pre-commit hook as the K7 checker reads it (OMN-21503)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelValidatorHomeHookFact:
    """One hook of a pre-commit config with the ``repo`` it sits under."""

    hook_id: str
    repo: str
    language: str
    entry: str
