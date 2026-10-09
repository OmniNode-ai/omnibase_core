# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Claude Code hook models.

Models for Claude Code hook events and payloads.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event import (
        ModelClaudeCodeHookEvent,
    )
    from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload import (
        ModelClaudeCodeHookEventPayload,
    )
    from omnibase_core.models.hooks.claude_code.model_claude_code_session_outcome import (
        ModelClaudeCodeSessionOutcome,
    )
    from omnibase_core.models.hooks.claude_code.model_user_prompt_submit_payload import (
        ModelUserPromptSubmitPayload,
    )
    from omnibase_core.utils.util_parse_hook_payload import (
        get_payload_type,
        parse_hook_payload,
    )

__all__ = [
    "ModelClaudeCodeHookEvent",
    "ModelClaudeCodeHookEventPayload",
    "ModelClaudeCodeSessionOutcome",
    "ModelUserPromptSubmitPayload",
    "get_payload_type",
    "parse_hook_payload",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelClaudeCodeHookEvent": (
        "omnibase_core.models.hooks.claude_code.model_claude_code_hook_event",
        "ModelClaudeCodeHookEvent",
    ),
    "ModelClaudeCodeHookEventPayload": (
        "omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload",
        "ModelClaudeCodeHookEventPayload",
    ),
    "ModelClaudeCodeSessionOutcome": (
        "omnibase_core.models.hooks.claude_code.model_claude_code_session_outcome",
        "ModelClaudeCodeSessionOutcome",
    ),
    "ModelUserPromptSubmitPayload": (
        "omnibase_core.models.hooks.claude_code.model_user_prompt_submit_payload",
        "ModelUserPromptSubmitPayload",
    ),
    "get_payload_type": (
        "omnibase_core.utils.util_parse_hook_payload",
        "get_payload_type",
    ),
    "parse_hook_payload": (
        "omnibase_core.utils.util_parse_hook_payload",
        "parse_hook_payload",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
