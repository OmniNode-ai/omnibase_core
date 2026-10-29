# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure URL normalization and YAML pin extraction (OMN-21495)."""

from __future__ import annotations

from typing import Final

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.precommit_pins.model_precommit_pin import ModelPrecommitPin

__all__ = ["VALIDATOR_ID", "extract_pins", "normalize_repo_url"]

VALIDATOR_ID: Final[str] = "precommit-pin-parity"


def _refusal(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.VALIDATION_ERROR
    )


def normalize_repo_url(repo: str) -> str:
    """Compare repository URLs without a trailing slash or git suffix, casefolded."""
    return repo.removesuffix("/").casefold().removesuffix(".git")


def _field(node: MappingNode, name: str) -> Node | None:
    """Read a mapping field without constructing or coercing YAML scalar values."""
    for key, value in node.value:
        if (
            isinstance(key, ScalarNode)
            and key.value == name
            and isinstance(value, Node)
        ):
            return value
    return None


def extract_pins(source: str) -> tuple[ModelPrecommitPin, ...]:
    """Extract external pins and 1-based rev lines; reject malformed configs.

    Composition preserves numeric-looking revisions verbatim, as well as source
    marks for quoted scalars and flow mappings. Local and meta entries have no rev.
    """
    try:
        document = yaml.compose(source, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        raise _refusal(f"invalid pre-commit YAML: {exc}") from exc
    if not isinstance(document, MappingNode):
        raise _refusal("pre-commit config must be a mapping with a repos list")
    repos = _field(document, "repos")
    if not isinstance(repos, SequenceNode):
        raise _refusal("pre-commit config must be a mapping with a repos list")

    pins: list[ModelPrecommitPin] = []
    for entry in repos.value:
        if not isinstance(entry, MappingNode):
            raise _refusal("each repos entry must be a mapping")
        repo = _field(entry, "repo")
        if not isinstance(repo, ScalarNode) or not repo.value:
            raise _refusal("each repos entry must name a repository")
        if normalize_repo_url(repo.value) in ("local", "meta"):
            continue
        rev = _field(entry, "rev")
        if not isinstance(rev, ScalarNode) or not rev.value:
            raise _refusal(f"repository {repo.value} must have a rev scalar")
        hook_ids: list[str] = []
        hooks = _field(entry, "hooks")
        if isinstance(hooks, SequenceNode):
            for hook in hooks.value:
                if isinstance(hook, MappingNode):
                    hook_id = _field(hook, "id")
                    if isinstance(hook_id, ScalarNode):
                        hook_ids.append(hook_id.value)
        pins.append(
            ModelPrecommitPin(
                repo=repo.value,
                rev=rev.value,
                line=rev.start_mark.line + 1,
                hook_ids=tuple(hook_ids),
            )
        )
    return tuple(pins)
