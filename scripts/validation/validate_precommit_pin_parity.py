#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CI/pre-commit check: pin-parity ratchet between .pre-commit-config.yaml and the
CI workflow(s) that independently pin the SAME omnibase_core validator
(OMN-14671, WS7 fan-out #7 of OMN-14655; DRIFT-3 recurrence guard).

The problem this guards (elsewhere in the fleet): a pre-commit `repo:` hook pins
an omnibase_core `rev:` that clones a validator at one SHA, while a dedicated CI
ratchet workflow (`uv run --with "omnibase-core @ git+...@<sha>"`) pins the SAME
validator at a DIFFERENT SHA. Both surfaces then enforce a DIFFERENT frozen
baseline, so a change that is green locally can be red in CI (or vice-versa)
purely because the two pins drifted -- staleness by construction. This gate
fails closed the moment a pinned pair diverges, on either side.

omnibase_core is the LAYERING ROOT of the fleet. Unlike the downstream repos it
does not consume omnibase_core as a pinned git dependency: every validator it
gates on is defined IN-REPO and invoked as `repo: local` +
`uv run python -m omnibase_core.validators...`, and no workflow pins an
`omnibase-core @ git+...@<sha>` dependency (verified across all
`.github/workflows/*.yml` on 2026-07-16). So there is NO cross-repo pin pair to
compare here and DRIFT-3 is structurally impossible in omnibase_core --
`PIN_PAIRS` is therefore intentionally EMPTY.

That does NOT make this gate a vacuous green. Two protections keep it live:

  1. The `--self-test` mode (run in CI alongside the real check) drives the
     comparison logic over synthetic matched / mismatched / missing fixtures and
     asserts the expected verdicts, so the mechanism is proven working on every
     run even while PIN_PAIRS is empty. A silently-broken comparator (e.g. a
     regex that stops matching, or a fail-open on a missing pin) is caught here.
  2. The moment a future change adds an `omnibase-core @ git+...@<sha>` CI pin
     with a mirroring `repo:` hook, add its row to PIN_PAIRS in the SAME change
     -- and this gate then enforces the pair stays converged.

PIN_PAIRS rows are (pre-commit hook id, pre-commit repo URL, CI workflow file
(repo-relative), validator module the pair references [for humans/audit only]).
Add a row only after confirming by hand that both sides really reference the same
validator, not two independently-pinned tools that share an upstream repo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".pre-commit-config.yaml"

# (pre-commit hook id, pre-commit repo URL, CI workflow file (repo-relative),
#  validator module the pair references [for humans/audit only]) -> both sides
# must resolve to the identical pinned omnibase_core SHA.
#
# Intentionally EMPTY: omnibase_core is the layering root and pins no external
# omnibase_core git-SHA (see module docstring). The `--self-test` mode keeps the
# comparator honest until the first real pair is added.
PIN_PAIRS: tuple[tuple[str, str, str, str], ...] = ()

_CI_PIN_RE = re.compile(
    r"omnibase-core\s*@\s*git\+https://github\.com/OmniNode-ai/omnibase_core"
    r"(?:\.git)?@([0-9a-f]{40})"
)


def _find_hook_rev(config: dict[str, Any], hook_id: str, repo_url: str) -> str | None:
    for repo in config.get("repos", []):
        if repo.get("repo") != repo_url:
            continue
        for hook in repo.get("hooks", []):
            if hook.get("id") == hook_id:
                rev = repo.get("rev")
                return str(rev) if rev is not None else None
    return None


def _find_ci_pins(ci_text: str) -> list[str]:
    return [m.group(1) for m in _CI_PIN_RE.finditer(ci_text)]


def _check_pair(
    hook_id: str,
    repo_url: str,
    ci_workflow_rel: str,
    validator: str,
    config: dict[str, Any],
    ci_text: str | None,
) -> list[str]:
    """Compare one pin pair. `ci_text` is None when the workflow file is absent.

    Fail-closed: a missing workflow, a missing hook rev, or a missing CI pin are
    all violations (a pin that cannot be resolved is treated as drift, never as
    a pass)."""
    violations: list[str] = []

    if ci_text is None:
        violations.append(
            f"pin-parity: CI workflow {ci_workflow_rel!r} not found "
            f"(hook {hook_id!r}, validator {validator!r}) -- "
            "update PIN_PAIRS or restore the workflow."
        )
        return violations

    precommit_rev = _find_hook_rev(config, hook_id, repo_url)
    if precommit_rev is None:
        violations.append(
            f"pin-parity: hook id={hook_id!r} not found under repo={repo_url!r} "
            f"in {CONFIG_PATH.name} -- update PIN_PAIRS or the config."
        )
        return violations

    ci_pins = _find_ci_pins(ci_text)
    if not ci_pins:
        violations.append(
            f"pin-parity: no CI-pinned SHA found in {ci_workflow_rel} "
            f"(hook {hook_id!r}, validator {validator!r}) -- "
            "update PIN_PAIRS or restore the CI pin."
        )
        return violations

    mismatched = sorted({p for p in ci_pins if p != precommit_rev})
    if mismatched:
        violations.append(
            f"pin-parity: hook {hook_id!r} pins rev={precommit_rev} in "
            f"{CONFIG_PATH.name}, but {ci_workflow_rel} pins {mismatched} "
            f"for the same validator ({validator}). These must match -- "
            "bump whichever side is stale."
        )
    return violations


def run_pin_parity(config: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for hook_id, repo_url, ci_workflow_rel, validator in PIN_PAIRS:
        ci_workflow_path = REPO_ROOT / ci_workflow_rel
        ci_text = (
            ci_workflow_path.read_text(encoding="utf-8")
            if ci_workflow_path.is_file()
            else None
        )
        violations.extend(
            _check_pair(hook_id, repo_url, ci_workflow_rel, validator, config, ci_text)
        )
    return violations


def self_test() -> int:
    """Drive the comparator over synthetic fixtures and assert the verdicts.

    Proves the mechanism is live even while PIN_PAIRS is empty: a matched pair
    passes, a mismatched pair fails, and each missing-input case fails closed.
    """
    good_sha = "a" * 40
    bad_sha = "b" * 40
    repo_url = "https://github.com/OmniNode-ai/omnibase_core"
    hook_id = "synthetic-validator"
    ci_rel = ".github/workflows/synthetic-gate.yml"
    validator = "validator_synthetic"

    def cfg(rev: str) -> dict[str, Any]:
        return {"repos": [{"repo": repo_url, "rev": rev, "hooks": [{"id": hook_id}]}]}

    ci_pinned = (
        f'          uv run --with "omnibase-core @ '
        f'git+https://github.com/OmniNode-ai/omnibase_core@{good_sha}" foo\n'
    )

    cases: list[tuple[str, bool, dict[str, Any], str | None]] = [
        # (label, expect_violation, config, ci_text)
        ("matched pair passes", False, cfg(good_sha), ci_pinned),
        ("mismatched rev fails", True, cfg(bad_sha), ci_pinned),
        ("missing CI workflow fails closed", True, cfg(good_sha), None),
        ("missing hook rev fails closed", True, {"repos": []}, ci_pinned),
        ("no CI pin fails closed", True, cfg(good_sha), "no pin here\n"),
    ]

    failures: list[str] = []
    for label, expect_violation, config, ci_text in cases:
        got = _check_pair(hook_id, repo_url, ci_rel, validator, config, ci_text)
        if bool(got) != expect_violation:
            failures.append(
                f"self-test case {label!r}: expected "
                f"{'a violation' if expect_violation else 'no violation'}, "
                f"got {got!r}"
            )

    if failures:
        print("FAIL: pin-parity self-test detected a broken comparator:\n")
        for f in failures:
            print(f"  {f}\n")
        return 1

    print(f"OK: pin-parity self-test passed ({len(cases)} synthetic cases).")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--self-test" in args:
        return self_test()

    if not CONFIG_PATH.is_file():
        print(f"ERROR: {CONFIG_PATH} not found", file=sys.stderr)
        return 1

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        print(f"ERROR: {CONFIG_PATH} did not parse to a mapping", file=sys.stderr)
        return 1

    violations = run_pin_parity(config)

    if violations:
        print(f"FAIL: {len(violations)} pin-parity violation(s):\n")
        for v in violations:
            print(f"  {v}\n")
        return 1

    if not PIN_PAIRS:
        print(
            "OK: no cross-repo omnibase_core pin pairs to compare "
            "(layering root; PIN_PAIRS intentionally empty -- run --self-test "
            "to verify the comparator)."
        )
    else:
        print("OK: all pinned revs in PIN_PAIRS match their CI-pinned counterpart.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
