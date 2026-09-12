# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-18235 — the cascade generator may not silently stop emitting provenance.

``dependency-cascade.yml`` already emits a machine-readable provenance block
(OMN-16286): a ``Cascade provenance`` heading carrying the source repository and
the released version the bump was opened to deliver. ``omnibase_infra#3446``
carries exactly that.

What was missing is that **nothing asserted it**. No consumer parsed the block
and no test required it, so the generator could drop it in an unrelated edit and
every downstream reader would simply see a bump with no provenance -- with no
red anywhere.

That matters now because the block is load-bearing. Clause 1 of the OMN-18233
verified-supersession predicate resolves against it: a closed cascade bump is
ignorable by the evidence closer ONLY when it declares a source package and a
required version. A generator that can stop emitting the block makes that
predicate silently unresolvable, which means every ticket whose release opens
downstream bumps goes back to being blocked forever by a pull request that can
never merge. The predicate fails closed, so the failure is a permanent hold
rather than a wrong flip -- which is the safe direction and still costs the
lane-hours this phase exists to remove.

**The consumer lives in another repository and cannot be imported here.**
``omnibase_infra`` depends on ``omnibase_core``, never the reverse, so this test
carries its own structural reader rather than importing the parser at
``omnibase_infra`` ``src/omnibase_infra/nodes/node_evidence_autoclose_sweep_effect/handlers/cascade_supersession.py``.
The two are pinned to the same shape deliberately: the field names, the bullet
form and the section binding asserted below are exactly what that parser reads,
and a change to either side must change both.

**Every assertion here has a negative control.** A test that asserts a string is
present in a file passes just as happily when it is asserting nothing, so each
structural rule below is also run against a body that violates it and is
required to FAIL. That is what makes "a cascade bump with no machine-readable
provenance block fails the generator's own test" a measured property rather than
an intention.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency-cascade.yml"

#: The step whose `gh pr create --body` heredoc IS the emitted pull request body.
_PR_STEP_NAME = "Open pull request"
_JOB_NAME = "open-bump-pr"

#: The shape the OMN-18233 consumer parses. Kept verbatim beside the parser's
#: own regexes; see this module's docstring for why they are not shared code.
_PROVENANCE_HEADING_RE = re.compile(r"^#{2,6}\s+cascade\s+provenance\b", re.IGNORECASE)
_ANY_HEADING_RE = re.compile(r"^#{1,6}\s+")
_SOURCE_REPO_RE = re.compile(
    r"^\s*[-*]\s*Source repo:\s*`?([\w.-]+/[\w.-]+)`?\s*$", re.IGNORECASE
)
_RELEASED_VERSION_RE = re.compile(
    r"^\s*[-*]\s*Released version:\s*`?([^`\s]+)`?\s*$", re.IGNORECASE
)

#: Concrete values standing in for the workflow's own resolved outputs, chosen
#: to match the real `omnibase_infra#3446` bump so the rendered body is the body
#: the consumer was measured against.
_RENDER_VALUES = {
    "steps.vars.outputs.package": "omnibase_core",
    "steps.vars.outputs.pkg_hyphen": "omnibase-core",
    "steps.vars.outputs.version": "0.47.12",
    "steps.vars.outputs.ticket": "OMN-18201",
    "steps.vars.outputs.evidence_source": "OCC#9159",
    "steps.vars.outputs.branch": "automation/bump-omnibase-core-0.47.12-omn-18201",
    "github.server_url": "https://github.com",
    "github.repository": "OmniNode-ai/omnibase_core",
    "github.run_id": "34665021693",
}

_EXPRESSION_RE = re.compile(r"\$\{\{\s*(?P<expr>[^}]+?)\s*\}\}")


def _pr_create_script() -> str:
    with WORKFLOW_PATH.open() as handle:
        document = yaml.safe_load(handle)
    job = document["jobs"][_JOB_NAME]
    for step in job["steps"]:
        if isinstance(step, dict) and step.get("name") == _PR_STEP_NAME:
            run = step.get("run", "")
            assert isinstance(run, str)
            return run
    raise AssertionError(
        f"job {_JOB_NAME!r} has no step named {_PR_STEP_NAME!r}; the generator's "
        "pull request body could not be located, which is itself the failure "
        "this module exists to catch"
    )


def _body_template() -> str:
    """The heredoc that becomes the bump pull request's body, dedented."""
    script = _pr_create_script()
    opener = "<<'PREOF'"
    start = script.find(opener)
    assert start != -1, (
        "the `gh pr create` step no longer builds its body from a quoted "
        f"heredoc; the emitted body cannot be read:\n{script}"
    )
    start = script.index("\n", start) + 1
    end = script.find("PREOF", start)
    assert end != -1, "unterminated body heredoc in the `gh pr create` step"
    return textwrap.dedent(script[start:end])


def _render(template: str) -> str:
    """The template with its workflow expressions resolved to concrete values.

    An expression this module does not know about renders to a visible marker
    rather than to an empty string: a silently-empty substitution would let a
    field that resolves to nothing pass a presence assertion.
    """

    def substitute(match: re.Match[str]) -> str:
        expression = match.group("expr")
        return _RENDER_VALUES.get(expression, f"<UNRESOLVED:{expression}>")

    return _EXPRESSION_RE.sub(substitute, template)


def read_cascade_provenance(body: str) -> tuple[str, str] | None:
    """``(source_repo, released_version)`` from the provenance block, or ``None``.

    Structural, and bound to the heading: the two fields count only when they
    appear INSIDE the provenance section, before the next heading. A body whose
    summary happens to spell the field names declares no provenance.
    """
    in_section = False
    source_repo = ""
    released_version = ""
    for line in body.splitlines():
        if _PROVENANCE_HEADING_RE.match(line):
            in_section = True
            continue
        if in_section and _ANY_HEADING_RE.match(line):
            break
        if not in_section:
            continue
        source_match = _SOURCE_REPO_RE.match(line)
        if source_match and not source_repo:
            source_repo = source_match.group(1)
            continue
        version_match = _RELEASED_VERSION_RE.match(line)
        if version_match and not released_version:
            released_version = version_match.group(1)
    if not source_repo or not released_version:
        return None
    return source_repo, released_version


# ------------------------------------------------------- the assertion -------


@pytest.mark.unit
def test_the_generator_emits_a_readable_provenance_block() -> None:
    """AC1, positive half. The live workflow's body declares both fields."""
    declared = read_cascade_provenance(_render(_body_template()))

    assert declared is not None, (
        "the cascade generator's pull request body carries no machine-readable "
        "provenance block. Clause 1 of the OMN-18233 supersession predicate "
        "resolves against this block, so without it every closed cascade bump "
        "blocks its ticket permanently:\n" + _render(_body_template())
    )
    source_repo, released_version = declared
    assert source_repo == "OmniNode-ai/omnibase_core", source_repo
    assert released_version == "0.47.12", released_version


@pytest.mark.unit
def test_both_fields_resolve_from_the_workflow_and_are_not_literals() -> None:
    """The fields must carry the run's OWN package and version.

    A block hardcoding a package name would read as present forever and be
    wrong on every bump but one.
    """
    template = _body_template()
    lines = template.splitlines()
    in_section = False
    source_line = ""
    version_line = ""
    for line in lines:
        if _PROVENANCE_HEADING_RE.match(line.strip()):
            in_section = True
            continue
        if in_section and _ANY_HEADING_RE.match(line.strip()):
            break
        if not in_section:
            continue
        if re.match(r"^\s*[-*]\s*Source repo:", line, re.IGNORECASE):
            source_line = line
        if re.match(r"^\s*[-*]\s*Released version:", line, re.IGNORECASE):
            version_line = line

    assert "${{ steps.vars.outputs.package }}" in source_line, source_line
    assert "${{ steps.vars.outputs.version }}" in version_line, version_line
    assert "<UNRESOLVED:" not in _render(source_line + "\n" + version_line)


@pytest.mark.unit
def test_the_source_repo_field_renders_to_an_owner_slash_name() -> None:
    """Clause 1 needs a repository, not a bare package name.

    The consumer derives the pinned distribution from the repository's NAME
    half, so a field carrying only `omnibase_core` would parse as a repo with
    no owner and resolve to nothing.
    """
    declared = read_cascade_provenance(_render(_body_template()))
    assert declared is not None
    source_repo, _version = declared
    assert source_repo.count("/") == 1, source_repo
    owner, name = source_repo.split("/")
    assert owner and name, source_repo


# ------------------------------------------------- the negative controls -----


@pytest.mark.unit
def test_a_body_with_the_provenance_heading_removed_fails_the_assertion() -> None:
    """AC1, the half that makes the assertion above mean something.

    This is the exact regression the ticket names: the generator drops the
    block in an unrelated edit. It must go red, and this control proves the
    reader is capable of going red at all.
    """
    body = _render(_body_template())
    without_heading = "\n".join(
        line for line in body.splitlines() if not _PROVENANCE_HEADING_RE.match(line)
    )

    assert read_cascade_provenance(without_heading) is None


@pytest.mark.unit
def test_a_body_missing_only_the_version_field_fails_the_assertion() -> None:
    """A half-emitted block is not a block. Clause 1 needs both fields."""
    body = _render(_body_template())
    without_version = "\n".join(
        line
        for line in body.splitlines()
        if not re.match(r"^\s*[-*]\s*Released version:", line, re.IGNORECASE)
    )

    assert read_cascade_provenance(without_version) is None


@pytest.mark.unit
def test_a_body_missing_only_the_source_repo_field_fails_the_assertion() -> None:
    body = _render(_body_template())
    without_source = "\n".join(
        line
        for line in body.splitlines()
        if not re.match(r"^\s*[-*]\s*Source repo:", line, re.IGNORECASE)
    )

    assert read_cascade_provenance(without_source) is None


@pytest.mark.unit
def test_fields_outside_the_provenance_section_do_not_count() -> None:
    """The section binding is a rule, not an accident of ordering.

    A generator that moved the two bullets up under `## Summary` would keep
    every substring present while declaring no provenance, and a loose reader
    would call that a pass.
    """
    loose = (
        "## Summary\n\n"
        "- Source repo: `OmniNode-ai/omnibase_core`\n"
        "- Released version: `0.47.12`\n\n"
        "## Test plan\n\n- [ ] CI passes\n"
    )

    assert read_cascade_provenance(loose) is None


@pytest.mark.unit
def test_an_ordinary_pull_request_body_declares_no_provenance() -> None:
    """The reader must not turn every pull request into a cascade bump."""
    ordinary = (
        "## Summary\n\nFixes the disk guard so it halts on free space.\n\n"
        "## Test plan\n\n- [x] unit tests\n"
    )

    assert read_cascade_provenance(ordinary) is None
