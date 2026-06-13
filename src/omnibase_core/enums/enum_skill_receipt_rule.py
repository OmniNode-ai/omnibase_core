# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumSkillReceiptRule — the checks performed by the skill-dispatch
receipt-mode validator (OMN-13098)."""

from __future__ import annotations

from enum import StrEnum


class EnumSkillReceiptRule(StrEnum):
    """The four checks performed by ``validate_skill_dispatch_receipt_mode``.

    MISSING_SKILL_KIND
        (a) Skill frontmatter omits ``skill_kind: dispatch | methodology``.
        Classification is explicit, never heuristic.
    INVALID_SKILL_KIND
        Frontmatter declares ``skill_kind`` with a value other than
        ``dispatch`` / ``methodology``.
    BARE_DISPATCH_INVOCATION
        (b) A ``dispatch`` skill's markdown contains a bare
        ``onex (run|node|run-node)`` invocation instead of the single
        ``onex skill`` / ``onex delegate`` receipt-mode command.
    EXECUTABLE_LOGIC_IN_SKILL_DIR
        (c) A ``dispatch`` skill directory contains executable logic
        (``*.py``, ``_lib/``, shell scripts). Dispatch skills are markdown only.
    PROMPT_PRINTS_RAW_JSON
        (d) A ``dispatch`` skill instructs Claude to surface the JSON verbatim
        / ``cat workflow_result.json``, which conflicts with receipt mode.
    """

    MISSING_SKILL_KIND = "missing_skill_kind"
    INVALID_SKILL_KIND = "invalid_skill_kind"
    BARE_DISPATCH_INVOCATION = "bare_dispatch_invocation"
    EXECUTABLE_LOGIC_IN_SKILL_DIR = "executable_logic_in_skill_dir"
    PROMPT_PRINTS_RAW_JSON = "prompt_prints_raw_json"
