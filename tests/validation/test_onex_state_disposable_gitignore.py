# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The `.onex_state/` disposable-vs-durable separation rule (OMN-15989).

WHAT THIS LOCKS
---------------
`.onex_state/` inside a repo checkout is a mixed bag: it holds regenerable
per-run output (caches, locks, push logs, lane scratch) *and* a small amount of
committed evidence. Before OMN-15989 the split was adjudicated per file, by
hand, every time a landed worktree came up for teardown — an untracked
generated artifact left the worktree dirty, and a dirty worktree escalates into
an owner-approval gate before it can be removed.

The rule that replaces that judgement call, in one sentence:

    Inside a repo checkout, ``.onex_state/`` is DISPOSABLE by default; the only
    durable content is what lives under the explicitly named subtrees
    ``.onex_state/evidence/`` and ``.onex_state/friction/``.

Durable state that must outlive the worktree does not belong in the worktree at
all -- it lives outside every checkout under ``$OMNI_HOME/.onex_state/``
(lane scratch, ledger locks, claim/run state; see
``omnibase_infra/scripts/lane_scratch.py``, which resolves its root to
``$OMNI_HOME/.onex_state/lane_scratch`` precisely so a worktree teardown cannot
take it with them).

WHY THE ASSERTIONS USE ``--no-index``
-------------------------------------
``git check-ignore`` consults the index by default and refuses to report a
*tracked* path as ignored, which would make the durable-side assertions pass
for the wrong reason (they are tracked, therefore reported un-ignored,
regardless of the patterns). ``--no-index`` evaluates the ignore rules alone,
so these tests answer the question actually being asked: what happens to a
*new*, not-yet-tracked file at each of these paths.

NEGATIVE CONTROL
----------------
``test_real_source_paths_are_never_ignored`` exists so this rule can never
widen into a mask over real work. If a future edit to the ignore block starts
swallowing ``src/`` or ``tests/`` paths, that test fails before the change can
land.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = REPO_ROOT / ".gitignore"

# The written-down rule must stay attached to the patterns that implement it.
# A bare pattern block with the rationale stripped out is how the separation
# decays back into per-file judgement.
RULE_MARKER = "OMN-15989"

# ---------------------------------------------------------------------------
# The line, named on both sides (AC1 / AC2).
# ---------------------------------------------------------------------------
# DISPOSABLE: regenerable from a command, or a per-run log/lock/scratch file.
# Every entry below was observed untracked in a real omnibase_core worktree
# during the OMN-15989 survey, except where noted.
DISPOSABLE_PATHS = (
    # Derived build cache + its single-flight lock (OMN-15431).
    ".onex_state/consumer-graph.json",
    ".onex_state/consumer-graph.lock",
    ".onex_state/consumer-graph.json.1234.tmp",
    # Push-path logs and exit codes.
    ".onex_state/push_log.txt",
    ".onex_state/push_exit_code.txt",
    # Lane scratch that leaked into the worktree root instead of
    # $OMNI_HOME/.onex_state/lane_scratch.
    ".onex_state/omn16507-prepush-waiter.sh",
    ".onex_state/omn16507-prepush-waiter.out",
    ".onex_state/MOVED_TO_201.md",
    ".onex_state/OMN-16677-push-handoff.md",
    # Nested per-run output (not observed in core, observed in sibling repos).
    ".onex_state/local_runtime/some_node/run-id/state.yaml",
    ".onex_state/tmp/probe-0000.json",
    ".onex_state/lane_scratch/label-123-abcd.log",
)

# DURABLE: committed evidence. A NEW file at either of these prefixes must stay
# visible to `git status` so it can be reviewed and committed, not silently
# swallowed.
DURABLE_PATHS = (
    ".onex_state/evidence/OMN-15989/separation-rule-evidence.md",
    ".onex_state/evidence/deterministic-ir/deterministic-ir-evidence.txt",
    ".onex_state/friction/a-newly-observed-friction.md",
)

# NEGATIVE CONTROL: ordinary work that must never be masked.
SOURCE_PATHS = (
    "src/omnibase_core/analysis/consumer_graph.py",
    "tests/validation/test_onex_state_disposable_gitignore.py",
    "docs/architecture/ONEX_CANONICAL_ARCHITECTURE.md",
    ".gitignore",
)


def _is_ignored(rel_path: str) -> bool:
    """True when the repo's ignore rules alone would exclude ``rel_path``.

    The env is scrubbed (OMN-14891): git exports GIT_DIR / GIT_WORK_TREE into
    every hook environment and those override ``cwd=``, so an unscrubbed call
    from a pre-push hook would silently evaluate a different repository.
    """
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "--", rel_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=scrub_git_location_env(os.environ),
    )
    # 0 = ignored, 1 = not ignored, anything else = git itself failed.
    assert result.returncode in (0, 1), (
        f"git check-ignore failed for {rel_path!r} "
        f"(rc={result.returncode}): {result.stderr.strip()}"
    )
    return result.returncode == 0


@pytest.mark.unit
def test_separation_rule_is_written_down_next_to_the_patterns() -> None:
    text = GITIGNORE.read_text(encoding="utf-8")
    assert RULE_MARKER in text, (
        ".gitignore must carry the OMN-15989 separation rule as prose next to "
        "the .onex_state patterns — the patterns alone do not say which side "
        "of the line a new path falls on."
    )


@pytest.mark.unit
@pytest.mark.parametrize("rel_path", DISPOSABLE_PATHS)
def test_generated_onex_state_artifacts_are_ignored(rel_path: str) -> None:
    assert _is_ignored(rel_path), (
        f"{rel_path} is regenerable output but is NOT ignored — it will leave a "
        "landed worktree dirty and block teardown behind an owner-approval gate."
    )


@pytest.mark.unit
@pytest.mark.parametrize("rel_path", DURABLE_PATHS)
def test_durable_onex_state_subtrees_stay_visible(rel_path: str) -> None:
    assert not _is_ignored(rel_path), (
        f"{rel_path} holds durable evidence and must stay visible to "
        "`git status`; ignoring it would silently hide committable work."
    )


@pytest.mark.unit
@pytest.mark.parametrize("rel_path", SOURCE_PATHS)
def test_real_source_paths_are_never_ignored(rel_path: str) -> None:
    assert not _is_ignored(rel_path), (
        f"NEGATIVE CONTROL FAILED: {rel_path} is ordinary tracked work and must "
        "never be swallowed by the .onex_state ignore rule."
    )
