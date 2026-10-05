# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Permissive view of a pre-commit configuration document (the repos list only)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = ["ModelPrecommitRawDocument"]


class ModelPrecommitRawDocument(BaseModel):
    """A pre-commit config as written; only ``repos`` is read, unknown keys are dropped before validation."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repos: object = None

    @model_validator(mode="before")
    @classmethod
    def _keep_known_keys(cls, data: object) -> object:
        """Drop the keys this view does not read; the file carries many more."""
        if not isinstance(data, dict):
            return data
        known = "repos"
        return {key: value for key, value in data.items() if key in known}
