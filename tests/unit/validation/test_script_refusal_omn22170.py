# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Script refusals of the canonical-file-shape node, one fixture per script kind (OMN-22170).

Every case runs through the node handler (facts and contract in, report out), the
way the CI job and the pre-commit hook run it. ``script_fixture_matrix`` is the
measured table of OMN-22170 AC1: each script kind is refused or admitted, and a
refusal names the file and the node it should become. ``script_refusal`` cases are
the AC2 falsifier: they fail on the node before OMN-22170 (no node named in the
text, launchd and cron units admitted) and pass on the node after it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.validation.model_canonical_file_shape_check_input import (
    ModelCanonicalFileShapeCheckInput,
)
from omnibase_core.models.validation.model_canonical_file_shape_facts import (
    ModelCanonicalFileShapeFacts,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.handler import (
    NodeCanonicalFileShapeCheckCompute,
)
from omnibase_core.validation.validator_canonical_file_shape import (
    ValidatorCanonicalFileShape,
)

pytestmark = pytest.mark.unit

REPO_CONFIGS = Path(__file__).parent / "script_matrix_omn22170" / "repo_configs.yaml"

CONTRACT = ValidatorCanonicalFileShape().contract
PLIST_RUNS_SCRIPT = (
    '<plist version="1.0"><dict><key>ProgramArguments</key><array>'
    "<string>/bin/sh</string><string>scripts/job.sh</string></array></dict></plist>\n"
)
CRON_RUNS_SCRIPT = "*/5 * * * * /bin/sh scripts/job.sh\n"
BASE_LINES = "a = 1\nb = 2\nc = 3\n"


def _facts(
    files: list[str],
    changes: list[dict[str, object]] | None = None,
    baseline: str | None = None,
    base_baseline: str | None = None,
) -> ModelCanonicalFileShapeFacts:
    return ModelCanonicalFileShapeFacts.model_validate(
        {
            "head_tree": {"files": files},
            "has_base": True,
            "changes": changes or [],
            "head_baseline_text": baseline,
            "base_baseline_text": base_baseline,
        }
    )


def _added(path: str, text: str) -> dict[str, object]:
    return {"status": "A", "path": path, "new_text": text}


def _findings(facts: ModelCanonicalFileShapeFacts) -> list[ModelValidationFindingEmbed]:
    report = NodeCanonicalFileShapeCheckCompute().handle(
        ModelCanonicalFileShapeCheckInput(contract=CONTRACT, facts=facts)
    )
    return list(report.findings)


# fixture name -> (facts, expected rule id or None when admitted, file named, node named)
MATRIX: dict[str, tuple[ModelCanonicalFileShapeFacts, str | None, str, str]] = {
    "new_scripts_py": (
        _facts(["scripts/zz_new.py"]),
        "noncanonical-file",
        "scripts/zz_new.py",
        "node_zz_new",
    ),
    "new_shell_anywhere": (
        _facts(["tools/zz-new.sh"]),
        "noncanonical-file",
        "tools/zz-new.sh",
        "node_zz_new",
    ),
    "new_plugin_skill_script": (
        _facts(["plugins/p/skills/s/scripts/zz_new.py"]),
        "noncanonical-file",
        "plugins/p/skills/s/scripts/zz_new.py",
        "node_zz_new",
    ),
    "new_launchd_unit_running_a_script": (
        _facts(
            ["launchd/ai.zz.job.plist"],
            [_added("launchd/ai.zz.job.plist", PLIST_RUNS_SCRIPT)],
        ),
        "script-unit-new",
        "launchd/ai.zz.job.plist",
        "node_ai_zz_job",
    ),
    "new_cron_unit_running_a_script": (
        _facts(["cron/zz_job.cron"], [_added("cron/zz_job.cron", CRON_RUNS_SCRIPT)]),
        "script-unit-new",
        "cron/zz_job.cron",
        "node_zz_job",
    ),
    "baselined_script_grows": (
        _facts(
            ["scripts/old.py"],
            [
                {
                    "status": "M",
                    "path": "scripts/old.py",
                    "old_text": BASE_LINES,
                    "new_text": BASE_LINES + "d = 4\n",
                }
            ],
            baseline="scripts/old.py\n",
            base_baseline="scripts/old.py\n",
        ),
        "baselined-file-growth",
        "scripts/old.py",
        "node_old",
    ),
    "baseline_gains_a_line": (
        _facts(
            ["scripts/old.py", "scripts/zz_new.py"],
            baseline="scripts/old.py\nscripts/zz_new.py\n",
            base_baseline="scripts/old.py\n",
        ),
        "baseline-growth",
        ".onex_ratchets/canonical_file_shape_baseline.txt",
        "node_zz_new",
    ),
    "baselined_skill_script_grows": (
        _facts(
            ["plugins/p/skills/s/scripts/old_skill.py"],
            [
                {
                    "status": "M",
                    "path": "plugins/p/skills/s/scripts/old_skill.py",
                    "old_text": BASE_LINES,
                    "new_text": BASE_LINES + "d = 4\n",
                }
            ],
            baseline="plugins/p/skills/s/scripts/old_skill.py\n",
            base_baseline="plugins/p/skills/s/scripts/old_skill.py\n",
        ),
        "baselined-file-growth",
        "plugins/p/skills/s/scripts/old_skill.py",
        "node_old_skill",
    ),
    "control_file_in_a_canonical_location": (
        _facts(
            ["src/pkg/models/model_zz.py"],
            [_added("src/pkg/models/model_zz.py", "x = 1\n")],
        ),
        None,
        "",
        "",
    ),
    "control_launchd_unit_that_runs_a_node": (
        _facts(
            ["launchd/ai.zz.job.plist"],
            [
                _added(
                    "launchd/ai.zz.job.plist",
                    "<string>onex</string><string>node</string><string>node_job</string>\n",
                )
            ],
        ),
        None,
        "",
        "",
    ),
    "control_baselined_script_that_shrinks": (
        _facts(
            ["scripts/old.py"],
            [
                {
                    "status": "M",
                    "path": "scripts/old.py",
                    "old_text": BASE_LINES,
                    "new_text": "a = 1\n",
                }
            ],
            baseline="scripts/old.py\n",
            base_baseline="scripts/old.py\n",
        ),
        None,
        "",
        "",
    ),
}


@pytest.mark.parametrize("name", sorted(MATRIX))
def test_script_fixture_matrix(name: str) -> None:
    facts, rule, file_named, node_named = MATRIX[name]
    findings = _findings(facts)
    if rule is None:
        assert findings == []
        return
    assert [f.rule_id for f in findings] == [rule]
    location = findings[0].location
    assert location is not None
    assert file_named in location
    assert file_named in findings[0].message or rule == "baseline-growth"
    assert node_named in findings[0].message


@pytest.mark.parametrize(
    "name",
    [
        "new_scripts_py",
        "new_shell_anywhere",
        "new_plugin_skill_script",
        "new_launchd_unit_running_a_script",
        "new_cron_unit_running_a_script",
        "baselined_script_grows",
        "baselined_skill_script_grows",
    ],
)
def test_script_refusal_names_the_file_and_the_node_it_becomes(name: str) -> None:
    facts, _, file_named, node_named = MATRIX[name]
    message = _findings(facts)[0].message
    assert message.startswith(f"{file_named}: ")
    assert f"node {node_named}" in message


def test_script_refusal_of_a_unit_in_a_test_or_docs_tree_is_not_made() -> None:
    facts = _facts(
        ["tests/fixtures/launchd/ai.zz.plist", "docs/cron/zz.cron"],
        [
            _added("tests/fixtures/launchd/ai.zz.plist", PLIST_RUNS_SCRIPT),
            _added("docs/cron/zz.cron", CRON_RUNS_SCRIPT),
        ],
    )
    assert _findings(facts) == []


def test_script_refusal_of_an_existing_unit_edit_is_not_a_new_unit() -> None:
    facts = _facts(
        ["launchd/ai.zz.job.plist"],
        [
            {
                "status": "M",
                "path": "launchd/ai.zz.job.plist",
                "old_text": PLIST_RUNS_SCRIPT,
                "new_text": PLIST_RUNS_SCRIPT + "\n",
            }
        ],
    )
    assert _findings(facts) == []


def test_script_refusal_of_an_added_baseline_line_names_the_file_and_the_node() -> None:
    facts, _, _, _ = MATRIX["baseline_gains_a_line"]
    message = _findings(facts)[0].message
    assert "'scripts/zz_new.py'" in message
    assert "node node_zz_new" in message


def test_script_refusal_of_an_added_burndown_line_names_the_file_and_the_node() -> None:
    facts = ModelCanonicalFileShapeFacts.model_validate(
        {
            "head_tree": {"files": ["scripts/old.py", "scripts/zz_new.py"]},
            "has_base": True,
            "changes": [],
            "head_burndown_text": "# Burn-down ticket: OMN-1\nscripts/old.py\nscripts/zz_new.py\n",
            "base_burndown_text": "# Burn-down ticket: OMN-1\nscripts/old.py\n",
        }
    )
    [finding] = _findings(facts)
    assert finding.rule_id == "baseline-growth"
    assert "'scripts/zz_new.py'" in finding.message
    assert "node node_zz_new" in finding.message


def test_script_refusal_of_growth_when_the_head_baseline_drops_the_entry() -> None:
    """Dropping the entry in the growing change does not admit the growth: the file is refused as new."""
    facts = _facts(
        ["scripts/old.py"],
        [
            {
                "status": "M",
                "path": "scripts/old.py",
                "old_text": BASE_LINES,
                "new_text": BASE_LINES + "d = 4\n",
            }
        ],
        baseline="",
        base_baseline="scripts/old.py\n",
    )
    findings = _findings(facts)
    assert [f.rule_id for f in findings] == ["noncanonical-file"]
    assert findings[0].message.startswith("scripts/old.py: ")
    assert "node node_old" in findings[0].message


# AC1: the measured table. Each repository runs the node of the omnibase_core revision its own CI
# file pins, so what a repository refuses today is what that pinned revision refuses. The rows of
# repo_configs.yaml were measured by running each fixture as a real commit through the pinned
# module with the flags the repository's CI file passes; the ``this_change`` pin is the node in
# this tree and is compared here with a live run of every fixture.


def _table() -> dict[str, object]:
    loaded = yaml.safe_load(REPO_CONFIGS.read_text())
    assert isinstance(loaded, dict)
    return loaded


def _live_outcome(name: str) -> tuple[bool, bool]:
    findings = _findings(MATRIX[name][0])
    return bool(findings), bool(findings) and all(
        "node node_" in f.message for f in findings
    )


def _pin_rows(table: dict[str, object]) -> dict[str, dict[str, list[str]]]:
    pins = table["pins"]
    assert isinstance(pins, dict)
    return pins


def _repo_rows(table: dict[str, object]) -> list[dict[str, str | None]]:
    rows = table["repositories"]
    assert isinstance(rows, list)
    return rows


def render_script_fixture_matrix(table: dict[str, object]) -> str:
    """The markdown table of the pull request body: fixture rows, repository columns."""
    pins = _pin_rows(table)
    repos = _repo_rows(table)
    measured = [r for r in repos if r["config_read"] == "yes"]
    header = "| fixture | " + " | ".join(str(r["name"]) for r in measured) + " |"
    lines = [header, "|" + " -- |" * (len(measured) + 1)]
    for name in sorted(MATRIX):
        cells = []
        for repo in measured:
            refused = name in pins[str(repo["pin"])]["refused"]
            cells.append("refused" if refused else "admitted")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lacking = [str(r["name"]) for r in repos if r["required_ci_runs_check"] == "no"]
    unread = [str(r["name"]) for r in repos if r["required_ci_runs_check"] == "unread"]
    lines.append("")
    lines.append("required CI does not run the check: " + ", ".join(lacking))
    lines.append("configuration not readable on the lab host: " + ", ".join(unread))
    return "\n".join(lines)


def test_script_fixture_matrix_table_current_node_row_matches_the_live_node() -> None:
    pin = _pin_rows(_table())["this_change"]
    for name in sorted(MATRIX):
        refused, names_node = _live_outcome(name)
        assert (name in pin["refused"]) is refused, name
        assert (name in pin["names_node"]) is names_node, name


def test_script_fixture_matrix_table_pins_only_name_known_fixtures_and_admit_the_controls() -> (
    None
):
    for pin_id, pin in _pin_rows(_table()).items():
        assert set(pin["refused"]) <= set(MATRIX), pin_id
        assert set(pin["names_node"]) <= set(pin["refused"]), pin_id
        assert not {n for n in pin["refused"] if n.startswith("control_")}, pin_id


def test_script_fixture_matrix_table_every_measured_repository_maps_to_a_recorded_pin() -> (
    None
):
    table = _table()
    pins = _pin_rows(table)
    for repo in _repo_rows(table):
        if repo["config_read"] == "yes":
            assert repo["pin"] in pins, repo["name"]
            assert repo["base_sha"], repo["name"]
        else:
            assert repo["pin"] is None, repo["name"]
            assert repo["required_ci_runs_check"] == "unread", repo["name"]


def test_script_fixture_matrix_table_names_the_repositories_whose_required_ci_lacks_the_check() -> (
    None
):
    repos = _repo_rows(_table())
    lacking = sorted(
        str(r["name"]) for r in repos if r["required_ci_runs_check"] == "no"
    )
    assert lacking == ["omnibase_internal", "omniclaude-internal"]


def test_script_fixture_matrix_table_shows_a_unit_running_a_script_is_admitted_outside_core() -> (
    None
):
    table = _table()
    pins = _pin_rows(table)
    for repo in _repo_rows(table):
        if repo["config_read"] != "yes" or repo["name"] == "omnibase_core":
            continue
        assert (
            "new_launchd_unit_running_a_script" not in pins[str(repo["pin"])]["refused"]
        )


def test_script_fixture_matrix_table_renders(
    capsys: pytest.CaptureFixture[str],
) -> None:
    text = render_script_fixture_matrix(_table())
    print(text)
    assert "| new_cron_unit_running_a_script |" in text
    assert "required CI does not run the check: " in text
    assert capsys.readouterr().out.strip() == text.strip()
