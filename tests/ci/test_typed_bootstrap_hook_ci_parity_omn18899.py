# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The typed-bootstrap gate runs one invocation locally and remotely (OMN-18899).

Before OMN-18899 the two sides ran the same validator module in two different
modes. The ``typed-bootstrap-environment-boundary`` job in ``ci.yml`` passed
``--all --inventory``, which audits the four-root corpus against the OMN-17744
debt register and is green: 321 findings across 102 paths, ``unassigned=0
stale=0``. The pre-commit hook of the same id passed neither flag, landing in
strict mode, which by design fails on every one of those 321 registered
findings. A whole-tree local run was therefore red from the hour the hook was
added, and had never been green on any commit, while the remote gate reported
success on the same tree.

A local check whose verdict cannot agree with the remote one teaches the next
lane to read past it. This module is the mechanism that keeps them equal: it
reads the argument list out of each file and compares them, so a flag added to
one side without the other is a red test rather than a rediscovery six months
later.

What it does NOT assert: that the 102 registered readers are acceptable. They
are owned debt under OMN-17744 with a recorded disposition, and migrating them
is that ticket's work, not this one's.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

HOOK_ID = "typed-bootstrap-environment-boundary"
VALIDATOR_MODULE = "omnibase_core.validators.no_new_os_environ"


def _hook_argv() -> list[str]:
    """Return the pre-commit hook's command line, split like a shell would."""
    config = yaml.safe_load(PRECOMMIT_CONFIG.read_text(encoding="utf-8"))
    hooks = [
        hook
        for repo in config["repos"]
        for hook in repo.get("hooks", [])
        if hook["id"] == HOOK_ID
    ]
    assert len(hooks) == 1, f"{HOOK_ID} is not declared exactly once"
    return shlex.split(hooks[0]["entry"])


def _hook_definition() -> dict[str, object]:
    config = yaml.safe_load(PRECOMMIT_CONFIG.read_text(encoding="utf-8"))
    return next(
        hook
        for repo in config["repos"]
        for hook in repo.get("hooks", [])
        if hook["id"] == HOOK_ID
    )


def _ci_argv() -> list[str]:
    """Return the ci.yml job's validator command line.

    The workflow is read as text rather than as parsed YAML so that a multi-line
    ``run:`` block is matched on the line that actually invokes the module.
    """
    lines = CI_WORKFLOW.read_text(encoding="utf-8").splitlines()
    invocations = [
        shlex.split(line.strip())
        for line in lines
        if re.search(rf"-m\s+{re.escape(VALIDATOR_MODULE)}\b", line)
    ]
    assert len(invocations) == 1, (
        f"expected exactly one {VALIDATOR_MODULE} invocation in ci.yml, "
        f"found {len(invocations)}"
    )
    return invocations[0]


def _flags(argv: list[str]) -> set[str]:
    """Return the option flags from a command line, ignoring how it is launched."""
    index = argv.index("-m")
    assert argv[index + 1] == VALIDATOR_MODULE, "module name follows -m"
    return {token for token in argv[index + 2 :] if token.startswith("-")}


class TestTypedBootstrapInvocationParity:
    def test_both_sides_run_the_same_validator_module(self) -> None:
        assert VALIDATOR_MODULE in _hook_argv()
        assert VALIDATOR_MODULE in _ci_argv()

    def test_flag_sets_are_identical(self) -> None:
        hook_flags = _flags(_hook_argv())
        ci_flags = _flags(_ci_argv())
        assert hook_flags == ci_flags, (
            "the pre-commit hook and the ci.yml job must run the same mode; "
            f"hook={sorted(hook_flags)} ci={sorted(ci_flags)}"
        )

    def test_inventory_mode_is_the_mode_both_sides_run(self) -> None:
        """Pin the mode itself, not only that the two sides agree.

        Two sides agreeing on strict mode would satisfy the comparison above
        while putting the tree back to red on every whole-corpus run.
        """
        assert "--inventory" in _flags(_hook_argv())
        assert "--all" in _flags(_hook_argv())

    def test_hook_does_not_receive_staged_filenames(self) -> None:
        """Inventory mode reads the corpus, so a file subset is not valid input.

        ``--inventory`` fails closed on an inventory entry that the scan did not
        reach. Given a subset it would report every unscanned entry as stale and
        refuse the commit, so the two settings are one decision.
        """
        hook = _hook_definition()
        assert hook.get("pass_filenames") is False
        argv = _hook_argv()
        assert "--all" in argv, "the roots must come from the validator, not pre-commit"

    def test_ci_job_declares_the_hook_id_as_its_job_name(self) -> None:
        """The two sides are found by the same name, so neither can be renamed alone."""
        workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
        assert HOOK_ID in workflow["jobs"], (
            f"ci.yml has no job named {HOOK_ID}; if it was renamed, this test's "
            "lookup and the pre-commit hook id must move together"
        )
