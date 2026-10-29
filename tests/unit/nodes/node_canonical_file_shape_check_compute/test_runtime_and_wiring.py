# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Runtime, hook wiring and golden report of the canonical-file-shape node (OMN-21515)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_output import (
    ModelValidationReportWriteOutput,
)
from omnibase_core.models.validation.model_canonical_file_shape_check_input import (
    ModelCanonicalFileShapeCheckInput,
)
from omnibase_core.models.validation.model_canonical_file_shape_facts import (
    ModelCanonicalFileShapeFacts,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.handler import (
    NodeCanonicalFileShapeCheckCompute,
)
from omnibase_core.nodes.node_canonical_file_shape_check_compute.runtime_canonical_file_shape_check import (
    main,
    run_check,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.validation.validator_canonical_file_shape import (
    ValidatorCanonicalFileShape,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    RULES,
    GitRepo,
    git,
    init_repo,
    issues,
    rules_hit,
    stage,
    write,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES = REPO_ROOT / "tests/fixtures/validation/canonical_file_shape"
RUNTIME_MODULE = (
    "omnibase_core.nodes.node_canonical_file_shape_check_compute"
    ".runtime_canonical_file_shape_check"
)
CODE5 = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n"
CODE7 = CODE5 + "f = 6\ng = 7\n"
LIFECYCLE = RULES.parameters.lifecycle_path


def _hooks() -> dict[str, dict[str, Any]]:
    manifest = yaml.safe_load((REPO_ROOT / ".pre-commit-hooks.yaml").read_text())
    return {hook["id"]: hook for hook in manifest}


def test_hook_id_canonical_file_shape_is_unchanged_and_runs_the_new_node() -> None:
    """AC1: the hook id downstream consumers name is the same; its entry is the node runtime."""
    hook = _hooks()["canonical-file-shape"]
    assert hook["entry"] == f"python -m {RUNTIME_MODULE}"
    assert hook["pass_filenames"] is False
    assert hook["always_run"] is True


def test_check_node_home_hook_id_is_unchanged_and_runs_only_the_node_home_rule() -> (
    None
):
    hook = _hooks()["check-node-home"]
    assert hook["entry"] == f"python -m {RUNTIME_MODULE} --rules node-home"


def test_the_node_contract_names_the_node_and_the_report_model() -> None:
    contract = yaml.safe_load(
        (
            REPO_ROOT
            / "src/omnibase_core/nodes/node_canonical_file_shape_check_compute/contract.yaml"
        ).read_text()
    )
    assert contract["name"] == "node_canonical_file_shape_check_compute"
    assert contract["node_type"] == "compute"
    assert contract["output_model"].endswith("ModelValidationReport")
    assert contract["handler_routing"]["default_handler"] == (
        "handler:NodeCanonicalFileShapeCheckCompute"
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    write(tmp_path, "src/pkg/models/model_a.py", CODE5)
    write(tmp_path, "docs/ledger.md", "row 1\n")
    return init_repo(tmp_path)


def _run(repo: Path, *argv: str) -> int:
    return main(
        ["--repo-root", str(repo), *argv],
        env=scrub_git_location_env(),
    )


def test_a_new_script_is_refused_through_the_hook_entry_and_a_clean_change_passes(
    repo: Path,
) -> None:
    """AC2: the canary commit that adds scripts/x.py is refused."""
    write(repo, "scripts/x.py", "print('x')\n")
    stage(repo)
    assert rules_hit(repo) == ["noncanonical-file"]
    assert _run(repo) == 1
    git(repo, "rm", "-q", "--cached", "scripts/x.py")
    (repo / "scripts/x.py").unlink()
    write(repo, "src/pkg/models/model_b.py", "b = 1\n")
    stage(repo)
    assert _run(repo) == 0


def test_no_code_repository_end_to_end(repo: Path) -> None:
    """AC3: no-code refuses src/.../x.py and admits a ledger-row Markdown append."""
    write(repo, LIFECYCLE, "state: no-code\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "declare no-code")
    write(repo, "docs/ledger.md", "row 1\nrow 2\n")
    stage(repo)
    assert rules_hit(repo) == []
    write(repo, "src/pkg/models/x.py", "x = 1\n")
    stage(repo)
    assert rules_hit(repo) == ["lifecycle-no-code"]
    assert _run(repo) == 1


def test_fix_only_repository_end_to_end(repo: Path) -> None:
    """AC4: new file refused; a two-line fix refused without the trailer, admitted with it."""
    write(repo, LIFECYCLE, "state: fix-only\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "declare fix-only")
    write(repo, "src/pkg/models/new.py", "n = 1\n")
    stage(repo)
    assert rules_hit(repo, commit_message="fix\n") == ["lifecycle-fix-only-new-file"]
    git(repo, "rm", "-q", "-f", "src/pkg/models/new.py")
    write(repo, "src/pkg/models/model_a.py", CODE7)
    stage(repo)
    assert rules_hit(repo, commit_message="fix a bug\n") == [
        "lifecycle-fix-only-growth"
    ]
    assert (
        rules_hit(repo, commit_message="fix a bug\n\nrelease=2026-10-29T01:00:00Z\n")
        == []
    )
    assert (
        rules_hit(repo) == []
    )  # no message known on the index: deferred to commit-msg


def test_fix_only_trailer_is_read_from_the_commit_range(repo: Path) -> None:
    write(repo, LIFECYCLE, "state: fix-only\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "declare fix-only")
    write(repo, "src/pkg/models/model_a.py", CODE7)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fix\n\nrelease=2026-10-29T01:00:00Z")
    assert rules_hit(repo, base="HEAD~1", head="HEAD") == []
    git(repo, "commit", "-q", "--amend", "-m", "fix without a stamp")
    assert rules_hit(repo, base="HEAD~1", head="HEAD") == ["lifecycle-fix-only-growth"]


def test_commit_message_file_flag_carries_the_trailer(
    repo: Path, tmp_path: Path
) -> None:
    write(repo, LIFECYCLE, "state: fix-only\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "declare fix-only")
    write(repo, "src/pkg/models/model_a.py", CODE7)
    stage(repo)
    message = tmp_path.parent / f"{tmp_path.name}-msg.txt"
    message.write_text("fix\n", encoding="utf-8")
    assert _run(repo, "--commit-message-file", str(message)) == 1
    message.write_text("fix\n\nrelease=2026-10-29T01:00:00Z\n", encoding="utf-8")
    assert _run(repo, "--commit-message-file", str(message)) == 0


def test_handler_not_bound_by_a_contract_is_refused_and_a_bound_one_is_not(
    repo: Path,
) -> None:
    """K2: handlers/ stays canonical for a bound handler."""
    write(repo, "src/pkg/handlers/handler_y.py", "class HandlerY:\n    pass\n")
    stage(repo)
    assert rules_hit(repo) == ["handler_outside_node"]
    write(
        repo,
        "src/pkg/nodes/node_y/contract.yaml",
        "name: node_y\nhandler_routing:\n  default_handler: pkg.handlers.handler_y:HandlerY\n",
    )
    stage(repo)
    assert rules_hit(repo) == []


def test_class_named_handler_in_a_model_file_is_refused(repo: Path) -> None:
    write(repo, "src/pkg/models/model_h.py", "class HandlerThing:\n    pass\n")
    stage(repo)
    assert rules_hit(repo) == ["handler_outside_node"]


def test_an_argparse_main_outside_a_node_runtime_is_refused(repo: Path) -> None:
    body = "import argparse\n\n\ndef main() -> int:\n    argparse.ArgumentParser()\n    return 0\n"
    write(repo, "src/pkg/models/model_cli.py", body)
    stage(repo)
    assert rules_hit(repo) == ["cli_entry_outside_node"]
    git(repo, "rm", "-q", "-f", "src/pkg/models/model_cli.py")
    write(repo, "src/pkg/nodes/node_y/contract.yaml", "name: node_y\n")
    write(repo, "src/pkg/nodes/node_y/runtime_y.py", body)
    stage(repo)
    assert rules_hit(repo) == []


def test_a_console_script_to_a_non_runtime_module_is_refused(repo: Path) -> None:
    write(repo, "src/pkg/models/model_tool.py", "def main() -> int:\n    return 0\n")
    write(
        repo,
        "pyproject.toml",
        '[project.scripts]\ntool = "pkg.models.model_tool:main"\n',
    )
    stage(repo)
    assert rules_hit(repo) == ["cli_entry_outside_node"]


@pytest.mark.parametrize(
    ("key", "path", "text", "rule"),
    [
        (
            "handler_class_pattern",
            "src/pkg/models/model_h.py",
            "class HandlerThing:\n    pass\n",
            "handler_outside_node",
        ),
        (
            "argparse_pattern",
            "src/pkg/models/model_cli.py",
            "import argparse\nargparse.ArgumentParser()\n\n\ndef main() -> int:\n    return 0\n",
            "cli_entry_outside_node",
        ),
        (
            "main_pattern",
            "src/pkg/models/model_cli.py",
            "import argparse\nargparse.ArgumentParser()\n\n\ndef main() -> int:\n    return 0\n",
            "cli_entry_outside_node",
        ),
    ],
)
def test_mutating_a_reader_parameter_changes_the_verdict(
    repo: Path, key: str, path: str, text: str, rule: str
) -> None:
    write(repo, path, text)
    stage(repo)
    assert rules_hit(repo) == [rule]
    mutated = RULES.model_copy(
        update={
            "parameters": RULES.parameters.model_copy(update={key: "zz-never-matches"})
        }
    )
    assert [i.code for i in issues(repo, rules=mutated)] == []


class _SpyWriter:
    def __init__(self) -> None:
        self.requests: list[ModelValidationReportWriteInput] = []

    def handle(
        self, request: ModelValidationReportWriteInput
    ) -> ModelValidationReportWriteOutput:
        self.requests.append(request)
        return ModelValidationReportWriteOutput(
            report_path=request.report_path,
            bytes_written=0,
            events_path="",
            events_written=0,
        )


class _SpyContainer:
    """Records what the runtime resolves from its container."""

    def __init__(self, writer: _SpyWriter) -> None:
        self.writer = writer
        self.resolved: list[type] = []

    def get_service(self, protocol_type: type, service_name: str | None = None) -> Any:
        self.resolved.append(protocol_type)
        return self.writer


def test_the_runtime_resolves_the_report_writer_from_the_container(
    repo: Path, tmp_path: Path
) -> None:
    write(repo, "scripts/x.py", "print('x')\n")
    stage(repo)
    writer = _SpyWriter()
    container = _SpyContainer(writer)
    report = run_check(
        cast(ModelONEXContainer, container),
        GitRepo(
            root=repo,
            env=scrub_git_location_env(),
            cat_file_timeout_s=RULES.parameters.cat_file_timeout_s,
        ),
        None,
        None,
        None,
        str(tmp_path / "report.json"),
    )
    assert container.resolved == [NodeValidationReportWriteEffect]
    assert [r.report for r in writer.requests] == [report]
    assert [f.rule_id for f in report.findings] == ["noncanonical-file"]


def test_no_report_is_written_and_no_writer_is_resolved_without_report_json(
    repo: Path,
) -> None:
    container = _SpyContainer(_SpyWriter())
    run_check(
        cast(ModelONEXContainer, container),
        GitRepo(
            root=repo,
            env=scrub_git_location_env(),
            cat_file_timeout_s=RULES.parameters.cat_file_timeout_s,
        ),
        None,
        None,
        None,
        None,
    )
    assert container.resolved == []


def _normalised(report_json: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(report_json)
    data["report_id"] = "<run-id>"
    data["provenance"]["generated_at"] = "<timestamp>"
    return data


def test_the_report_equals_the_committed_golden_report() -> None:
    """The in-memory run's report equals the golden report after normalising run id and timestamp.

    The broker overlay half of this proof needs the validator-runtime overlay pair
    that the report-writer publish task lands; until then only the in-memory half
    runs (see the pull request body).
    """
    facts = ModelCanonicalFileShapeFacts.model_validate(
        {
            "head_tree": {
                "files": [
                    "scripts/x.py",
                    "src/pkg/handlers/handler_y.py",
                    "src/pkg/models/model_ok.py",
                ]
            }
        }
    )
    report = NodeCanonicalFileShapeCheckCompute().handle(
        ModelCanonicalFileShapeCheckInput(
            facts=facts, contract=ValidatorCanonicalFileShape().contract
        )
    )
    golden = json.loads(
        (FIXTURES / "golden_check_output.json").read_text(encoding="utf-8")
    )
    assert _normalised(report.model_dump_json()) == golden
