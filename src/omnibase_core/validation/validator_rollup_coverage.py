# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Model-B rollup-coverage verifier for validator-requirements.yaml (OMN-13574).

The legacy :mod:`validator_requirements_consumer` proves each spec-required
validator is *present* as a pre-commit hook id and as a keyword somewhere in
``.github/workflows/*.yml``. It does NOT prove the validator actually *gates*
merge: a repo can be "baseline-clean" while the single required rollup never
depends on the job that runs the validator (it lives in a workflow with no
aggregator that is not in branch protection), or the job carries
``continue-on-error: true`` (so its failure is swallowed), or the keyword match
was incidental (e.g. ``pydantic`` matching ``pip install pydantic``).

This module closes that hole for **Model B** (operator-locked decision,
epic OMN-13573): keep ONE required aggregate rollup context per repo, but prove
it is AIRTIGHT — the rollup job's transitive ``needs`` graph reaches a real job
for every opted-in spec-required validator, and none of those jobs swallow
failure with ``continue-on-error: true``.

Per-repo opt-in lives under ``model_b_rollup_enforcement.repos`` in the spec.
Only listed repos are checked, so the other 11 repos' handshake gate is
unaffected (pilot scope; fleet rollout is OMN-13576).

Usage::

    uv run python -m omnibase_core.validation.validator_rollup_coverage \\
        --repo omnibase_core --repo-root .

Exit codes:
    0 — rollup is airtight for the repo (or repo not opted in)
    2 — one or more coverage gaps detected
"""

from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path
from typing import Any, Final

import yaml

from omnibase_core.models.validation.model_rollup_coverage_gap import (
    ModelRollupCoverageGap,
)

__all__ = ["RollupCoverageVerifier"]

_CANONICAL_SPEC_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "architecture-handshakes"
    / "validator-requirements.yaml"
)


def _as_list(value: Any) -> list[str]:
    """Normalize a workflow ``needs`` value (str | list | None) to list[str]."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


class RollupCoverageVerifier:
    """Verify that a repo's required rollup transitively covers every opted-in
    spec-required validator, with no failure-swallowing on the covering jobs."""

    def __init__(self, spec: dict[str, Any]) -> None:
        self._spec = spec
        enforcement = spec.get("model_b_rollup_enforcement")
        repos = enforcement.get("repos", {}) if isinstance(enforcement, dict) else {}
        self._repos: dict[str, Any] = repos if isinstance(repos, dict) else {}

    @classmethod
    def from_spec_path(cls, spec_path: Path) -> RollupCoverageVerifier:
        if not spec_path.exists():
            raise FileNotFoundError(  # error-ok: missing spec at load boundary
                f"validator-requirements.yaml missing at {spec_path}"
            )
        with spec_path.open() as fh:
            raw = yaml.safe_load(fh)
        if not isinstance(raw, dict):
            raise ValueError(  # error-ok: spec shape validation at load boundary
                "spec root must be a mapping"
            )
        return cls(raw)

    @classmethod
    def from_canonical(cls) -> RollupCoverageVerifier:
        return cls.from_spec_path(_CANONICAL_SPEC_PATH)

    def is_opted_in(self, repo_name: str) -> bool:
        return repo_name in self._repos

    def verify_repo(
        self, *, repo_name: str, repo_root: Path
    ) -> list[ModelRollupCoverageGap]:
        """Return coverage gaps for ``repo_name``. Empty list ⇒ airtight.

        A repo not listed under ``model_b_rollup_enforcement.repos`` returns an
        empty list (not opted in — pilot scope).

        Raises:
            ValueError: If the opt-in block is malformed or the named rollup
                workflow / job cannot be resolved (fail loud, never silent-pass).
        """
        cfg = self._repos.get(repo_name)
        if cfg is None:
            return []
        if not isinstance(cfg, dict):
            raise ValueError(  # error-ok: opt-in shape validation
                f"model_b_rollup_enforcement.repos[{repo_name!r}] must be a mapping"
            )

        rollup_workflow = cfg["rollup_workflow"]
        rollup_job = cfg["rollup_job"]
        rollup_context = cfg["required_rollup_context"]
        validator_jobs = cfg["validator_jobs"]
        if not isinstance(validator_jobs, dict):
            raise ValueError(  # error-ok: opt-in shape validation
                f"validator_jobs for {repo_name!r} must be a mapping"
            )

        workflow_path = repo_root / ".github" / "workflows" / rollup_workflow
        if not workflow_path.exists():
            raise ValueError(  # error-ok: opt-in points at a real workflow file
                f"rollup_workflow {rollup_workflow!r} not found at {workflow_path}"
            )
        with workflow_path.open() as fh:
            workflow = yaml.safe_load(fh)
        jobs = workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
        if not isinstance(jobs, dict) or rollup_job not in jobs:
            raise ValueError(  # error-ok: opt-in points at a real job key
                f"rollup_job {rollup_job!r} not defined in {rollup_workflow}"
            )

        # Assert the named rollup job actually emits the required context name.
        declared_name = jobs[rollup_job].get("name")
        gaps: list[ModelRollupCoverageGap] = []
        if declared_name != rollup_context:
            gaps.append(
                ModelRollupCoverageGap(
                    repo=repo_name,
                    validator="<rollup>",
                    detail=(
                        f"rollup_job {rollup_job!r} has name {declared_name!r}, "
                        f"expected required_rollup_context {rollup_context!r}"
                    ),
                )
            )

        reachable = self._transitive_needs(jobs, rollup_job)
        # The rollup job itself is trivially reachable (depends on its own needs);
        # include it so a validator mapped directly to the rollup job counts.
        reachable.add(rollup_job)

        for validator, job_keys in validator_jobs.items():
            keys = _as_list(job_keys)
            if not keys:
                gaps.append(
                    ModelRollupCoverageGap(
                        repo=repo_name,
                        validator=str(validator),
                        detail="validator_jobs entry lists no covering job",
                    )
                )
                continue
            # Coverage requires at least one mapped job to be (a) defined and
            # (b) transitively required by the rollup and (c) not swallowing
            # failure with continue-on-error.
            covered = False
            reasons: list[str] = []
            for key in keys:
                if key not in jobs:
                    reasons.append(f"{key!r} undefined in {rollup_workflow}")
                    continue
                if key not in reachable:
                    reasons.append(f"{key!r} not in transitive needs of {rollup_job!r}")
                    continue
                if self._swallows_failure(jobs[key]):
                    reasons.append(f"{key!r} has continue-on-error: true")
                    continue
                covered = True
                break
            if not covered:
                gaps.append(
                    ModelRollupCoverageGap(
                        repo=repo_name,
                        validator=str(validator),
                        detail=(
                            f"no covering job feeds rollup {rollup_context!r}: "
                            + "; ".join(reasons)
                        ),
                    )
                )

        return gaps

    @staticmethod
    def _swallows_failure(job: dict[str, Any]) -> bool:
        # continue-on-error: true makes the job result "success" even when its
        # steps fail, so an aggregator reading needs.<job>.result can never go
        # red on it. Treat literal true and the string "true".
        value = job.get("continue-on-error", False)
        return value is True or (isinstance(value, str) and value.strip() == "true")

    @staticmethod
    def _transitive_needs(jobs: dict[str, Any], start: str) -> set[str]:
        """All jobs transitively reachable through ``needs`` edges from ``start``."""
        seen: set[str] = set()
        queue: deque[str] = deque(_as_list(jobs.get(start, {}).get("needs")))
        while queue:
            job = queue.popleft()
            if job in seen:
                continue
            seen.add(job)
            if job in jobs:
                queue.extend(_as_list(jobs[job].get("needs")))
        return seen


def _format_gaps(gaps: list[ModelRollupCoverageGap]) -> str:
    lines = [f"{len(gaps)} rollup-coverage gap(s):"]
    for gap in gaps:
        lines.append(f"  [{gap.repo}] {gap.validator} — {gap.detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify Model-B rollup coverage (OMN-13574)."
    )
    parser.add_argument("--repo", required=True, help="Target repo name.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to target repo's working tree (default: cwd).",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help="Path to validator-requirements.yaml (default: canonical).",
    )
    args = parser.parse_args(argv)

    spec_path = args.spec or _CANONICAL_SPEC_PATH
    verifier = RollupCoverageVerifier.from_spec_path(spec_path)

    if not verifier.is_opted_in(args.repo):
        print(
            f"rollup-coverage: {args.repo} not opted into Model B (pilot scope) — skip",
            file=sys.stderr,
        )
        return 0

    gaps = verifier.verify_repo(repo_name=args.repo, repo_root=args.repo_root)
    if not gaps:
        print(
            f"rollup-coverage: AIRTIGHT ({args.repo} @ {args.repo_root})",
            file=sys.stderr,
        )
        return 0
    print(_format_gaps(gaps), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: standard CLI entry-point idiom
