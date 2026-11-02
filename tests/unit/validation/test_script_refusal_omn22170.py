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

import pytest

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
        "scripts/zz_new.py",
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
    assert file_named in findings[0].location
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
