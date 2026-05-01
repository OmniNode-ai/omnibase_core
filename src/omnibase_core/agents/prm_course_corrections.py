# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from omnibase_core.enums.enum_prm_pattern import EnumPrmPattern

_ADVISORY: dict[EnumPrmPattern, str] = {
    EnumPrmPattern.REPETITION_LOOP: (
        "ADVISORY: Repetition loop detected. You are repeating the same action on the same "
        "target. Step back and consider an alternative approach before continuing."
    ),
    EnumPrmPattern.PING_PONG: (
        "ADVISORY: Ping-pong delegation detected. The same task is bouncing between agents "
        "without resolution. Assign ownership explicitly and proceed to closure."
    ),
    EnumPrmPattern.EXPANSION_DRIFT: (
        "ADVISORY: Scope expansion detected. The number of targets is growing rapidly across "
        "steps. Narrow focus to the original task scope before adding new targets."
    ),
    EnumPrmPattern.STUCK_ON_TEST: (
        "ADVISORY: Stuck on failing test. Multiple edit/test-fail cycles on the same file. "
        "Diagnose the root cause before making further edits."
    ),
    EnumPrmPattern.CONTEXT_THRASH: (
        "ADVISORY: Context thrash detected. Too many new targets introduced consecutively. "
        "Revisit earlier targets to consolidate context before expanding further."
    ),
}

_STRONGER: dict[EnumPrmPattern, str] = {
    EnumPrmPattern.REPETITION_LOOP: (
        "WARNING (escalated): Repetition loop persists. This is the second occurrence. "
        "You must change strategy: either skip this target, file a blocker ticket, or "
        "request human review. Do not repeat the same action again."
    ),
    EnumPrmPattern.PING_PONG: (
        "WARNING (escalated): Ping-pong persists. Assign a single responsible agent and "
        "do not re-delegate. If the task is blocked, escalate to the team lead explicitly."
    ),
    EnumPrmPattern.EXPANSION_DRIFT: (
        "WARNING (escalated): Scope expansion continues. Revert to original ticket scope "
        "immediately. Create separate tickets for out-of-scope work discovered."
    ),
    EnumPrmPattern.STUCK_ON_TEST: (
        "WARNING (escalated): Test failure loop persists. Write a diagnosis doc before "
        "making any further edits. Do not attempt a third fix without diagnosis."
    ),
    EnumPrmPattern.CONTEXT_THRASH: (
        "WARNING (escalated): Context thrash persists. Stop introducing new targets. "
        "Complete or abandon existing open targets before touching anything new."
    ),
}

HARD_STOP_SENTINEL = (
    "HARD_STOP: This pattern has triggered three times. Agent execution halted. "
    "Human review required before proceeding. No further automated actions permitted."
)


def advisory_for(pattern: EnumPrmPattern) -> str:
    return _ADVISORY[pattern]


def stronger_for(pattern: EnumPrmPattern) -> str:
    return _STRONGER[pattern]
