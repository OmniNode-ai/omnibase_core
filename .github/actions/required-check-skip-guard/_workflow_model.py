#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# VENDORED COPY (OMN-14863, fan-out from OMN-14854 omniclaude canary).
# Canonical source: OmniNode-ai/omniclaude
# .github/actions/required-check-skip-guard/_workflow_model.py
# See validate_no_required_check_skip_vectors.py in this same directory for
# the vendoring rationale.
#
# Required-Check Skip-Vector Guard (OMN-14854) — shared workflow-parsing model.
#
# Implements the context->job resolution algorithm from the design spec §1:
# every live `required_status_checks` context string is mapped back to the
# GitHub Actions job that produces it, walking through at most one level of
# `uses:` reusable-workflow nesting (Shape A/B/C). This module is imported by
# both the PR-time validator (validate_no_required_check_skip_vectors.py) and
# the privileged reconcile job (reconcile_manifest_vs_live.py) so the
# resolution logic is defined exactly once (DRY).
#
# Deliberately dependency-light: PyYAML only (already an omniclaude runtime
# dependency, see pyproject.toml). No network I/O in this module.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# GitHub Actions events this guard treats as "PR-reachable" — the only events
# `required_status_checks` can ever gate (branch protection cannot see push,
# schedule, or workflow_dispatch runs).
PR_REACHABLE_EVENTS = ("pull_request", "pull_request_target", "merge_group")

# Local-repo `uses:` cross-references to this same org/repo (self-referential
# `OmniNode-ai/omniclaude/.github/workflows/x.yml@ref` form some callers use
# instead of the `./` relative form). Resolved locally exactly like `./`.
_SELF_REPO_USES_RE = re.compile(
    r"^OmniNode-ai/omniclaude/\.github/workflows/(?P<path>[^@]+)@[^/]+$"
)
_LOCAL_USES_RE = re.compile(r"^\./\.github/workflows/(?P<path>[^@]+)$")


class UnresolvedContext(Exception):
    """Raised when a required context cannot be mapped to any local job."""


class UnclassifiableCondition(Exception):
    """Raised internally when `classify()` cannot symbolically evaluate an if:."""


@dataclass
class ParsedJob:
    job_id: str
    raw: dict[str, Any]

    @property
    def name(self) -> str:
        return str(self.raw.get("name") or self.job_id)

    @property
    def if_expr(self) -> str | None:
        expr = self.raw.get("if")
        return str(expr) if expr is not None else None

    @property
    def uses(self) -> str | None:
        uses = self.raw.get("uses")
        return str(uses) if uses is not None else None


@dataclass
class ParsedWorkflow:
    path: Path
    raw: dict[str, Any]
    jobs: dict[str, ParsedJob] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for job_id, job_raw in (self.raw.get("jobs") or {}).items():
            self.jobs[job_id] = ParsedJob(job_id=job_id, raw=job_raw or {})

    @property
    def on_block(self) -> dict[str, Any]:
        """Normalize the `on:` block to a dict, regardless of source shape.

        YAML `on:` may be a bare string (`on: push`), a list
        (`on: [push, pull_request]`), or a mapping (`on: {pull_request: {...}}`).
        PyYAML also parses the bare word `on` as the boolean `True` under
        YAML 1.1 core schema rules in some edge cases — guarded for below.
        """
        # PyYAML's default (non-safe-adjacent) resolver can turn the literal
        # scalar key `on` into the boolean True. safe_load with the standard
        # SafeLoader does this for the *key* `on` under YAML 1.1 bool
        # resolution history; guard both spellings defensively.
        raw_any: dict[Any, Any] = self.raw
        on_val = raw_any.get("on", raw_any.get(True))
        if on_val is None:
            return {}
        if isinstance(on_val, str):
            return {on_val: {}}
        if isinstance(on_val, list):
            return {str(k): {} for k in on_val}
        if isinstance(on_val, dict):
            return {str(k): (v or {}) for k, v in on_val.items()}
        return {}

    def triggers_on_pr_or_merge_group(self) -> bool:
        return any(evt in self.on_block for evt in PR_REACHABLE_EVENTS)

    def path_filtered_pr_events(self) -> list[str]:
        """Return PR-reachable event names whose trigger carries a paths filter."""
        hits: list[str] = []
        for evt in PR_REACHABLE_EVENTS:
            cfg = self.on_block.get(evt)
            if isinstance(cfg, dict) and ("paths" in cfg or "paths-ignore" in cfg):
                hits.append(evt)
        return hits


@dataclass
class ResolvedJob:
    workflow: ParsedWorkflow
    job_id: str
    # None for Shape A (direct job); set for Shape B/C (caller job that
    # invokes the reusable workflow producing the composed context).
    caller_job_id: str | None = None
    nested_workflow: ParsedWorkflow | None = None
    nested_job_id: str | None = None
    # True when the composed context's second half resolves into a reusable
    # workflow this repo cannot read (cross-org `uses:` ref).
    cross_repo_ref: str | None = None

    @property
    def is_nested(self) -> bool:
        return self.caller_job_id is not None


def load_workflows(workflows_dir: Path) -> dict[str, ParsedWorkflow]:
    """Parse every *.yml/*.yaml file directly under workflows_dir (no recursion:
    GitHub Actions does not read workflows from subdirectories)."""
    workflows: dict[str, ParsedWorkflow] = {}
    for pattern in ("*.yml", "*.yaml"):
        for path in sorted(workflows_dir.glob(pattern)):
            with path.open(encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            if not isinstance(raw, dict):
                continue
            key = path.name
            workflows[key] = ParsedWorkflow(path=path, raw=raw)
    return workflows


def resolve_uses_ref(
    uses_ref: str, workflows: dict[str, ParsedWorkflow]
) -> ParsedWorkflow | None:
    """Resolve a job's `uses:` reference to a locally-parseable ParsedWorkflow,
    or None if the reference points outside this repo (cross-repo reusable —
    e.g. omnibase_core's occ-preflight.yml, onex_change_control's
    pr-title-check-reusable.yml)."""
    local_match = _LOCAL_USES_RE.match(uses_ref)
    if local_match:
        return workflows.get(Path(local_match.group("path")).name)
    self_repo_match = _SELF_REPO_USES_RE.match(uses_ref)
    if self_repo_match:
        return workflows.get(Path(self_repo_match.group("path")).name)
    return None


def resolve_context_to_job(
    context: str, workflows: dict[str, ParsedWorkflow]
) -> ResolvedJob:
    """Implements the design spec §1 mapping algorithm.

    Tries Shape A (plain job name/id match) first, then Shape B/C
    (`<caller_job_id> / <rest>` composed contexts, where `<rest>` is matched
    verbatim against the reusable job's own display name — this handles the
    real "call-reject-skip-token / scan / reject-skip-gate-token" case where
    the reusable job's own `name:` field itself contains a `/`).

    Deliberately does NOT filter candidate workflows by
    `triggers_on_pr_or_merge_group()` before matching: doing so would make
    vector 4 (missing pull_request/merge_group trigger entirely) unreachable,
    since a workflow lacking that trigger would be skipped during resolution
    and the context would surface as `UnresolvedContext` instead of the more
    specific, more actionable "no PR trigger" finding. The trigger check is
    still applied — just downstream, against the resolved job's own workflow
    — by the caller (see validate_no_required_check_skip_vectors.py).
    """
    for wf in workflows.values():
        for job_id, job in wf.jobs.items():
            if job.name == context:
                return ResolvedJob(workflow=wf, job_id=job_id)

    for wf in workflows.values():
        for job_id, job in wf.jobs.items():
            if job.uses is None:
                continue
            prefix = f"{job_id} / "
            if not context.startswith(prefix):
                continue
            remainder = context[len(prefix) :]
            reusable_wf = resolve_uses_ref(job.uses, workflows)
            if reusable_wf is None:
                # Cross-repo reusable: caller side resolves, far side does not.
                return ResolvedJob(
                    workflow=wf,
                    job_id=job_id,
                    caller_job_id=job_id,
                    cross_repo_ref=job.uses,
                )
            for r_job_id, r_job in reusable_wf.jobs.items():
                if r_job.name == remainder:
                    return ResolvedJob(
                        workflow=wf,
                        job_id=job_id,
                        caller_job_id=job_id,
                        nested_workflow=reusable_wf,
                        nested_job_id=r_job_id,
                    )

    raise UnresolvedContext(context)


# ---------------------------------------------------------------------------
# Conditional classifier (design spec §2 `classify(if_expr)`)
# ---------------------------------------------------------------------------

ALWAYS_TRUE_FOR_PR = "ALWAYS_TRUE_FOR_PR"
UNGUARDED_CONDITIONAL = "UNGUARDED_CONDITIONAL"

# Anything referencing these is never in the provably-safe set (spec §2), full
# stop — no partial credit, even if combined with a safe event-name check.
_UNSAFE_REFERENCE_RE = re.compile(
    r"github\.actor"
    r"|github\.event\.(?!repository\b|action\b)"  # allow harmless event.* only defensively; still excluded below
    r"|needs\."
    r"|steps\."
    r"|vars\."
    r"|secrets\."
)

_EVENT_NAME_TOKEN_RE = re.compile(r"github\.event_name")


def classify(if_expr: str | None, declared_events: tuple[str, ...]) -> str:
    """Classify a job-level `if:` expression per spec §2.

    - Absent `if:` -> ALWAYS_TRUE_FOR_PR.
    - `always()` -> ALWAYS_TRUE_FOR_PR.
    - An expression referencing ONLY `github.event_name` (via ==, !=, &&, ||,
      parens) is evaluated symbolically for each PR-reachable event declared
      on the workflow's own `on:` block; ALWAYS_TRUE_FOR_PR only if it is true
      for every one of them.
    - Anything referencing github.actor / github.event.* / needs.* / steps.* /
      vars.* / secrets.* (or any other non-event-name predicate) is
      UNGUARDED_CONDITIONAL, unconditionally — this is intentionally stricter
      than "provably safe", per spec §2's explicit no-partial-credit rule.
    """
    if if_expr is None:
        return ALWAYS_TRUE_FOR_PR

    expr = if_expr.strip()
    if expr in ("always()", "${{ always() }}"):
        return ALWAYS_TRUE_FOR_PR

    # Strip the ${{ }} wrapper if present (GHA allows bare or wrapped forms).
    inner = expr
    if inner.startswith("${{") and inner.endswith("}}"):
        inner = inner[3:-2].strip()

    if _UNSAFE_REFERENCE_RE.search(inner):
        return UNGUARDED_CONDITIONAL

    if not _EVENT_NAME_TOKEN_RE.search(inner):
        # References neither event_name nor any known-unsafe token but is not
        # `always()`/absent either (e.g. a bare boolean literal, or something
        # this classifier doesn't recognize) — fail closed, no partial credit.
        return UNGUARDED_CONDITIONAL

    events_to_check = [e for e in declared_events if e in PR_REACHABLE_EVENTS] or list(
        PR_REACHABLE_EVENTS
    )

    py_expr = (
        inner.replace("&&", " and ")
        .replace("||", " or ")
        .replace("github.event_name", "__EVENT_NAME__")
    )
    py_expr = re.sub(r"(?<![=!<>])==(?!=)", "==", py_expr)

    for event in events_to_check:
        candidate = py_expr.replace("__EVENT_NAME__", repr(event))
        try:
            result = eval(candidate, {"__builtins__": {}}, {})  # noqa: S307
        except Exception:
            return UNGUARDED_CONDITIONAL
        if not result:
            return UNGUARDED_CONDITIONAL

    return ALWAYS_TRUE_FOR_PR
