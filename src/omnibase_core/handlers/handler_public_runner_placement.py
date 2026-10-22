# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerPublicRunnerPlacement -- no public-repository job runs on the fleet.

RULING 2026-10-16T07:07:09Z (OMN-19998): "Ci runners should be for private
repos only." In a PUBLIC repository this handler refuses every job whose
``runs-on`` is, or can resolve to, anything but a GitHub-hosted label:

* a literal label that is not ``ubuntu-*``, ``windows-*`` or ``macos-*``
  (``self-hosted``, ``omnibase-ci``, ``omnibase-deploy``, a ``group:``), and
* a computed ``runs-on`` expression that names such a label or reads a value
  the workflow cannot prove hosted (``vars.``, ``needs.``, ``matrix.``,
  ``inputs.``, ``env.``, ``secrets.``, ``steps.``).

There is no baseline (OMN-21280): each such job is a FAIL (rule
``self_hosted_in_public``). One computed shape is proved hosted for a public
repository: ``github.event.repository.private && (<route>) || <hosted label>``,
whose parenthesized route only a private repository (or a private caller of a
reusable workflow) can take. A private repository passes: self-hosted runners
are where its CI belongs. Jobs that call a reusable workflow with ``uses:``
carry no ``runs-on`` and are judged where the callee is defined.

Pure: no filesystem, no clock, no global state. Tickets: OMN-19998, OMN-21280.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Final, Literal

import yaml

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.models.version_drift.model_public_runner_placement_input import (
    ModelPublicRunnerPlacementInput,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

__all__ = [
    "VALIDATOR_ID",
    "HandlerPublicRunnerPlacement",
    "self_hosted_jobs",
]

VALIDATOR_ID: Final[str] = "public_runner_placement"
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"
_HOSTED_LABEL = re.compile(r"^(ubuntu|windows|macos)-[\w.\-]+$", re.IGNORECASE)
# Contexts whose value the workflow cannot prove to be a hosted label.
_UNPROVABLE = re.compile(
    r"\b(?:vars|needs|matrix|inputs|env|secrets|steps)\.", re.IGNORECASE
)
# A quoted value an expression can return: after `&&`, `||`, `?` or `:`.
_RETURNED_LITERAL = re.compile(r"""(?:&&|\|\||\?|:)\s*['"]([^'"]+)['"]""")
# Each token owns its whitespace; failed arrays must not repartition it while
# backtracking through repeated empty labels (CodeQL, OMN-19998).
_JSON_ARRAY_LITERAL = re.compile(r"""\[\s*+(?:"[^"]*+"\s*+,?+\s*+)++\]""")
# `github.event.repository.private && (` opening a private-caller route.
_PRIVATE_GUARD = re.compile(r"^github\.event\.repository\.private\s*&&\s*\(")
_HOSTED_FALLBACK = re.compile(
    r"""^\|\|\s*(?:'([^']+)'|fromJSON\(\s*'(\[[^']*\])'\s*\))$"""
)
_REMEDIATION: Final[str] = (
    "Run the job on a GitHub-hosted label (ubuntu-latest), or move it to a bus "
    "node the private lab runs (plan: knowledge_base_internal#1340). CI runners are "
    "for private repositories only (RULING 2026-10-16T07:07:09Z, OMN-19998); there "
    "is no baseline to record the job in (OMN-21280)."
)


def _hosted(label: object) -> bool:
    return isinstance(label, str) and bool(_HOSTED_LABEL.match(label.strip()))


def _closing_paren(text: str, start: int) -> int | None:
    """Index of the ``)`` matching the ``(`` at ``start``; quoted text is skipped."""
    depth = 0
    quoted = False
    for index in range(start, len(text)):
        char = text[index]
        if char == "'":
            quoted = not quoted  # `''` inside a string toggles twice: no change
        elif quoted:
            continue
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _private_guarded(expression: str) -> bool:
    """True for ``${{ github.event.repository.private && (<route>) || <hosted> }}``.

    For a public repository the guard is false, so the expression is the hosted
    fallback whatever ``<route>`` reads. The route must be one parenthesized
    group, or an inner ``||`` would bind outside the guard.
    """
    body = expression.strip()
    if not (body.startswith("${{") and body.endswith("}}")):
        return False
    body = body[3:-2].strip()
    guard = _PRIVATE_GUARD.match(body)
    if guard is None:
        return False
    end = _closing_paren(body, guard.end() - 1)
    if end is None:
        return False
    fallback = _HOSTED_FALLBACK.match(body[end + 1 :].strip())
    if fallback is None:
        return False
    label, array = fallback.groups()
    if label is not None:
        return _hosted(label)
    labels = re.findall(r'"([^"]*)"', array)
    return bool(labels) and all(_hosted(item) for item in labels)


def _computed_is_unproven(expression: str) -> bool:
    """True when a ``runs-on`` expression can resolve to a non-hosted label."""
    if _private_guarded(expression):
        return False
    if _UNPROVABLE.search(expression) or "self-hosted" in expression.lower():
        return True
    literals = _RETURNED_LITERAL.findall(expression)
    for array in _JSON_ARRAY_LITERAL.findall(expression):
        literals.extend(re.findall(r'"([^"]*)"', array))
    return any(not _hosted(literal) for literal in literals)


def runs_on_kind(runs_on: object) -> str | None:
    """``self_hosted_label`` or ``computed`` when ``runs-on`` can leave GitHub-hosted; else None."""
    if isinstance(runs_on, str):
        if "${{" in runs_on:
            return "computed" if _computed_is_unproven(runs_on) else None
        return None if _hosted(runs_on) else "self_hosted_label"
    if isinstance(runs_on, list):
        for label in runs_on:
            kind = runs_on_kind(label)
            if kind is not None:
                return kind
        return None
    if isinstance(runs_on, Mapping):
        if "group" in runs_on:
            return "self_hosted_label"
        return runs_on_kind(runs_on.get("labels", []))
    return None


def self_hosted_jobs(source: str, path: str) -> dict[str, str]:
    """Job id to kind for each job of a workflow that can leave GitHub-hosted runners.

    Invalid YAML raises ``yaml.YAMLError`` or ``ValueError``.
    """
    document = load_yaml_mapping_no_duplicates(source, source=path)
    jobs = document.get("jobs")
    if not isinstance(jobs, Mapping):
        return {}
    found: dict[str, str] = {}
    for job_id, job in jobs.items():
        if not isinstance(job, Mapping) or "runs-on" not in job:
            continue
        kind = runs_on_kind(job["runs-on"])
        if kind is not None:
            found[str(job_id)] = kind
    return found


class HandlerPublicRunnerPlacement:
    """Refuse every public-repository job that can run on a self-hosted runner."""

    def handle(self, request: ModelPublicRunnerPlacementInput) -> ModelValidationReport:
        """Definition-B canonical entry-point (OMN-14355). Pure, no I/O, no clock."""
        if not request.public:
            return self._report(())

        errors: list[str] = []
        head: dict[str, dict[str, str]] = {}
        for file in request.files:
            try:
                head[file.path] = self_hosted_jobs(file.source, file.path)
            except (yaml.YAMLError, ValueError) as exc:
                errors.append(f"{file.path}: workflow does not parse: {exc}")
        if errors:
            return ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID, tuple(errors)
            )

        findings = [
            self._finding(
                f"{path}:jobs.{job}",
                f"{path}:jobs.{job}: {kind} runs-on in public repository "
                f"{request.repository} (rule self_hosted_in_public)",
            )
            for path in sorted(head)
            for job, kind in sorted(head[path].items())
        ]
        return self._report(tuple(findings))

    @staticmethod
    def _finding(location: str, message: str) -> ModelValidationFinding:
        return ModelValidationFinding(
            validator_id=VALIDATOR_ID,
            severity="FAIL",
            location=location,
            message=message,
            remediation=_REMEDIATION,
        )

    @staticmethod
    def _report(findings: tuple[ModelValidationFinding, ...]) -> ModelValidationReport:
        return ModelValidationReport.from_findings(
            findings=tuple(
                ModelValidationFindingEmbed(**f.model_dump(mode="json"))
                for f in findings
            ),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )
