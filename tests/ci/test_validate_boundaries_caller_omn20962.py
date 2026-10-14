# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20962: the boundary-validation job calls omnibase_core's own action.

OMN-20074 moved the validate-boundaries composite action out of the
change-control repository. The ``boundary-validation`` job in ci.yml keeps its
job id, name and check-run context and changes only its ``uses:`` line, to the
full commit sha of the merge that added the action (omnibase_core#1942).
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
REQUIRED_CHECKS = REPO_ROOT / ".github" / "required-checks.yaml"

JOB_ID = "boundary-validation"
CONTEXT = "Cross-repo boundary validation"
ACTION = "OmniNode-ai/omnibase_core/.github/actions/validate-boundaries"
# Exact reviewed action revisions from the original migration and #1977.
AUDITED_ACTION_USES = {
    f"{ACTION}@de3398d1fcf7a6f48451f680b74b1a6c6c383b8a",
    f"{ACTION}@c1f8e8fe0c513c0ac70ad666433a3ce1cec136c1",
}
_PINNED_USES = re.compile(
    rf"^(?:{'|'.join(re.escape(uses) for uses in sorted(AUDITED_ACTION_USES))})$"
)
_RETIRED_ACTION = re.compile(
    r"onex_change_control/\.github/actions/validate-boundaries"
)


def _job() -> dict[str, Any]:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"][JOB_ID]


def _retired_references(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if _RETIRED_ACTION.search(line)]


def test_boundary_validation_job_calls_the_core_action_at_the_merge_sha() -> None:
    uses = [s["uses"].split(" ")[0] for s in _job()["steps"] if "uses" in s]

    assert [u for u in uses if _PINNED_USES.fullmatch(u)] != []


def test_no_workflow_calls_the_retired_change_control_action() -> None:
    offenders = {
        path.name: _retired_references(path.read_text(encoding="utf-8"))
        for path in sorted((REPO_ROOT / ".github").rglob("*.yml"))
    }

    assert {name: refs for name, refs in offenders.items() if refs} == {}


def test_retired_action_reference_is_detected() -> None:
    old = (
        "      - uses: OmniNode-ai/onex_change_control/.github/actions/"
        "validate-boundaries@77f63a25b67db14dbca603ed8f841c3c5c4ee93e # dev"
    )

    assert _retired_references(old) == [old.strip()]


def _core_action_file() -> Path:
    """The action.yml in this tree that the job's omnibase_core ``uses:`` line names."""
    prefix = "OmniNode-ai/omnibase_core/"
    paths = [
        s["uses"].split("@")[0].removeprefix(prefix)
        for s in _job()["steps"]
        if s.get("uses", "").startswith(prefix)
    ]
    assert len(paths) == 1, f"expected one omnibase_core action step, found {paths}"
    return REPO_ROOT / paths[0] / "action.yml"


def test_the_called_action_runs_core_handlers_that_fail_a_drifted_fixture(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Run the module the called action names, as the action runs it, on both fixtures."""
    action = _core_action_file().read_text(encoding="utf-8")
    module = re.search(
        r"python -m (omnibase_core\.handlers\.handler_boundary_parity)\b", action
    )
    assert module is not None, (
        "the called action does not run the boundary-parity handler"
    )
    main = importlib.import_module(module.group(1)).main

    topic = "onex.cmd.omniintelligence.claude-hook-event.v1"
    producer = "src/omniclaude/hooks/topics.py"
    consumer = "src/omniintelligence/nodes/node_claude_hook_event_effect/contract.yaml"
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        f'---\nversion: "1"\nboundaries:\n  - topic_name: "{topic}"\n'
        f"    producer_repo: omniclaude\n    consumer_repo: omniintelligence\n"
        f'    producer_file: "{producer}"\n    consumer_file: "{consumer}"\n'
        '    topic_pattern: "claude-hook-event\\\\.v1"\n'
        '    event_schema: "ModelClaudeCodeHookEvent"\n',
        encoding="utf-8",
    )
    repos = tmp_path / "repos"
    (repos / "omniintelligence" / Path(consumer).parent).mkdir(parents=True)
    (repos / "omniintelligence" / consumer).write_text(
        f"subscribe_topics:\n  - {topic}\n", encoding="utf-8"
    )
    (repos / "omniclaude" / Path(producer).parent).mkdir(parents=True)
    argv = ["--repos-root", str(repos), "--manifest", str(manifest)]

    (repos / "omniclaude" / producer).write_text(
        f'HOOK = "{topic}"\n', encoding="utf-8"
    )
    assert main(argv) == 0
    capsys.readouterr()

    (repos / "omniclaude" / producer).write_text("UNRELATED = 1\n", encoding="utf-8")
    assert main(argv) != 0
    assert (
        f"topic not found in producer: omniclaude/{producer}" in capsys.readouterr().out
    )


def test_inputs_job_name_and_required_context_are_unchanged() -> None:
    job = _job()
    step = next(s for s in job["steps"] if ACTION in s.get("uses", ""))

    assert job["name"] == CONTEXT
    assert step["with"] == {
        "checks": "boundary-parity",
        "warn-only": "false",
        "repos": "omniclaude,omnidash,omniintelligence,omnibase_infra,omnibase_core,omnimemory,omnimarket,onex_change_control",
    }
    entries = yaml.safe_load(REQUIRED_CHECKS.read_text(encoding="utf-8"))
    required = [e for e in _entries(entries) if e.get("name") == CONTEXT]
    assert [e["job_path"] for e in required] == [[JOB_ID]]


def _entries(doc: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(doc, dict):
        if "name" in doc and "job_path" in doc:
            found.append(doc)
        for value in doc.values():
            found.extend(_entries(value))
    elif isinstance(doc, list):
        for value in doc:
            found.extend(_entries(value))
    return found
