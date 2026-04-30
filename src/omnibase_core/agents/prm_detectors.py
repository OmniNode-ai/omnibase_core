# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from omnibase_core.enums.enum_prm_pattern import EnumPrmPattern
from omnibase_core.models.agents.model_prm_match import ModelPrmMatch
from omnibase_core.models.agents.model_trajectory_entry import ModelTrajectoryEntry


def _make_dedup_key(
    pattern: EnumPrmPattern,
    affected_agents: list[str],
    affected_targets: list[str],
    step_range: tuple[int, int],
) -> str:
    return f"{pattern}:{','.join(sorted(set(affected_agents)))}:{','.join(sorted(set(affected_targets)))}:{step_range[0]}-{step_range[1]}"


def detect_repetition_loop(
    entries: list[ModelTrajectoryEntry],
    last_processed_step: int,
) -> list[ModelPrmMatch]:
    """Sliding window of 10. Same (agent, action, target) triple ≥2 times → match."""
    if not entries:
        return []

    window_size = 10
    matches: list[ModelPrmMatch] = []
    seen_keys: set[str] = set()

    for start in range(len(entries)):
        window = entries[start : start + window_size]
        triple_count: dict[tuple[str, str, str], list[int]] = {}
        for entry in window:
            key = (entry.agent, entry.action, entry.target)
            triple_count.setdefault(key, []).append(entry.step)

        for (agent, action, target), steps in triple_count.items():
            if len(steps) >= 2:
                step_range = (steps[0], steps[-1])
                if step_range[1] <= last_processed_step:
                    continue
                dedup_key = _make_dedup_key(
                    EnumPrmPattern.REPETITION_LOOP,
                    [agent],
                    [target],
                    step_range,
                )
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)
                matches.append(
                    ModelPrmMatch(
                        pattern=EnumPrmPattern.REPETITION_LOOP,
                        affected_agents=(agent,),
                        affected_targets=(target,),
                        step_range=step_range,
                        severity_level=1,
                        dedup_key=dedup_key,
                    )
                )

    return matches


def detect_ping_pong(
    entries: list[ModelTrajectoryEntry],
    last_processed_step: int,
) -> list[ModelPrmMatch]:
    """Filter to delegate actions. A→B→A with same target ≥3 times in window 5 → match."""
    if not entries:
        return []

    delegate_entries = [e for e in entries if e.action == "delegate"]
    if not delegate_entries:
        return []

    window_size = 5
    matches: list[ModelPrmMatch] = []
    seen_keys: set[str] = set()

    for start in range(len(delegate_entries)):
        window = delegate_entries[start : start + window_size]
        if len(window) < 3:
            break

        # Group by target, look for A→B→A pattern
        target_agents: dict[str, list[str]] = {}
        target_steps: dict[str, list[int]] = {}
        for entry in window:
            target_agents.setdefault(entry.target, []).append(entry.agent)
            target_steps.setdefault(entry.target, []).append(entry.step)

        for target, agents in target_agents.items():
            if len(agents) < 3:
                continue
            # Check for A→B→A pattern: first and third agent same, second different
            has_aba = any(
                agents[i] == agents[i + 2] and agents[i] != agents[i + 1]
                for i in range(len(agents) - 2)
            )
            if not has_aba:
                continue

            steps = target_steps[target]
            step_range = (steps[0], steps[-1])
            if step_range[1] <= last_processed_step:
                continue

            unique_agents = list(dict.fromkeys(agents))
            dedup_key = _make_dedup_key(
                EnumPrmPattern.PING_PONG,
                unique_agents,
                [target],
                step_range,
            )
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            matches.append(
                ModelPrmMatch(
                    pattern=EnumPrmPattern.PING_PONG,
                    affected_agents=tuple(unique_agents),
                    affected_targets=(target,),
                    step_range=step_range,
                    severity_level=1,
                    dedup_key=dedup_key,
                )
            )

    return matches


def detect_expansion_drift(
    entries: list[ModelTrajectoryEntry],
    last_processed_step: int,
) -> list[ModelPrmMatch]:
    """Adjacent windows N=20. recent_unique / prev_unique > 1.5 → match."""
    if not entries:
        return []

    window_size = 20
    if len(entries) < window_size * 2:
        return []

    matches: list[ModelPrmMatch] = []
    seen_keys: set[str] = set()

    for start in range(len(entries) - window_size * 2 + 1):
        prev_window = entries[start : start + window_size]
        recent_window = entries[start + window_size : start + window_size * 2]

        prev_unique = len({e.target for e in prev_window})
        recent_unique = len({e.target for e in recent_window})

        if prev_unique == 0:
            continue

        ratio = recent_unique / prev_unique
        if ratio <= 1.5:
            continue

        step_range = (prev_window[0].step, recent_window[-1].step)
        if step_range[1] <= last_processed_step:
            continue

        all_agents = list({e.agent for e in prev_window + recent_window})
        all_targets = list({e.target for e in recent_window})
        dedup_key = _make_dedup_key(
            EnumPrmPattern.EXPANSION_DRIFT,
            all_agents,
            all_targets,
            step_range,
        )
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        matches.append(
            ModelPrmMatch(
                pattern=EnumPrmPattern.EXPANSION_DRIFT,
                affected_agents=tuple(sorted(set(all_agents))),
                affected_targets=tuple(sorted(set(all_targets))),
                step_range=step_range,
                severity_level=1,
                dedup_key=dedup_key,
            )
        )

    return matches


def detect_stuck_on_test(
    entries: list[ModelTrajectoryEntry],
    last_processed_step: int,
    threshold: int = 3,
) -> list[ModelPrmMatch]:
    """Group by target file. Count edit→test_fail→edit cycles. Threshold default 3."""
    if not entries:
        return []

    # Group entries by target
    target_entries: dict[str, list[ModelTrajectoryEntry]] = {}
    for entry in entries:
        target_entries.setdefault(entry.target, []).append(entry)

    matches: list[ModelPrmMatch] = []

    for target, target_list in target_entries.items():
        cycle_count = 0
        i = 0
        cycle_steps: list[int] = []

        while i < len(target_list) - 2:
            if (
                target_list[i].action == "edit"
                and target_list[i + 1].action == "test_fail"
                and target_list[i + 2].action == "edit"
            ):
                cycle_count += 1
                cycle_steps.extend(
                    [
                        target_list[i].step,
                        target_list[i + 1].step,
                        target_list[i + 2].step,
                    ]
                )
                i += 2  # advance past this cycle (next edit starts the next potential cycle)
            else:
                i += 1

        if cycle_count < threshold:
            continue

        step_range = (min(cycle_steps), max(cycle_steps))
        if step_range[1] <= last_processed_step:
            continue

        agents = list({e.agent for e in target_list})
        dedup_key = _make_dedup_key(
            EnumPrmPattern.STUCK_ON_TEST,
            agents,
            [target],
            step_range,
        )
        matches.append(
            ModelPrmMatch(
                pattern=EnumPrmPattern.STUCK_ON_TEST,
                affected_agents=tuple(sorted(set(agents))),
                affected_targets=(target,),
                step_range=step_range,
                severity_level=1,
                dedup_key=dedup_key,
            )
        )

    return matches


def detect_context_thrash(
    entries: list[ModelTrajectoryEntry],
    last_processed_step: int,
    threshold: int = 5,
) -> list[ModelPrmMatch]:
    """≥5 consecutive new-target steps without revisits → match."""
    if not entries:
        return []

    matches: list[ModelPrmMatch] = []
    seen_targets: set[str] = set()
    streak_start_idx: int | None = None
    streak_steps: list[int] = []
    streak_targets: list[str] = []
    streak_agents: list[str] = []

    def _emit_match(
        streak_steps: list[int],
        streak_targets: list[str],
        streak_agents: list[str],
    ) -> ModelPrmMatch | None:
        if len(streak_steps) < threshold:
            return None
        step_range = (streak_steps[0], streak_steps[-1])
        if step_range[1] <= last_processed_step:
            return None
        dedup_key = _make_dedup_key(
            EnumPrmPattern.CONTEXT_THRASH,
            streak_agents,
            streak_targets,
            step_range,
        )
        return ModelPrmMatch(
            pattern=EnumPrmPattern.CONTEXT_THRASH,
            affected_agents=tuple(sorted(set(streak_agents))),
            affected_targets=tuple(sorted(set(streak_targets))),
            step_range=step_range,
            severity_level=1,
            dedup_key=dedup_key,
        )

    for entry in entries:
        if entry.target not in seen_targets:
            # New target — extend streak
            seen_targets.add(entry.target)
            if streak_start_idx is None:
                streak_start_idx = entry.step
            streak_steps.append(entry.step)
            streak_targets.append(entry.target)
            streak_agents.append(entry.agent)
        else:
            # Revisit — emit if streak long enough, then reset
            if len(streak_steps) >= threshold:
                match = _emit_match(streak_steps, streak_targets, streak_agents)
                if match is not None:
                    matches.append(match)
            # Reset streak; the revisited target is already seen
            streak_start_idx = None
            streak_steps = []
            streak_targets = []
            streak_agents = []
            # Don't re-add the revisited target to seen_targets since it's already there

    # Check trailing streak
    if len(streak_steps) >= threshold:
        match = _emit_match(streak_steps, streak_targets, streak_agents)
        if match is not None:
            matches.append(match)

    return matches
