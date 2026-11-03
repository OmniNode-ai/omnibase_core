# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The hooks of a pre-commit file for the fail-loud meta check (OMN-22357)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.models.precommit_fail_loud.model_fail_loud_hook import (
    ModelFailLoudHook,
)

__all__ = ["ModelFailLoudDocument"]


class ModelFailLoudDocument(BaseModel):
    """Every hook of a ``.pre-commit-config.yaml`` or ``.pre-commit-hooks.yaml``.

    A config file nests its hooks under ``repos[].hooks`` and may name
    ``default_install_hook_types``; an exported hook file is a top-level list of
    hooks. Both are flattened to ``hooks`` in file order. Unknown top-level keys of
    a config are not this check's concern and are dropped.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hooks: tuple[ModelFailLoudHook, ...] = ()
    is_config: bool = False
    installed_stages: tuple[str, ...] | None = None

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data: object) -> object:
        """Accept the config mapping or the exported list; refuse anything else."""
        if isinstance(data, list):
            return {"hooks": data, "is_config": False}
        if not isinstance(data, dict):
            raise ValueError("expected a config mapping or an exported hook list")
        repos = data.get("repos") or []
        if not isinstance(repos, list):
            raise ValueError("repos must be a list")
        hooks: list[object] = []
        for repo in repos:
            if not isinstance(repo, dict) or not isinstance(repo.get("hooks"), list):
                raise ValueError("each repository needs a hooks list")
            hooks.extend(repo["hooks"])
        installed = data.get("default_install_hook_types")
        if installed is not None and not isinstance(installed, list):
            raise ValueError("default_install_hook_types must be a list")
        return {
            "hooks": hooks,
            "is_config": True,
            "installed_stages": None
            if installed is None
            else [str(stage) for stage in installed],
        }
