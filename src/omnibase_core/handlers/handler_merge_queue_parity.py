# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerMergeQueueParity -- pull request CI runs every job the merge queue runs.

A job that runs on ``merge_group`` and not on ``pull_request`` fails first in
the merge queue, after the pull request read green, and holds every pull
request behind it: omnibase_infra's ``Runtime Boot Laptop Profile (catalog
local)`` did that for 6.5 hours on 2026-10-15. In every workflow that triggers
on ``merge_group``, this handler refuses:

* ``no_pull_request_trigger`` -- the workflow does not also trigger on
  ``pull_request``.
* ``pull_request_path_filter`` -- the ``pull_request`` trigger carries
  ``paths`` or ``paths-ignore``; a merge group runs the workflow unfiltered.
* ``merge_queue_only_if`` -- a job's ``if:`` can be true on ``merge_group``
  while false on ``pull_request`` for the same values of everything else. A
  skip on a draft pull request is not one: a draft never enters the queue.
* ``event_dependent_gate`` -- a job's ``if:`` reads ``needs.<job>.outputs`` and
  that job's steps read ``github.event_name``: a paths gate that answers
  "changed" for the queue and diffs for the pull request.

Findings in the caller's baseline WARN; the baseline only shrinks. Jobs of a
reusable workflow a job ``uses:`` are not followed.

Pure: no filesystem, no clock, no global state. Ticket: OMN-19998.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping
from typing import Final, Literal

import yaml

from omnibase_core.enums.enum_merge_queue_parity_rule import EnumMergeQueueParityRule
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.models.version_drift.model_merge_queue_parity_input import (
    ModelMergeQueueParityInput,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

__all__ = ["VALIDATOR_ID", "HandlerMergeQueueParity", "merge_queue_only"]

VALIDATOR_ID: Final[str] = "merge_queue_parity"
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"
_REMEDIATION: Final[str] = (
    "Run the job on pull_request whenever it runs on merge_group: drop the "
    "merge_group-only condition, the pull_request path filter, or the event-name "
    "branch in the gate job. Never add it to the baseline."
)
_PR_EVENTS: Final[tuple[str, ...]] = ("pull_request", "pull_request_target")
_MAX_UNKNOWNS: Final[int] = 10
_EVENT_ATOM = re.compile(
    r"""^\s*(?:github\.event_name\s*(==|!=)\s*['"]([^'"]*)['"]"""
    r"""|['"]([^'"]*)['"]\s*(==|!=)\s*github\.event_name)\s*$"""
)
_DRAFT_ATOM = re.compile(r"^\s*github\.event\.pull_request\.draft\s*$")
_NEEDS_OUTPUT = re.compile(r"needs\.([A-Za-z0-9_-]+)\.outputs\.")
_ANY_EVENT_NAME = re.compile(r"github\.event_name")


def _strip_expression(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("${{") and stripped.endswith("}}"):
        stripped = stripped[3:-2]
    return stripped.strip()


def _tokens(expression: str) -> list[str] | None:
    """Split an expression into ``(``, ``)``, ``&&``, ``||``, ``!`` and atoms.

    Quoted strings and a function call's argument list stay inside their atom.
    None means the expression could not be split (unbalanced).
    """
    tokens: list[str] = []
    atom: list[str] = []
    i = 0

    def flush() -> None:
        text = "".join(atom).strip()
        if text:
            tokens.append(text)
        atom.clear()

    while i < len(expression):
        char = expression[i]
        if char in "'\"":
            end = expression.find(char, i + 1)
            if end < 0:
                return None
            atom.append(expression[i : end + 1])
            i = end + 1
            continue
        if expression.startswith(("&&", "||"), i):
            flush()
            tokens.append(expression[i : i + 2])
            i += 2
            continue
        if char == "!" and not expression.startswith("!=", i):
            flush()
            tokens.append("!")
            i += 1
            continue
        if char == "(":
            if "".join(atom).strip() and re.search(r"[A-Za-z0-9_]$", "".join(atom)):
                depth = 0
                for j in range(i, len(expression)):
                    if expression[j] == "(":
                        depth += 1
                    elif expression[j] == ")":
                        depth -= 1
                        if depth == 0:
                            atom.append(expression[i : j + 1])
                            i = j + 1
                            break
                else:
                    return None
                continue
            flush()
            tokens.append("(")
            i += 1
            continue
        if char == ")":
            flush()
            tokens.append(")")
            i += 1
            continue
        atom.append(char)
        i += 1
    flush()
    return tokens


def _truth(tokens: list[str], values: Mapping[str, bool]) -> bool | None:
    """Evaluate the token list with atom truth values; None when malformed."""
    pos = 0

    def parse_or() -> bool | None:
        nonlocal pos
        left = parse_and()
        while left is not None and pos < len(tokens) and tokens[pos] == "||":
            pos += 1
            right = parse_and()
            left = None if right is None else (left or right)
        return left

    def parse_and() -> bool | None:
        nonlocal pos
        left = parse_not()
        while left is not None and pos < len(tokens) and tokens[pos] == "&&":
            pos += 1
            right = parse_not()
            left = None if right is None else (left and right)
        return left

    def parse_not() -> bool | None:
        nonlocal pos
        if pos < len(tokens) and tokens[pos] == "!":
            pos += 1
            inner = parse_not()
            return None if inner is None else not inner
        if pos < len(tokens) and tokens[pos] == "(":
            pos += 1
            inner = parse_or()
            if pos >= len(tokens) or tokens[pos] != ")":
                return None
            pos += 1
            return inner
        if pos < len(tokens) and tokens[pos] not in ("&&", "||", ")"):
            atom = tokens[pos]
            pos += 1
            return values.get(atom)
        return None

    result = parse_or()
    return result if pos == len(tokens) else None


def _event_value(atom: str, event: str) -> bool | None:
    # A pull request reaches the merge queue only once it is ready for review,
    # and a merge group has no pull request: the draft flag is false for both.
    if _DRAFT_ATOM.match(atom):
        return False
    match = _EVENT_ATOM.match(atom)
    if match is None:
        return None
    op = match.group(1) or match.group(4)
    name = match.group(2) if match.group(2) is not None else match.group(3)
    return (name == event) if op == "==" else (name != event)


def merge_queue_only(condition: str) -> bool:
    """True when ``condition`` can hold on ``merge_group`` and fail on ``pull_request``.

    Atoms that compare ``github.event_name`` are evaluated per event; every
    other atom is unknown and takes both truth values, the same value under
    both events. An expression that does not split or evaluate is not flagged.
    """
    tokens = _tokens(_strip_expression(condition))
    if not tokens:
        return False
    atoms = sorted({t for t in tokens if t not in ("(", ")", "&&", "||", "!")})
    unknowns = [a for a in atoms if _event_value(a, "merge_group") is None]
    if len(unknowns) > _MAX_UNKNOWNS:
        return False
    for combo in itertools.product((False, True), repeat=len(unknowns)):
        fixed = dict(zip(unknowns, combo, strict=True))
        on_queue = _truth(tokens, {**fixed, **_event_map(atoms, "merge_group")})
        on_pr = _truth(tokens, {**fixed, **_event_map(atoms, "pull_request")})
        if on_queue is None or on_pr is None:
            return False
        if on_queue and not on_pr:
            return True
    return False


def _event_map(atoms: list[str], event: str) -> dict[str, bool]:
    mapped: dict[str, bool] = {}
    for atom in atoms:
        value = _event_value(atom, event)
        if value is not None:
            mapped[atom] = value
    return mapped


def _triggers(document: Mapping[object, object]) -> dict[str, object]:
    # PyYAML (YAML 1.1) reads a bare ``on`` key as the boolean True.
    raw = document.get("on", document.get(True))
    if isinstance(raw, str):
        return {raw: None}
    if isinstance(raw, list):
        return {str(item): None for item in raw}
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _line_of(source: str, key: str, indent: int) -> int:
    pattern = re.compile(rf"^ {{{indent}}}['\"]?{re.escape(key)}['\"]?\s*:")
    for number, line in enumerate(source.splitlines(), start=1):
        if pattern.match(line):
            return number
    return 1


class HandlerMergeQueueParity:
    """COMPUTE handler that flags jobs the merge queue runs and pull request CI skips."""

    def handle(self, request: ModelMergeQueueParityInput) -> ModelValidationReport:
        """Definition-B canonical entry-point: typed request in, typed report out."""
        errors: list[str] = []
        raw: list[tuple[str, str, EnumMergeQueueParityRule, int, str]] = []
        for file in sorted(request.files, key=lambda f: f.path):
            try:
                document = load_yaml_mapping_no_duplicates(
                    file.source, source=file.path
                )
            except (yaml.YAMLError, ValueError) as exc:
                errors.append(f"{file.path}: workflow does not parse: {exc}")
                continue
            raw.extend(self._violations(file.path, file.source, document))
        if errors:
            return ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID, tuple(errors)
            )

        baseline = {entry.key(): entry for entry in request.baseline}
        seen: set[tuple[str, str, str]] = set()
        findings: list[ModelValidationFindingEmbed] = []
        for path, job, rule, line, detail in raw:
            key = (path, job, rule.value)
            seen.add(key)
            message = f"{path}:{line}: {rule.value}: {detail}"
            recorded = baseline.get(key)
            findings.append(
                ModelValidationFindingEmbed(
                    validator_id=VALIDATOR_ID,
                    severity="WARN" if recorded is not None else "FAIL",
                    location=f"{path}:{line}",
                    message=(
                        f"baselined ({recorded.ticket}): {message}"
                        if recorded is not None
                        else message
                    ),
                    remediation=_REMEDIATION,
                )
            )
        if request.report_stale_baseline:
            for key, entry in sorted(baseline.items()):
                if key in seen:
                    continue
                findings.append(
                    ModelValidationFindingEmbed(
                        validator_id=VALIDATOR_ID,
                        severity="WARN",
                        location=entry.path,
                        message=(
                            f"stale baseline entry ({entry.ticket}): {entry.path} job "
                            f"{entry.job} no longer violates {entry.rule.value}; "
                            "remove it from the baseline"
                        ),
                        remediation=None,
                    )
                )
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )

    @staticmethod
    def _violations(
        path: str, source: str, document: Mapping[object, object]
    ) -> list[tuple[str, str, EnumMergeQueueParityRule, int, str]]:
        triggers = _triggers(document)
        if "merge_group" not in triggers:
            return []
        found: list[tuple[str, str, EnumMergeQueueParityRule, int, str]] = []
        on_line = _line_of(source, "on", 0)
        pr_events = [e for e in _PR_EVENTS if e in triggers]
        if not pr_events:
            found.append(
                (
                    path,
                    "*",
                    EnumMergeQueueParityRule.NO_PULL_REQUEST_TRIGGER,
                    on_line,
                    "the workflow triggers on merge_group and not on pull_request",
                )
            )
        for event in pr_events:
            config = triggers[event]
            if isinstance(config, dict) and (
                "paths" in config or "paths-ignore" in config
            ):
                found.append(
                    (
                        path,
                        "*",
                        EnumMergeQueueParityRule.PULL_REQUEST_PATH_FILTER,
                        _line_of(source, event, 2),
                        f"the {event} trigger filters on paths; merge_group runs unfiltered",
                    )
                )

        jobs = document.get("jobs")
        if not isinstance(jobs, dict):
            return found
        for job_id, job in jobs.items():
            if not isinstance(job, dict):
                continue
            condition = job.get("if")
            if condition is None:
                continue
            condition = str(condition)
            line = _line_of(source, str(job_id), 2)
            if merge_queue_only(condition):
                found.append(
                    (
                        path,
                        str(job_id),
                        EnumMergeQueueParityRule.MERGE_QUEUE_ONLY_IF,
                        line,
                        f"job {job_id} can run on merge_group and be skipped on "
                        f"pull_request: if: {' '.join(condition.split())}",
                    )
                )
                continue
            for gate in sorted(set(_NEEDS_OUTPUT.findall(condition))):
                gate_job = jobs.get(gate)
                if not isinstance(gate_job, dict):
                    continue
                if _ANY_EVENT_NAME.search(repr(gate_job.get("steps", []))):
                    found.append(
                        (
                            path,
                            str(job_id),
                            EnumMergeQueueParityRule.EVENT_DEPENDENT_GATE,
                            line,
                            f"job {job_id} is gated on needs.{gate}.outputs and job "
                            f"{gate}'s steps branch on github.event_name",
                        )
                    )
                    break
        return found
