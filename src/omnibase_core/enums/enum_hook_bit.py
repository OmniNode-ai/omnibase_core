# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""EnumHookBit and hook_enabled() — bitmask gating for omniclaude hooks.

Source of truth for which hook wrappers are active. Each member is a single-bit
power of two. Bit positions are APPEND-ONLY forever — never reorder or reuse.

Runtime mask: env var `ONEX_HOOKS_MASK` (defaults to all-on when unset or malformed).

Fail-open on malformed mask is deliberate: favors hook continuity over honoring
broken user config. A CLI warning on write is a follow-up (OMN-9614).
"""

from __future__ import annotations

import functools
import operator
import os
from enum import IntEnum, unique

__all__ = ["EnumHookBit", "_DEFAULT_MASK", "hook_enabled"]


@unique
class EnumHookBit(IntEnum):
    """Bit positions for omniclaude hook wrappers.

    APPEND-ONLY. Never reorder. Never reuse a removed value.
    Ordinals match the Task 1 (OMN-9610) governance freeze ordering.
    """

    # --- top-level hooks (plugins/onex/hooks/) ---
    CI_REMINDER = 1 << 0
    RUFF_FIX = 1 << 1
    CONVENTION_INJECTOR = 1 << 2

    # --- scripts/ GATE wrappers ---
    EPIC_POSTACTION_GATE = 1 << 3
    EPIC_PREFLIGHT_GATE = 1 << 4
    FILE_PATH_CONVENTION_INJECT = 1 << 5
    HOOK_DISPATCH_CLAIM_POSTTOOL = 1 << 6
    HOOK_DISPATCH_CLAIM_PRETOOL = 1 << 7
    HOOK_IDLE_NOTIFICATION_RATELIMIT = 1 << 8
    HOOK_VERIFIER_ROLE_GUARD = 1 << 9
    PERMISSION_DENIED_LOGGER = 1 << 10
    POST_SKILL_DELEGATION_ENFORCER = 1 << 11
    POST_TOOL_DELEGATION_COUNTER = 1 << 12
    POST_TOOL_USE_QUALITY = 1 << 13
    TEST_REMINDER = 1 << 14
    POST_TOOL_AGENT_RESULT_VERIFIER = 1 << 15
    AUTO_CHECKPOINT = 1 << 16
    AUTO_HOSTILE_REVIEW = 1 << 17
    CHANGESET_GUARD_POST = 1 << 18
    POST_TOOL_COMMIT_VERIFY = 1 << 19
    POST_TOOL_CRON_ACTION_GUARD = 1 << 20
    ENV_SYNC = 1 << 21
    POST_TOOL_KAFKA_POISON_MESSAGE_GUARD = 1 << 22
    POST_TOOL_OUTPUT_SUPPRESSOR = 1 << 23
    POST_TOOL_RETURN_PATH_AUDITOR = 1 << 24
    POST_TOOL_STATE_VERIFY = 1 << 25
    POST_TOOL_SUBAGENT_TOOL_LOG = 1 << 26
    TEAM_OBSERVABILITY = 1 << 27
    POST_TOOL_TSC_CHECK = 1 << 28
    PRE_COMPACT = 1 << 29
    PRE_TOOL_USE_QUALITY = 1 << 30
    PRE_TOOL_AGENT_DISPATCH_GATE = 1 << 31
    PRE_TOOL_AGENT_TOOL_GATE = 1 << 32
    PRE_TOOL_AUTHORIZATION_SHIM = 1 << 33
    BASH_GUARD = 1 << 34
    BRANCH_PROTECTION_GUARD = 1 << 35
    CHANGESET_GUARD_PRE = 1 << 36
    CONTEXT_SCOPE_AUDITOR = 1 << 37
    DISPATCH_GUARD = 1 << 38
    DISPATCH_GUARD_TICKET_EVIDENCE = 1 << 39
    DISPATCH_MODE_GUARDRAIL = 1 << 40
    DOD_COMPLETION_GUARD = 1 << 41
    HOSTILE_REVIEW_GATE = 1 << 42
    LINEAR_DONE_VERIFY = 1 << 43
    MODEL_ROUTER = 1 << 44
    OVERSEER_FOREGROUND_BLOCK = 1 << 45
    PIPELINE_GATE = 1 << 46
    PLAN_EXISTENCE_GATE = 1 << 47
    POLY_ENFORCER = 1 << 48
    PREPUSH_VALIDATOR = 1 << 49
    SCOPE_GATE = 1 << 50
    SWEEP_PREFLIGHT = 1 << 51
    TDD_DISPATCH_GATE = 1 << 52
    TEAM_LEAD_GUARD = 1 << 53
    WORKFLOW_GUARD = 1 << 54
    SESSION_START = 1 << 55
    SESSION_START_ONEX_CLI_PIN_CHECK = 1 << 56


# Default mask ORs all actual member values — correct even after tombstones are
# added (which lower len() but leave high bit positions in active members).
# (1 << len()) - 1 would silently disable the highest bits once any member is
# tombstoned. The generator (Task 3) emits the equivalent literal into hook_bits.sh.
_DEFAULT_MASK: int = functools.reduce(operator.or_, (int(m) for m in EnumHookBit))


def hook_enabled(bit: EnumHookBit, mask: int | None = None) -> bool:
    """Return True if the given bit is set in the effective mask.

    Args:
        bit: The hook bit to test.
        mask: Explicit mask. If None, reads `ONEX_HOOKS_MASK` from env,
              accepts hex (`0x...`), binary (`0b...`), or decimal literal.
              Malformed or missing => default mask (all-on).
    """
    if mask is None:
        raw = os.environ.get("ONEX_HOOKS_MASK")
        if raw is None:
            mask = _DEFAULT_MASK
        else:
            try:
                mask = int(raw, 0)
            except ValueError:
                # Fail-open favors hook continuity over honoring broken user config.
                # A CLI warning on write is a follow-up (OMN-9614).
                mask = _DEFAULT_MASK
    return bool(mask & bit)
