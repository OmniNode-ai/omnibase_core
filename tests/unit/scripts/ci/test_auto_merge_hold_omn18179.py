# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the auto-merge arming hold decision (OMN-18179).

These pin the exact shapes measured on the three PRs that were armed over a
human decision inside 24 hours (omninode_infra#1310 and #1313, and
omnibase_core#1678), plus the two GitHub API details the detector depends
on:

* the enable event emitted by an explicit-method arm is
  ``AutoSquashEnabledEvent``, not ``AutoMergeEnabledEvent``;
* every "we don't know" input resolves to hold rather than to arm.

The last test asserts the workflow's GraphQL ``itemTypes`` filter and the
module's event tuples have not drifted apart, which is the one way this
gate could silently stop seeing the events it exists to read.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT = _REPO_ROOT / "scripts" / "ci" / "check_auto_merge_hold.py"
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "auto-merge.yml"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_auto_merge_hold", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def _event(typename: str, created_at: str) -> dict[str, object]:
    return {"__typename": typename, "createdAt": created_at}


# The verbatim timeline read back from omninode_infra#1310 on 2026-09-11.
_PR_1310_TIMELINE = [
    _event("AutoSquashEnabledEvent", "2026-09-10T17:15:29Z"),
    _event("AutoMergeDisabledEvent", "2026-09-10T18:50:55Z"),
]

# The verbatim timeline read back from omnibase_core#1678 on 2026-09-11:
# armed on open, never disabled.
_PR_1678_TIMELINE = [_event("AutoSquashEnabledEvent", "2026-09-11T10:40:33Z")]


class TestLatestAutoMergeDecision:
    def test_no_events_is_no_decision(self) -> None:
        assert mod.latest_auto_merge_decision([]) is None

    @pytest.mark.parametrize("typename", list(mod.ENABLE_EVENT_TYPES))
    def test_every_enable_variant_is_recognised(self, typename: str) -> None:
        """An explicit-method arm emits AutoSquashEnabledEvent, not AutoMerge*.

        A detector matching only ``AutoMergeEnabledEvent`` reads an empty
        enable history for every squash-armed PR in this org.
        """
        timeline = [_event(typename, "2026-09-10T17:15:29Z")]
        assert mod.latest_auto_merge_decision(timeline) == "enable"

    def test_disable_after_enable_is_disable(self) -> None:
        assert mod.latest_auto_merge_decision(_PR_1310_TIMELINE) == "disable"

    def test_enable_after_disable_is_enable(self) -> None:
        """Re-arming by hand resumes automation with no special case."""
        timeline = [
            *_PR_1310_TIMELINE,
            _event("AutoSquashEnabledEvent", "2026-09-10T19:00:00Z"),
        ]
        assert mod.latest_auto_merge_decision(timeline) == "enable"

    def test_order_comes_from_created_at_not_list_position(self) -> None:
        timeline = [
            _event("AutoMergeDisabledEvent", "2026-09-10T18:50:55Z"),
            _event("AutoSquashEnabledEvent", "2026-09-10T17:15:29Z"),
        ]
        assert mod.latest_auto_merge_decision(timeline) == "disable"

    def test_undetermined_timeline_raises(self) -> None:
        with pytest.raises(ValueError, match="undetermined"):
            mod.latest_auto_merge_decision(None)

    def test_unknown_event_type_raises(self) -> None:
        timeline = [_event("AutoTeleportEnabledEvent", "2026-09-10T17:15:29Z")]
        with pytest.raises(ValueError, match="unknown auto-merge timeline event"):
            mod.latest_auto_merge_decision(timeline)

    @pytest.mark.parametrize("created_at", [None, "", "   "])
    def test_unorderable_event_raises(self, created_at: object) -> None:
        timeline = [{"__typename": "AutoSquashEnabledEvent", "createdAt": created_at}]
        with pytest.raises(ValueError, match="no usable createdAt"):
            mod.latest_auto_merge_decision(timeline)


class TestShouldHold:
    def test_pr_1310_shape_holds(self) -> None:
        """The prod scale-down PR: disabled by a human, must not re-arm."""
        assert mod.should_hold(_PR_1310_TIMELINE, []) is True

    def test_pr_1678_shape_arms_without_a_label(self) -> None:
        """Armed on open and never disabled: nothing here says to hold.

        This is the honest limit of the timeline rule, and the reason the
        pre-emptive label exists.
        """
        assert mod.should_hold(_PR_1678_TIMELINE, []) is False

    def test_pr_1678_shape_holds_with_the_label(self) -> None:
        assert mod.should_hold(_PR_1678_TIMELINE, list(mod.HOLD_LABELS)) is True

    def test_never_armed_pr_arms(self) -> None:
        assert mod.should_hold([], []) is False

    def test_label_holds_even_with_a_clean_timeline(self) -> None:
        assert mod.should_hold([], ["hold:auto-merge"]) is True

    def test_label_match_is_case_insensitive_and_trimmed(self) -> None:
        assert mod.should_hold([], ["  Hold:Auto-Merge "]) is True

    def test_unrelated_labels_do_not_hold(self) -> None:
        assert mod.should_hold([], ["infra", "needs-review"]) is False

    @pytest.mark.parametrize(
        ("timeline", "labels"),
        [
            (None, []),
            ([], None),
            (None, None),
        ],
    )
    def test_undetermined_inputs_fail_closed(
        self, timeline: object, labels: object
    ) -> None:
        assert mod.should_hold(timeline, labels) is True

    def test_unknown_event_type_fails_closed(self) -> None:
        timeline = [_event("AutoTeleportEnabledEvent", "2026-09-10T17:15:29Z")]
        assert mod.should_hold(timeline, []) is True

    def test_a_disable_is_honoured_whatever_its_reason(self) -> None:
        timeline = [
            _event("AutoSquashEnabledEvent", "2026-09-10T17:15:29Z"),
            {
                "__typename": "AutoMergeDisabledEvent",
                "createdAt": "2026-09-10T18:50:55Z",
                "reason": "Base branch was changed",
            },
        ]
        assert mod.should_hold(timeline, []) is True


class TestCli:
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(_SCRIPT), "hold", *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_arm_verdict(self) -> None:
        result = self._run(
            "--timeline-json",
            json.dumps(_PR_1678_TIMELINE),
            "--labels-json",
            "[]",
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "arm"

    def test_hold_verdict(self) -> None:
        result = self._run(
            "--timeline-json",
            json.dumps(_PR_1310_TIMELINE),
            "--labels-json",
            "[]",
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "hold"

    def test_a_hold_verdict_exits_zero(self) -> None:
        """The verdict rides on stdout, never on the exit status.

        Under the workflow's `set -euo pipefail` a non-zero exit would red
        the whole job rather than skip one step.
        """
        result = self._run("--timeline-json", "null", "--labels-json", "[]")
        assert result.returncode == 0
        assert result.stdout.strip() == "hold"

    def test_malformed_json_holds_without_crashing(self) -> None:
        result = self._run("--timeline-json", "{not json", "--labels-json", "[]")
        assert result.returncode == 0
        assert result.stdout.strip() == "hold"

    def test_omitted_flags_hold(self) -> None:
        result = self._run()
        assert result.returncode == 0
        assert result.stdout.strip() == "hold"

    def test_non_array_json_holds(self) -> None:
        result = self._run("--timeline-json", '{"a":1}', "--labels-json", "[]")
        assert result.returncode == 0
        assert result.stdout.strip() == "hold"


class TestWorkflowWiring:
    """The gate is only as good as its wiring into auto-merge.yml."""

    def test_workflow_queries_exactly_the_event_types_the_module_knows(self) -> None:
        """A type in the query but not the module fails closed, and a type in
        the module but not the query is simply never delivered -- silently,
        which is the failure this gate exists to prevent."""
        workflow = _WORKFLOW.read_text(encoding="utf-8")
        for typename in (*mod.ENABLE_EVENT_TYPES, *mod.DISABLE_EVENT_TYPES):
            # GraphQL itemTypes takes the SCREAMING_SNAKE enum spelling.
            enum_name = "".join(
                f"_{ch}" if ch.isupper() and i else ch.upper()
                for i, ch in enumerate(typename)
            ).upper()
            assert enum_name in workflow, (
                f"{typename} ({enum_name}) is missing from the auto-merge.yml "
                "GraphQL itemTypes filter"
            )

    def test_the_graphql_query_never_reads_total_count(self) -> None:
        """`timelineItems.totalCount` ignores the itemTypes filter.

        Measured 2026-09-11: the query that returned 2 filtered nodes for
        omninode_infra#1310 reported totalCount 7, and 2 nodes / totalCount
        13 for #1313 -- the unfiltered timeline length both times.

        Scoped to the query lines, not the whole file: the surrounding
        comments have to be able to name the field in order to explain why
        it must not be read.
        """
        query_lines = [
            line
            for line in _WORKFLOW.read_text(encoding="utf-8").splitlines()
            if "timelineItems(" in line
        ]
        assert query_lines, "no GraphQL timelineItems query found in auto-merge.yml"
        for line in query_lines:
            assert "totalCount" not in line, line

    def test_every_arming_step_is_gated_on_the_hold_check(self) -> None:
        """Every step that arms or enqueues must carry the condition.

        Gating only the arm step would still hand a held PR to a merge
        queue, so this walks the parsed job rather than counting strings.
        """
        import yaml

        workflow_text = _WORKFLOW.read_text(encoding="utf-8")
        assert "check_auto_merge_hold.py" in workflow_text

        # `on:` parses as the boolean True in YAML 1.1; irrelevant here, we
        # only read `jobs`.
        parsed = yaml.safe_load(workflow_text)
        arming_steps = [
            step
            for job in parsed["jobs"].values()
            for step in job.get("steps", [])
            if str(step.get("name", "")).startswith(
                ("Enable auto-merge", "Enqueue armed PR")
            )
        ]
        assert arming_steps, "no arming step found in auto-merge.yml"
        for step in arming_steps:
            condition = str(step.get("if", ""))
            assert "steps.hold_gate.outputs.hold != 'true'" in condition, (
                f"step {step.get('name')!r} arms auto-merge without the "
                f"OMN-18179 hold gate; its condition is {condition!r}"
            )
