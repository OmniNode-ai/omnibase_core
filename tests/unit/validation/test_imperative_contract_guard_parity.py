# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Parity of the imperative contract guard with the OCC validator at 725d2967 (OMN-20918).

``tests/fixtures/occ_imperative_contract_guard/manifest.yaml`` lists, for each of the
five consumer repositories (omnibase_infra, omniclaude, omniintelligence, omnimarket,
omnimemory), a recorded slice of the repository's dev head and a ``-plant`` variant of
it with a planted live freestanding raw-HTTP module and a planted routed handler with a
hardcoded topic. ``expected/<id>.stdout.txt`` and ``<id>.json.txt`` are the output of
``check-imperative-contracts --allowlists-dir ... --scan-freestanding`` from
onex_change_control at 725d2967 on that slice with the repository's allowlist, copied
byte for byte from that revision (``allowlists/<repo>.yaml.txt``). The core guard must
reproduce stdout, JSON and exit code, so a consumer that repoints to it sees the same
findings.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.governance.enum_compliance_violation import (
    EnumComplianceViolation,
)
from omnibase_core.enums.governance.enum_reachability import EnumReachability
from omnibase_core.handlers.handler_imperative_allowlist_ratchet import (
    allowlisted_paths,
)
from omnibase_core.handlers.handler_imperative_contract_guard import (
    HandlerImperativeContractGuard,
)
from omnibase_core.handlers.handler_imperative_contract_guard_cli import main
from omnibase_core.models.nodes.handler_contract_compliance.model_compliance_node_source import (
    ModelComplianceNodeSource,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_guard_contract_source import (
    ModelGuardContractSource,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_guard_module_source import (
    ModelGuardModuleSource,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_imperative_contract_guard_input import (
    ModelImperativeContractGuardInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "occ_imperative_contract_guard"
)

CONSUMERS = (
    "omnibase_infra",
    "omniclaude",
    "omniintelligence",
    "omnimarket",
    "omnimemory",
)

# Entries of allowlists/<repo>.yaml in onex_change_control at 725d2967.
OCC_ALLOWLIST_ENTRIES = {
    "omnibase_infra": 74,
    "omniclaude": 8,
    "omniintelligence": 132,
    "omnimarket": 279,
    "omnimemory": 4,
}


class _Case(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    repo: str
    trees: list[str]
    expected_exit: int


def _cases() -> list[_Case]:
    raw = yaml.safe_load((FIXTURES / "manifest.yaml").read_text(encoding="utf-8"))
    return [_Case(**item) for item in raw]


def _materialise(case: _Case, root: Path) -> Path:
    """Write the case's trees and allowlist under ``root``; return the repository root."""
    repo = root / case.repo
    for tree in case.trees:
        base = FIXTURES / "trees" / tree
        for source in base.rglob("*.txt"):
            target = repo / source.relative_to(base).with_suffix("")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, target)
    (root / "allowlists").mkdir()
    shutil.copy(
        FIXTURES / "allowlists" / f"{case.repo}.yaml.txt",
        root / "allowlists" / f"{case.repo}.yaml",
    )
    return repo


def _run(
    capsys: pytest.CaptureFixture[str], root: Path, repo: Path, *flags: str
) -> tuple[int, str]:
    capsys.readouterr()
    code = main(
        [
            "--repo-root",
            str(repo),
            "--allowlists-dir",
            str(root / "allowlists"),
            "--scan-freestanding",
            *flags,
        ]
    )
    return code, capsys.readouterr().out.replace(str(root.resolve()), "<ROOT>")


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c.id)
def test_imperative_contract_text_matches_occ(
    case: _Case, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _materialise(case, tmp_path)
    code, out = _run(capsys, tmp_path, repo)
    expected = (FIXTURES / "expected" / f"{case.id}.stdout.txt").read_text("utf-8")
    assert out == expected
    assert code == case.expected_exit


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c.id)
def test_imperative_contract_json_matches_occ(
    case: _Case, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _materialise(case, tmp_path)
    code, out = _run(capsys, tmp_path, repo, "--json")
    expected = (FIXTURES / "expected" / f"{case.id}.json.txt").read_text("utf-8")
    assert out == expected
    assert code == case.expected_exit


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c.id)
def test_imperative_contract_allowlist_path_flag_finds_the_same(
    case: _Case, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The caller's own allowlist, named by --allowlist-path, judges like --allowlists-dir."""
    repo = _materialise(case, tmp_path)
    shutil.copy(
        FIXTURES / "allowlists" / f"{case.repo}.yaml.txt",
        repo / "imperative-contract-allowlist.yaml",
    )
    capsys.readouterr()
    code = main(
        [
            "--repo-root",
            str(repo),
            "--allowlist-path",
            "imperative-contract-allowlist.yaml",
            "--scan-freestanding",
            "--json",
        ]
    )
    got = json.loads(capsys.readouterr().out)
    expected = json.loads(
        (FIXTURES / "expected" / f"{case.id}.json.txt")
        .read_text("utf-8")
        .replace("<ROOT>", str(tmp_path.resolve()))
    )
    for summary in (*got, *expected):
        summary.pop("allowlist_path")
    assert got == expected
    assert code == case.expected_exit


def test_imperative_contract_every_consumer_has_a_parity_case_and_a_plant() -> None:
    cases = {c.id: c for c in _cases()}
    for repo in CONSUMERS:
        assert cases[repo].repo == repo
        assert cases[f"{repo}-plant"].trees == [repo, f"{repo}-plant"]


@pytest.mark.parametrize("repo", CONSUMERS)
def test_imperative_contract_allowlist_fixture_keeps_every_occ_entry(
    repo: str,
) -> None:
    text = (FIXTURES / "allowlists" / f"{repo}.yaml.txt").read_text(encoding="utf-8")
    assert len(allowlisted_paths(text)) == OCC_ALLOWLIST_ENTRIES[repo]


@pytest.mark.parametrize("repo", CONSUMERS)
def test_imperative_contract_planted_freestanding_io_is_found_by_the_guard(
    repo: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Positive control: the planted module blocks the plant slice and not the slice."""
    cases = {c.id: c for c in _cases()}
    planted = "planted_imperative_io.py"
    plant_root = tmp_path / "plant"
    plant_root.mkdir()
    code, out = _run(
        capsys,
        plant_root,
        _materialise(cases[f"{repo}-plant"], plant_root),
        "--no-fail",
    )
    assert code == 0
    blocking = out.split("Blocking LIVE freestanding imperative violations:")[1]
    assert planted in blocking.split("Reported non-live")[0]
    assert "raw HTTP call 'requests.post'" in out
    assert "hardcoded topic 'onex.evt.planted.thing.v1' not in contract" in out

    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    _, clean_out = _run(
        capsys, clean_root, _materialise(cases[repo], clean_root), "--no-fail"
    )
    assert planted not in clean_out


# --- The pure handler ---

_PYPROJECT = '[project]\nname = "pkg"\n\n[project.scripts]\ntool = "pkg.tool:main"\n'
_RAW_HTTP = "import requests\n\n\ndef main():\n    requests.get('http://x.example/')\n"


def _guard(
    modules: dict[str, str],
    *,
    allowlisted: tuple[str, ...] = (),
    pyproject: str | None = _PYPROJECT,
    contracts: tuple[ModelGuardContractSource, ...] = (),
    nodes: tuple[ModelComplianceNodeSource, ...] = (),
):
    return HandlerImperativeContractGuard().handle(
        ModelImperativeContractGuardInput(
            repo="pkg",
            nodes=list(nodes),
            allowlisted_paths=list(allowlisted),
            scan_freestanding=True,
            modules=[
                ModelGuardModuleSource(path=p, source=s) for p, s in modules.items()
            ],
            contracts=list(contracts),
            pyproject_text=pyproject,
        )
    )


def test_imperative_contract_handler_blocks_a_live_freestanding_module() -> None:
    report = _guard({"src/pkg/tool.py": _RAW_HTTP})
    (result,) = report.blocking_freestanding
    assert result.module_path == "src/pkg/tool.py"
    assert result.reachability == EnumReachability.LIVE
    assert [f.violation for f in result.findings] == [
        EnumComplianceViolation.RAW_HTTP_INFERENCE
    ]
    assert report.new_violation_count == 1


def test_imperative_contract_handler_follows_imports_from_the_entrypoint() -> None:
    report = _guard(
        {
            "src/pkg/tool.py": "from pkg import helper\n\n\ndef main():\n    helper.go()\n",
            "src/pkg/helper.py": _RAW_HTTP,
        }
    )
    (result,) = report.blocking_freestanding
    assert result.module_path == "src/pkg/helper.py"


def test_imperative_contract_handler_reports_an_unreachable_module_as_non_live() -> (
    None
):
    report = _guard({"src/pkg/orphan.py": _RAW_HTTP})
    assert report.new_violation_count == 0
    (result,) = report.non_live_freestanding
    assert result.reachability == EnumReachability.DEAD


def test_imperative_contract_handler_classifies_test_named_modules() -> None:
    report = _guard({"src/pkg/test_helpers.py": _RAW_HTTP})
    (result,) = report.non_live_freestanding
    assert result.reachability == EnumReachability.TEST_HARNESS


def test_imperative_contract_handler_roots_liveness_in_a_contract_handler() -> None:
    contract = ModelGuardContractSource(
        path="src/pkg/nodes/node_x/contract.yaml",
        text=(
            "handler_routing:\n  handlers:\n    - handler:\n"
            "        module: pkg.adapter\n"
        ),
    )
    report = _guard(
        {"src/pkg/adapter.py": _RAW_HTTP}, pyproject=None, contracts=(contract,)
    )
    assert report.new_violation_count == 1


def test_imperative_contract_handler_roots_liveness_in_node_py_beside_a_contract() -> (
    None
):
    contract = ModelGuardContractSource(
        path="src/pkg/nodes/node_x/contract.yaml", text="{}\n", has_node_py=True
    )
    report = _guard(
        {
            "src/pkg/nodes/node_x/node.py": "from pkg import adapter\n",
            "src/pkg/adapter.py": _RAW_HTTP,
        },
        pyproject=None,
        contracts=(contract,),
    )
    assert report.new_violation_count == 1


def test_imperative_contract_handler_admits_an_allowlisted_module() -> None:
    report = _guard({"src/pkg/tool.py": _RAW_HTTP}, allowlisted=("src/pkg/tool.py",))
    assert report.new_violation_count == 0
    assert report.allowlisted_count == 1


def test_imperative_contract_handler_honours_the_inline_suppression() -> None:
    source = (
        "import requests\n\n\ndef main():\n"
        "    requests.get('x')  # no-contract-check: mock server in a fixture\n"
    )
    report = _guard({"src/pkg/tool.py": source})
    assert report.new_violation_count == 0
    (result,) = report.freestanding_results
    assert result.findings[0].suppressed
    assert result.active_findings == []


def test_imperative_contract_handler_leaves_tests_init_and_node_code_to_others() -> (
    None
):
    report = _guard(
        {
            "src/pkg/tool.py": "def main():\n    pass\n",
            "src/pkg/__init__.py": _RAW_HTTP,
            "src/pkg/tests/test_x.py": _RAW_HTTP,
            "src/pkg/nodes/node_x/handlers/handler_x.py": _RAW_HTTP,
            "src/pkg/nodes/node_x/node.py": _RAW_HTTP,
        }
    )
    assert report.freestanding_module_count == 1
    assert [r.module_path for r in report.freestanding_results] == ["src/pkg/tool.py"]


def test_imperative_contract_handler_scans_freestanding_only_when_asked() -> None:
    report = HandlerImperativeContractGuard().handle(
        ModelImperativeContractGuardInput(
            repo="pkg",
            modules=[ModelGuardModuleSource(path="src/pkg/tool.py", source=_RAW_HTTP)],
            pyproject_text=_PYPROJECT,
        )
    )
    assert not report.freestanding_scanned
    assert report.freestanding_results == []


def test_imperative_contract_handler_blocks_a_routed_node_handler_violation() -> None:
    node = ModelComplianceNodeSource(
        node_dir="src/pkg/nodes/node_x",
        contract_yaml=(
            "handler_routing:\n  handlers:\n    - handler:\n"
            "        module: pkg.nodes.node_x.handlers.handler_x\n"
        ),
        handlers=[
            ModelSourceFile(
                path="src/pkg/nodes/node_x/handlers/handler_x.py",
                source="TOPIC = 'onex.evt.a.b.v1'\n",
            )
        ],
    )
    report = _guard({}, nodes=(node,))
    (result,) = report.blocking_results
    assert result.handler_path == "pkg/nodes/node_x/handlers/handler_x.py"


def test_imperative_contract_cli_finds_modules_whatever_directory_holds_the_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A checkout under a directory named ``tests`` is still scanned (see PR body)."""
    repo = tmp_path / "tests" / "work" / "pkg"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "pyproject.toml").write_text(_PYPROJECT)
    (repo / "src" / "pkg" / "tool.py").write_text(_RAW_HTTP)
    capsys.readouterr()
    code = main(["--repo-root", str(repo), "--scan-freestanding"])
    assert code == 1
    assert "src/pkg/tool.py" in capsys.readouterr().out
