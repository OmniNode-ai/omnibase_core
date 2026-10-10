# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Replay of the decisions of the OCC arch-handler-contract-compliance validator (OMN-20074).

``tests/fixtures/occ_arch_handler_compliance/manifest.yaml`` lists cases; each case
names the fixture trees that make up a repository, the optional allowlist and flags,
and carries the stdout and exit code that onex_change_control produced for that
repository (``expected/<id>.stdout.txt``). The trees hold verbatim files of
omniintelligence nodes plus constructed nodes, one or more per rule class. The
handler must reproduce stdout byte for byte and the exit code, so the consumer that
changes only the module it runs sees no difference in what is flagged.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.enums.governance.enum_compliance_verdict import (
    EnumComplianceVerdict,
)
from omnibase_core.enums.governance.enum_compliance_violation import (
    EnumComplianceViolation,
)
from omnibase_core.enums.governance.enum_reachability import EnumReachability
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_arch_handler_contract_compliance import (
    HandlerArchHandlerContractCompliance,
    main,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_compliance_node_source import (
    ModelComplianceNodeSource,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_handler_contract_compliance_input import (
    ModelHandlerContractComplianceInput,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_handler_contract_compliance_report import (
    ModelHandlerContractComplianceReport,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "occ_arch_handler_compliance"
)

_CONTRACT_ROUTED = """\
name: node_x_compute
node_type: COMPUTE_GENERIC
handler_routing:
  handlers:
    - handler:
        name: HandlerX
        module: pkg.nodes.node_x_compute.handlers.handler_x
      operation: run
"""
_CLEAN_HANDLER = (
    "class HandlerX:\n    def handle(self, request):\n        return request\n"
)


class _Case(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    trees: list[str]
    allowlist: str | None = None
    flags: list[str] = []
    expected_exit: int


def _cases() -> list[_Case]:
    raw = yaml.safe_load((FIXTURES / "manifest.yaml").read_text(encoding="utf-8"))
    return [_Case(**item) for item in raw]


def _materialise(case: _Case, root: Path) -> list[str]:
    """Write the case's trees into ``root`` and return the validator arguments."""
    for tree in case.trees:
        base = FIXTURES / "trees" / tree
        for source in base.rglob("*.txt"):
            target = root / source.relative_to(base).with_suffix("")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, target)
    args = ["--repo-root", "."]
    if case.allowlist == "absent":
        args += ["--allowlist-path", "allowlist.yaml"]
    elif case.allowlist is not None:
        shutil.copy(
            FIXTURES / "allowlists" / f"{case.allowlist}.yaml.txt",
            root / "allowlist.yaml",
        )
        args += ["--allowlist-path", "allowlist.yaml"]
    return args + case.flags


def _expected(case: _Case) -> str:
    return (FIXTURES / "expected" / f"{case.id}.stdout.txt").read_text(encoding="utf-8")


def _node(
    contract: str | None,
    handlers: dict[str, str],
    *,
    node_py: str | None = None,
    node_dir: str = "src/pkg/nodes/node_x_compute",
) -> ModelComplianceNodeSource:
    return ModelComplianceNodeSource(
        node_dir=node_dir,
        contract_yaml=contract,
        node_py=node_py,
        handlers=[
            ModelSourceFile(path=f"{node_dir}/handlers/{name}", source=source)
            for name, source in handlers.items()
        ],
    )


def _handle(
    nodes: list[ModelComplianceNodeSource], allowlisted: list[str] | None = None
) -> ModelHandlerContractComplianceReport:
    return HandlerArchHandlerContractCompliance().handle(
        ModelHandlerContractComplianceInput(
            repo="pkg", nodes=nodes, allowlisted_paths=allowlisted or []
        )
    )


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c.id)
def test_replays_occ_output_and_exit_code(
    case: _Case,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = _materialise(case, tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(args)
    # fixture files end with exactly one newline (end-of-file hook); compare likewise
    assert capsys.readouterr().out.rstrip("\n") + "\n" == _expected(case)
    assert code == case.expected_exit


def test_manifest_covers_pass_and_fail_for_every_rule_class() -> None:
    by_id = {case.id: case for case in _cases()}
    # one pass and one fail per rule class, plus the positive control
    assert by_id["pass-compliant"].expected_exit == 0
    for failing in (
        "fail-hardcoded-topic",
        "fail-undeclared-transport",
        "fail-missing-routing",
        "fail-logic-in-node",
        "omniintelligence-subset-positive-control",
    ):
        assert by_id[failing].expected_exit == 1, failing
    assert "hardcoded topic" in _expected(by_id["fail-hardcoded-topic"])
    assert "undeclared transport" in _expected(by_id["fail-undeclared-transport"])
    assert "not registered in contract handler_routing" in _expected(
        by_id["fail-missing-routing"]
    )
    assert "node.py has custom methods" in _expected(by_id["fail-logic-in-node"])
    assert "node_planted_control_compute" in _expected(
        by_id["omniintelligence-subset-positive-control"]
    )


def test_positive_control_is_flagged_beside_real_files_that_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    by_id = {case.id: case for case in _cases()}
    clean = by_id["omniintelligence-subset-new-entries-listed"]
    planted = by_id["omniintelligence-subset-positive-control"]
    monkeypatch.chdir(tmp_path)
    assert main(_materialise(clean, tmp_path)) == 0
    capsys.readouterr()
    assert main(_materialise(planted, tmp_path)) == 1
    out = capsys.readouterr().out
    assert "hardcoded topic 'onex.evt.lab.positive-control.v1' not in contract" in out
    assert "undeclared transport DATABASE used in handler" in out


def test_invoked_as_module_with_the_consumer_flags(tmp_path: Path) -> None:
    by_id = {case.id: case for case in _cases()}
    for case_id, exit_code in (
        ("omniintelligence-subset-new-entries-listed", 0),
        ("omniintelligence-subset", 1),
    ):
        case = by_id[case_id]
        root = tmp_path / case_id
        root.mkdir()
        args = _materialise(case, root)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "omnibase_core.handlers.handler_arch_handler_contract_compliance",
                *args,
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == exit_code, result.stdout
        assert result.stdout.rstrip("\n") + "\n" == _expected(case)


def test_json_output_matches_occ_result_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    case = {c.id: c for c in _cases()}["reachability-json"]
    monkeypatch.chdir(tmp_path)
    main(_materialise(case, tmp_path))
    out = capsys.readouterr().out
    records = json.loads(out[: out.index("\n=== Handler")])
    by_name = {Path(r["handler_path"]).name: r for r in records}
    assert by_name["handler_in_tests.py"]["reachability"] == "test_harness"
    assert by_name["test_handler_named.py"]["reachability"] == "test_harness"
    assert by_name["handler_reach.py"]["reachability"] == "live"
    assert by_name["handler_dead.py"]["verdict"] == "missing_contract"
    assert by_name["handler_dead.py"]["reachability"] == "live"
    assert by_name["handler_in_tests.py"]["verdict"] == "hybrid"
    assert by_name["handler_in_tests.py"]["handler_in_routing"] is False


def test_missing_repo_root_argument_exits_two() -> None:
    with pytest.raises(SystemExit) as raised:
        main([])
    assert raised.value.code == 2


class TestHandlerDecisions:
    def test_clean_routed_handler_is_compliant(self) -> None:
        report = _handle([_node(_CONTRACT_ROUTED, {"handler_x.py": _CLEAN_HANDLER})])
        [result] = report.results
        assert result.verdict == EnumComplianceVerdict.COMPLIANT
        assert result.violations == []
        assert result.handler_in_routing is True
        assert report.new_violations == []

    def test_each_rule_class_raises_its_violation(self) -> None:
        topic_handler = 'T = "onex.evt.a.b.v1"\nS.session.execute(1)\n'
        node_py = "class N:\n    def run(self):\n        pass\n"
        report = _handle(
            [
                _node(
                    _CONTRACT_ROUTED,
                    {"handler_other.py": topic_handler},
                    node_py=node_py,
                )
            ]
        )
        [result] = report.results
        assert result.violations == [
            EnumComplianceViolation.HARDCODED_TOPIC,
            EnumComplianceViolation.UNDECLARED_TRANSPORT,
            EnumComplianceViolation.MISSING_HANDLER_ROUTING,
            EnumComplianceViolation.LOGIC_IN_NODE,
        ]
        assert result.verdict == EnumComplianceVerdict.IMPERATIVE
        assert result.violation_details[0] == (
            "hardcoded topic 'onex.evt.a.b.v1' not in contract"
        )
        assert result.undeclared_topics == ["onex.evt.a.b.v1"]
        assert result.undeclared_transports == ["DATABASE"]

    def test_one_violation_is_hybrid_and_the_allowlist_wins(self) -> None:
        nodes = [_node(_CONTRACT_ROUTED, {"handler_other.py": _CLEAN_HANDLER})]
        [result] = _handle(nodes).results
        assert result.verdict == EnumComplianceVerdict.HYBRID
        allowed = "pkg/nodes/node_x_compute/handlers/handler_other.py"
        # paths are relative to the directory three levels above the node: src/
        [allowlisted] = _handle(nodes, [allowed]).results
        assert allowlisted.allowlisted is True
        assert allowlisted.verdict == EnumComplianceVerdict.ALLOWLISTED
        assert allowlisted.violations == [
            EnumComplianceViolation.MISSING_HANDLER_ROUTING
        ]
        assert _handle(nodes, [allowed]).new_violations == []

    def test_missing_contract_carries_no_violation_and_does_not_fail(self) -> None:
        report = _handle([_node(None, {"handler_x.py": _CLEAN_HANDLER})])
        [result] = report.results
        assert result.verdict == EnumComplianceVerdict.MISSING_CONTRACT
        assert result.violations == []
        assert result.contract_path is None
        assert report.new_violations == []

    def test_contract_that_is_not_a_mapping_declares_nothing(self) -> None:
        [result] = _handle(
            [_node("- a\n- b\n", {"handler_x.py": _CLEAN_HANDLER})]
        ).results
        assert result.verdict == EnumComplianceVerdict.HYBRID
        assert result.declared_topics == []

    def test_malformed_contract_shape_fails_loudly(self) -> None:
        with pytest.raises(ModelOnexError, match="event_bus must be a mapping"):
            _handle([_node("event_bus: text\n", {"handler_x.py": _CLEAN_HANDLER})])

    def test_docstring_topics_and_syntax_errors_are_not_flagged(self) -> None:
        documented = '"""onex.evt.a.b.v1"""\n\nclass H:\n    """agent-actions"""\n'
        report = _handle(
            [
                _node(
                    _CONTRACT_ROUTED,
                    {"handler_x.py": documented, "handler_y.py": "def broken(:\n"},
                )
            ]
        )
        assert [r.used_topics for r in report.results] == [[], []]

    def test_module_is_inferred_from_the_first_src_segment(self) -> None:
        node_dir = "/work/src/pkg/nodes/node_x_compute"
        report = _handle(
            [
                _node(
                    _CONTRACT_ROUTED,
                    {"handler_x.py": _CLEAN_HANDLER},
                    node_dir=node_dir,
                )
            ]
        )
        [result] = report.results
        assert result.handler_in_routing is True
        assert result.handler_path == "pkg/nodes/node_x_compute/handlers/handler_x.py"

    def test_report_counts(self) -> None:
        report = _handle(
            [
                _node(_CONTRACT_ROUTED, {"handler_x.py": _CLEAN_HANDLER}),
                _node(
                    None,
                    {"handler_a.py": _CLEAN_HANDLER},
                    node_dir="src/pkg/nodes/node_a_compute",
                ),
                _node(
                    _CONTRACT_ROUTED,
                    {"handler_z.py": _CLEAN_HANDLER},
                    node_dir="src/pkg/nodes/node_z_compute",
                ),
            ]
        )
        assert report.total == 3
        assert report.compliant_count == 1
        assert report.allowlisted_count == 0
        assert [r.handler_path for r in report.new_violations] == [
            "pkg/nodes/node_z_compute/handlers/handler_z.py"
        ]

    def test_handle_reads_nothing_from_the_filesystem(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        [result] = _handle(
            [_node(_CONTRACT_ROUTED, {"handler_x.py": _CLEAN_HANDLER})]
        ).results
        assert result.verdict == EnumComplianceVerdict.COMPLIANT
        assert list(tmp_path.iterdir()) == []

    def test_reachability_classes(self) -> None:
        report = _handle(
            [
                _node(
                    _CONTRACT_ROUTED,
                    {
                        "handler_x.py": _CLEAN_HANDLER,
                        "tests/handler_t.py": _CLEAN_HANDLER,
                        "handler_dead.py": _CLEAN_HANDLER,
                    },
                )
            ]
        )
        by_name = {Path(r.handler_path).name: r for r in report.results}
        assert by_name["handler_x.py"].reachability == EnumReachability.LIVE
        assert by_name["handler_t.py"].reachability == EnumReachability.TEST_HARNESS
        assert by_name["handler_dead.py"].reachability == EnumReachability.DEAD


class TestModels:
    def test_input_models_forbid_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ModelComplianceNodeSource.model_validate({"node_dir": "x", "extra": 1})
        with pytest.raises(ValidationError):
            ModelHandlerContractComplianceInput.model_validate(
                {"repo": "pkg", "surprise": 1}
            )
        with pytest.raises(ValidationError):
            ModelHandlerContractComplianceReport.model_validate({"surprise": 1})

    def test_input_models_are_frozen(self) -> None:
        node = _node(_CONTRACT_ROUTED, {})
        request = ModelHandlerContractComplianceInput(repo="pkg", nodes=[node])
        for model, field in ((node, "node_dir"), (request, "repo")):
            assert model.model_config["frozen"] is True
            with pytest.raises(ValidationError):
                model.__setattr__(field, "other")


def test_allowlist_loader_rejects_nothing_it_can_read(tmp_path: Path) -> None:
    """A non-mapping allowlist is read as empty, like the source."""
    (tmp_path / "src/pkg/nodes/node_x_compute/handlers").mkdir(parents=True)
    node = tmp_path / "src/pkg/nodes/node_x_compute"
    (node / "contract.yaml").write_text(_CONTRACT_ROUTED, encoding="utf-8")
    (node / "handlers/handler_other.py").write_text(_CLEAN_HANDLER, encoding="utf-8")
    (tmp_path / "allowlist.yaml").write_text("- not\n- a mapping\n", encoding="utf-8")
    code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--allowlist-path",
            str(tmp_path / "allowlist.yaml"),
        ]
    )
    assert code == 1
