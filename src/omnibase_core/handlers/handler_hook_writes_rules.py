# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure hook parsing and check-only predicates for hook-writes (OMN-21433).

All rule values belong to the overlay. These helpers perform no filesystem I/O.
"""

from __future__ import annotations

import shlex
from typing import Final

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.hook_writes.model_hook_writes_document import (
    ModelHookWritesDocument,
)
from omnibase_core.models.hook_writes.model_hook_writes_hook import ModelHookWritesHook
from omnibase_core.models.hook_writes.model_hook_writes_rewriting_hook import (
    ModelHookWritesRewritingHook,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["VALIDATOR_ID", "is_check_only", "parse_hooks"]

VALIDATOR_ID: Final[str] = "hook-writes"


def _invalid(path: str, detail: str) -> ModelOnexError:
    """Build a validation error that identifies the source hook file."""
    return ModelOnexError(
        message=f"{path}: {detail}",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


def parse_hooks(path: str, source: str) -> tuple[ModelHookWritesHook, ...]:
    """Read config repositories or an exported hook list, retaining hook order.

    Malformed YAML, unsupported document shapes and malformed hooks raise a
    validation error naming ``path``. An empty config produces no hooks.
    """
    try:
        return load_yaml_content_as_model(source, ModelHookWritesDocument).hooks
    except ModelOnexError as exc:
        raise _invalid(path, f"cannot read hooks: {exc.message}") from exc


def is_check_only(
    hook: ModelHookWritesHook, rewriting: ModelHookWritesRewritingHook
) -> bool:
    """True when a check-only argument is a whole argument or entry token."""
    entry = hook.entry if hook.entry is not None else ""
    try:
        tokens = shlex.split(entry)
    except ValueError:
        tokens = entry.split()
    return any(arg in hook.args or arg in tokens for arg in rewriting.check_only_args)
