# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The hooks of a pre-commit file, in either of its two shapes (OMN-21498)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.models.hook_writes.model_hook_writes_hook import ModelHookWritesHook

__all__ = ["ModelHookWritesDocument"]


class ModelHookWritesDocument(BaseModel):
    """Every hook of a ``.pre-commit-config.yaml`` or ``.pre-commit-hooks.yaml``.

    A config file nests its hooks under ``repos[].hooks``; an exported hook file
    is a top-level list of hooks. Both are flattened to ``hooks`` in file order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hooks: tuple[ModelHookWritesHook, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data: object) -> object:
        """Accept the config mapping or the exported list; refuse anything else."""
        if isinstance(data, list):
            return {"hooks": data}
        if not isinstance(data, dict):
            raise ValueError("expected a config mapping or an exported hook list")
        repos = data.get("repos", [])
        if not isinstance(repos, list):
            raise ValueError("repos must be a list")
        hooks: list[object] = []
        for repo in repos:
            if not isinstance(repo, dict) or not isinstance(repo.get("hooks"), list):
                raise ValueError("each repository needs a hooks list")
            hooks.extend(repo["hooks"])
        return {"hooks": hooks}
