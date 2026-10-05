# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Direct rule checks supplementing the permanent parity corpus."""

from __future__ import annotations

import pytest
import yaml

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.precommit_interpreter_check.model_precommit_interpreter_check_input import (
    ModelPrecommitInterpreterCheckInput,
)
from omnibase_core.nodes.node_precommit_interpreter_check_compute.handler import (
    NodePrecommitInterpreterCheckCompute,
)
from omnibase_core.nodes.node_precommit_interpreter_check_compute.matcher_precommit_interpreter import (
    scan_entry,
    scan_script,
)

pytestmark = pytest.mark.unit


def test_parity_entry_message_and_command_list() -> None:
    entry = "bash -c 'python a.py && python3 b.py'"
    assert scan_entry("hook", entry) == [
        f"hook: entry invokes bare `{word}` -- use `uv run python` "
        f"(macOS has no bare `python`; entry={entry!r})"
        for word in ("python", "python3")
    ]


def test_parity_shell_message_and_python3_tolerance() -> None:
    source = "python3 x.py\npython x.py\n"
    assert scan_script("hook.sh", source) == [
        (
            2,
            "hook.sh:2: invokes bare `python` -- use `uv run python` or a guarded `python3` ('python x.py')",
        )
    ]


def test_parity_suppression_requires_comment_and_reason() -> None:
    marker = "precommit-" + "interp-ok"
    assert not scan_entry("hook", "python x.py # " + marker + ": reviewed")
    assert scan_entry("hook", "python x.py # " + marker + ":")
    assert scan_entry("hook", "python x.py " + marker)
    assert not scan_script("hook.sh", "python x.py # " + marker + ": reviewed")
    assert scan_script("hook.sh", "python x.py # " + marker + ":")


def test_parity_unparseable_entry_severity() -> None:
    hooks = [{"id": "hook", "entry": "python 'x.py"}] + [
        {"id": f"pad-{index}", "entry": "uv run python x.py"} for index in range(9)
    ]
    report = NodePrecommitInterpreterCheckCompute().handle(
        ModelPrecommitInterpreterCheckInput(
            config=ModelSourceFile(
                path="config.yaml", source=yaml.safe_dump({"repos": [{"hooks": hooks}]})
            )
        )
    )
    assert report.overall_status == "ERROR"
    assert len(report.findings) == 1
    assert (
        report.findings[0].message
        == 'hook: entry is not shell-parsable: "python \'x.py"'
    )
    assert report.findings[0].rule_id == "entry-interpreter"


def test_parity_floor_hides_other_violations() -> None:
    report = NodePrecommitInterpreterCheckCompute().handle(
        ModelPrecommitInterpreterCheckInput(
            config=ModelSourceFile(
                path="config.yaml",
                source="repos:\n  - hooks:\n      - id: hook\n        entry: python x.py\n",
            ),
            scripts=[ModelSourceFile(path="unreferenced.sh", source="python x.py")],
        )
    )
    assert len(report.findings) == 1
    assert report.findings[0].rule_id == "non-vacuity"
    assert report.findings[0].message == (
        "ERROR: interpreter gate scanned only 1 local hooks -- refusing to report a vacuous pass"
    )


@pytest.mark.parametrize(
    "source", ["repos: [", "", "[]", "repos: invalid", "repos: [invalid]"]
)
def test_parity_invalid_yaml_is_an_error(source: str) -> None:
    report = NodePrecommitInterpreterCheckCompute().handle(
        ModelPrecommitInterpreterCheckInput(
            config=ModelSourceFile(path="config.yaml", source=source)
        )
    )
    assert report.overall_status == "ERROR"
    assert report.findings[0].rule_id == "invalid-config"
