# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Real Git integration: symbol extraction, base revision ratchet and adoption."""

import json
import subprocess
from collections.abc import Callable
from importlib import import_module, resources
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_output import (
    ModelGitFileListingOutput,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_check_request import (
    ModelBoundaryImportCheckRequest,
)
from omnibase_core.models.nodes.source_file_gather.model_gathered_source_file import (
    ModelGatheredSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output import (
    ModelSourceFileGatherOutput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_boundary_import_check_compute import (
    runtime_node_boundary_import_check as runtime,
)
from omnibase_core.nodes.node_boundary_import_check_compute.analyzer import (
    DEFAULT_BASELINE,
    parse_baseline,
    render_baseline,
)
from omnibase_core.nodes.node_boundary_import_check_compute.handler import (
    NodeBoundaryImportCheckCompute,
)
from omnibase_core.nodes.node_boundary_import_check_compute.runtime_node_boundary_import_check import (
    build_container,
    main,
)
from omnibase_core.nodes.node_boundary_import_check_effect.handler import (
    NodeBoundaryImportCheckEffect,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit


def git(root: Path, *args: str) -> None:
    """Keep test Git commands independent of ambient hook environment."""
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env=scrub_git_location_env(),
    )


def write(root: Path, path: str, source: str) -> Path:
    """Create a fixture file in the isolated checkout."""
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)
    return target


def commit(root: Path) -> None:
    """Commit fixture state without signing or ambient hooks."""
    git(
        root,
        "-c",
        "user.name=Boundary Test",
        "-c",
        "user.email=boundary@example.test",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-qm",
        "fixture",
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    write(tmp_path, "src/example/__init__.py", "")
    write(tmp_path, "src/example/nodes/node_x/handler.py", "")
    write(
        tmp_path,
        "src/example/client.py",
        "from example.nodes.node_x.handler import handle\n",
    )
    git(tmp_path, "add", "src")
    commit(tmp_path)
    return tmp_path


def test_missing_baseline_fail_and_export(repo: Path) -> None:
    edges_path, report_path = repo / "edges.json", repo / "report.json"
    assert (
        main(
            [
                "--root",
                str(repo),
                "--edges-json",
                str(edges_path),
                "--report-json",
                str(report_path),
            ]
        )
        == 1
    )
    edges = json.loads(edges_path.read_text())
    assert edges == [
        {
            "importer": "example.client",
            "importer_path": "src/example/client.py",
            "line": 1,
            "target": "example.nodes.node_x.handler",
            "kind": "outside->node",
            "seam": "protocol",
            "imported_name": "handle",
            "via": "import",
        }
    ]
    assert json.loads(report_path.read_text())["overall_status"] == "FAIL"
    assert not (repo / DEFAULT_BASELINE).exists()


def test_create_shrink_and_growth_refusal(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = repo / "report.json"
    args = [
        "--root",
        str(repo),
        "--write-baseline",
        "--bootstrap",
        "--report-json",
        str(report_path),
    ]
    assert main(args) == 0
    baseline = repo / DEFAULT_BASELINE
    initial = baseline.read_text()
    assert parse_baseline(initial, str(baseline)) == (
        "example.client -> example.nodes.node_x.handler:handle",
    )
    assert json.loads(report_path.read_text())["overall_status"] == "PASS"
    git(repo, "add", DEFAULT_BASELINE)
    commit(repo)
    assert main(["--root", str(repo)]) == 0
    write(repo, "src/example/other.py", "import example.nodes.node_x.handler")
    git(repo, "add", "src/example/other.py")
    assert main(args) == 1
    assert baseline.read_text() == initial
    assert "example.other -> example.nodes.node_x.handler" in capsys.readouterr().err
    write(repo, "src/example/other.py", "")
    write(repo, "src/example/client.py", "")
    assert main(["--root", str(repo)]) == 1
    assert main(args) == 0
    assert parse_baseline(baseline.read_text(), str(baseline)) == ()
    assert main(["--root", str(repo)]) == 0
    write(repo, "src/example/client.py", "import example.nodes.node_x.handler")
    assert main(args) == 1
    assert parse_baseline(baseline.read_text(), str(baseline)) == ()


def test_custom_baseline_path(repo: Path) -> None:
    path = repo / "state" / "edges.yaml"
    assert (
        main(
            [
                "--root",
                str(repo),
                "--baseline",
                str(path),
                "--write-baseline",
                "--bootstrap",
            ]
        )
        == 0
    )
    git(repo, "add", "state/edges.yaml")
    commit(repo)
    assert main(["--root", str(repo), "--baseline", str(path)]) == 0
    assert not (repo / DEFAULT_BASELINE).exists()


@pytest.mark.parametrize(
    "source",
    [
        "not: [valid",
        "[]",
        "",
        "schema_version: 1\ngate: OMN-17427\nedges: []",
        "schema_version: true\ngate: OMN-17427\nedges: []",
        "schema_version: 2\ngate: wrong\nedges: []",
        "schema_version: 2\ngate: OMN-17427\nedges: bad",
        "schema_version: 2\ngate: OMN-17427\nedges: [bad]",
        "schema_version: 2\ngate: OMN-17427\nedges: ['z -> x:', 'a -> b:']",
        "schema_version: 2\ngate: OMN-17427\nedges: ['a -> b:', 'a -> b:']",
        "schema_version: 2\ngate: OMN-17427\nedges: []\nextra: value",
        "schema_version: 2\ngate: OMN-17427\nedges: []\nedges: []",
    ],
)
def test_malformed_baseline_error_and_no_write(repo: Path, source: str) -> None:
    baseline = write(repo, DEFAULT_BASELINE, source)
    report = repo / "report.json"
    assert (
        main(["--root", str(repo), "--write-baseline", "--report-json", str(report)])
        == 1
    )
    assert baseline.read_text() == source
    result = json.loads(report.read_text())
    assert result["overall_status"] == "ERROR"
    assert any(f["rule_id"] == "malformed-baseline" for f in result["findings"])


def test_tracked_only_and_excluded_paths(repo: Path) -> None:
    write(repo, "src/example/client.py", "")
    write(repo, "plugins/untracked.py", "from omnibase_infra._private import api")
    write(repo, "tests/bad.py", "invalid python !!!")
    git(repo, "add", "tests")
    assert main(["--root", str(repo)]) == 0
    git(repo, "add", "plugins")
    assert main(["--root", str(repo)]) == 1
    container = build_container()
    try:
        gathered = container.get_service(NodeBoundaryImportCheckEffect).handle(
            ModelBoundaryImportCheckRequest(root=str(repo))
        )
    finally:
        container.close()
    assert gathered.repo_packages == ("example",)
    assert "example.nodes.node_x" in gathered.node_packages


def test_zero_files_error(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    write(tmp_path, "untracked.py", "")
    write(tmp_path, "tests/test_ignored.py", "")
    git(tmp_path, "add", "tests")
    commit(tmp_path)
    report = tmp_path / "report.json"
    assert (
        main(
            ["--root", str(tmp_path), "--write-baseline", "--report-json", str(report)]
        )
        == 1
    )
    result = json.loads(report.read_text())
    assert result["overall_status"] == "ERROR"
    assert "zero files" in result["findings"][0]["message"]
    assert not (tmp_path / DEFAULT_BASELINE).exists()


def test_unreadable_and_unparseable_error_prevents_writes(repo: Path) -> None:
    client = repo / "src/example/client.py"
    for content in (b"\xff", b"bad python !!!"):
        client.write_bytes(content)
        assert main(["--root", str(repo), "--write-baseline"]) == 1
        assert not (repo / DEFAULT_BASELINE).exists()
    client.unlink()
    assert main(["--root", str(repo), "--write-baseline"]) == 1
    assert not (repo / DEFAULT_BASELINE).exists()


def test_not_a_git_repo_error(tmp_path: Path) -> None:
    assert main(["--root", str(tmp_path)]) == 1


def test_artifact_write_failure_is_error(repo: Path) -> None:
    baseline = write(
        repo,
        DEFAULT_BASELINE,
        render_baseline(("example.client -> example.nodes.node_x.handler:handle",)),
    )
    report = repo / "report.json"
    assert (
        main(
            [
                "--root",
                str(repo),
                "--edges-json",
                str(repo),
                "--report-json",
                str(report),
            ]
        )
        == 1
    )
    assert json.loads(report.read_text())["overall_status"] == "ERROR"
    assert baseline.exists()


def adopt(repo: Path) -> tuple[str, ...]:
    """Install v2 fixture baseline at HEAD for historical comparisons."""
    assert main(["--root", str(repo), "--write-baseline", "--bootstrap"]) == 0
    git(repo, "add", DEFAULT_BASELINE)
    commit(repo)
    return parse_baseline((repo / DEFAULT_BASELINE).read_text(), DEFAULT_BASELINE)


def rules(repo: Path, *args: str) -> set[str]:
    report = repo / "report.json"
    assert main(["--root", str(repo), "--report-json", str(report), *args]) == 1
    return {
        finding["rule_id"] for finding in json.loads(report.read_text())["findings"]
    }


@pytest.mark.parametrize("replace", [False, True])
def test_manual_baseline_addition_and_replacement_fail(
    repo: Path, replace: bool
) -> None:
    initial = adopt(repo)
    write(
        repo, "src/example/other.py", "from example.nodes.node_x.handler import other"
    )
    git(repo, "add", "src/example/other.py")
    if replace:
        write(repo, "src/example/client.py", "")
    candidate = (
        ("example.other -> example.nodes.node_x.handler:other",)
        if replace
        else initial + ("example.other -> example.nodes.node_x.handler:other",)
    )
    baseline = write(repo, DEFAULT_BASELINE, render_baseline(candidate))
    assert rules(repo) == {"baseline-growth"}
    current = baseline.read_text()
    assert "baseline-growth" in rules(repo, "--write-baseline", "--bootstrap")
    assert baseline.read_text() == current


def test_delete_baseline_cannot_rebootstrap_existing_base(repo: Path) -> None:
    adopt(repo)
    baseline = repo / DEFAULT_BASELINE
    baseline.unlink()
    assert "baseline-deleted" in rules(repo)
    assert main(["--root", str(repo), "--write-baseline"]) == 0
    assert baseline.exists()
    write(repo, "src/example/other.py", "import example.nodes.node_x.handler")
    git(repo, "add", "src/example/other.py")
    baseline.unlink()
    assert main(["--root", str(repo), "--write-baseline", "--bootstrap"]) == 1
    assert not baseline.exists()


def test_no_base_baseline_requires_explicit_bootstrap(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    identity = "example.client -> example.nodes.node_x.handler:handle"
    baseline = write(repo, DEFAULT_BASELINE, render_baseline((identity,)))
    assert rules(repo) == {"baseline-bootstrap-unflagged"}
    assert main(["--root", str(repo), "--bootstrap"]) == 0
    out = capsys.readouterr().out
    assert "Baseline adoption authorized by --bootstrap" in out
    assert "WARN" not in out and "INFO" not in out
    baseline.unlink()
    assert main(["--root", str(repo), "--write-baseline"]) == 1
    assert not baseline.exists()
    assert main(["--root", str(repo), "--write-baseline", "--bootstrap"]) == 0


def test_delete_commit_rebootstrap_against_merge_base_fails(repo: Path) -> None:
    adopt(repo)
    git(repo, "tag", "baseline-base")
    git(repo, "rm", DEFAULT_BASELINE)
    commit(repo)
    write(
        repo,
        DEFAULT_BASELINE,
        render_baseline(("example.client -> example.nodes.node_x.handler:handle",)),
    )
    assert "baseline-bootstrap-unflagged" in rules(repo)
    assert main(["--root", str(repo), "--base", "baseline-base"]) == 0
    write(repo, "src/example/other.py", "import example.nodes.node_x.handler")
    git(repo, "add", "src/example/other.py")
    write(
        repo,
        DEFAULT_BASELINE,
        render_baseline(
            (
                "example.client -> example.nodes.node_x.handler:handle",
                "example.other -> example.nodes.node_x.handler:",
            )
        ),
    )
    assert "baseline-growth" in rules(repo, "--base", "baseline-base", "--bootstrap")


def test_invalid_base_is_error_even_with_bootstrap(repo: Path) -> None:
    assert "scan-error" in rules(
        repo, "--base", "nonexistent-revision", "--bootstrap", "--write-baseline"
    )
    assert not (repo / DEFAULT_BASELINE).exists()


def test_version_one_tells_user_to_rebootstrap(repo: Path) -> None:
    write(repo, DEFAULT_BASELINE, "schema_version: 1\ngate: OMN-17427\nedges: []")
    assert rules(repo, "--bootstrap") == {"malformed-baseline"}
    assert "rebootstrap with --bootstrap" in (repo / "report.json").read_text()


def test_base_malformed_is_error_and_cannot_write(repo: Path) -> None:
    write(repo, DEFAULT_BASELINE, "schema_version: 1\ngate: OMN-17427\nedges: []")
    git(repo, "add", DEFAULT_BASELINE)
    commit(repo)
    (repo / DEFAULT_BASELINE).unlink()
    assert "malformed-baseline" in rules(repo, "--write-baseline", "--bootstrap")
    assert not (repo / DEFAULT_BASELINE).exists()


def test_yaml_and_string_inventory_is_tracked_and_summary_counts_pairs(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        repo,
        "src/example/client.py",
        "handler = 'omnibase_infra.nodes.node_remote.handler:ModelReply'\nother = 'omnibase_infra.nodes.node_remote.handler:ProtocolReply'\n",
    )
    write(
        repo,
        "src/example/contract.yml",
        "handler: omnibase_infra.nodes.node_remote.handler:ServiceError\n",
    )
    write(
        repo,
        "src/example/untracked.yaml",
        "handler: omnibase_infra.nodes.node_remote.handler:Untracked\n",
    )
    write(
        repo,
        "outside.yaml",
        "handler: omnibase_infra.nodes.node_remote.handler:Outside\n",
    )
    git(repo, "add", "src/example/contract.yml", "outside.yaml")
    edges_json = repo / "edges.json"
    assert main(["--root", str(repo), "--edges-json", str(edges_json)]) == 1
    edges = json.loads(edges_json.read_text())
    assert len(edges) == 3
    assert {edge["via"] for edge in edges} == {"string", "yaml"}
    assert "Module pairs: 2" in capsys.readouterr().out


def test_combined_edge_and_baseline_commit_fails_against_base(repo: Path) -> None:
    initial = adopt(repo)
    git(repo, "tag", "merge-base")
    write(repo, "src/example/other.py", "import example.nodes.node_x.handler")
    write(
        repo,
        DEFAULT_BASELINE,
        render_baseline(initial + ("example.other -> example.nodes.node_x.handler:",)),
    )
    git(repo, "add", "src/example/other.py", DEFAULT_BASELINE)
    commit(repo)
    assert rules(repo, "--base", "merge-base", "--bootstrap") == {"baseline-growth"}


def test_write_refuses_current_growth_even_when_base_contains_symbol(
    repo: Path,
) -> None:
    adopt(repo)
    baseline = write(repo, DEFAULT_BASELINE, render_baseline(()))
    current = baseline.read_text()
    assert main(["--root", str(repo), "--write-baseline", "--bootstrap"]) == 1
    assert baseline.read_text() == current


def test_empty_adoption_still_requires_flag(repo: Path) -> None:
    write(repo, "src/example/client.py", "")
    assert "baseline-bootstrap-unflagged" in rules(repo, "--write-baseline")
    assert not (repo / DEFAULT_BASELINE).exists()
    assert main(["--root", str(repo), "--write-baseline", "--bootstrap"]) == 0


@pytest.mark.parametrize("bootstrap", [False, True])
def test_deleted_baseline_with_zero_edges_fails(repo: Path, bootstrap: bool) -> None:
    adopt(repo)
    write(repo, "src/example/client.py", "")
    baseline = repo / DEFAULT_BASELINE
    baseline.unlink()
    args = ("--bootstrap",) if bootstrap else ()
    assert rules(repo, *args) == {"baseline-deleted"}
    report = json.loads((repo / "report.json").read_text())
    assert report["overall_status"] == "FAIL"
    assert report["findings"][0]["message"] == (
        "The baseline is kept, with an empty edges list when every "
        "edge is retired; it is never deleted after adoption."
    )
    assert not baseline.exists()
    assert main(["--root", str(repo), "--write-baseline", *args]) == 0
    assert baseline.is_file()
    assert parse_baseline(baseline.read_text(), DEFAULT_BASELINE) == ()
    assert main(["--root", str(repo), *args]) == 0


@pytest.mark.parametrize("bootstrap", [False, True])
def test_empty_list_baseline_with_zero_edges_passes(
    repo: Path, bootstrap: bool
) -> None:
    adopt(repo)
    write(repo, "src/example/client.py", "")
    baseline = write(repo, DEFAULT_BASELINE, render_baseline(()))
    args = ["--bootstrap"] if bootstrap else []
    assert main(["--root", str(repo), *args]) == 0
    assert baseline.is_file()
    assert parse_baseline(baseline.read_text(), DEFAULT_BASELINE) == ()


@pytest.mark.parametrize("bootstrap", [False, True])
def test_empty_base_baseline_cannot_grow(repo: Path, bootstrap: bool) -> None:
    write(repo, "src/example/client.py", "")
    adopt(repo)
    write(repo, "src/example/client.py", "import example.nodes.node_x.handler")
    baseline = write(
        repo,
        DEFAULT_BASELINE,
        render_baseline(("example.client -> example.nodes.node_x.handler:",)),
    )
    current = baseline.read_text()
    args = ("--bootstrap",) if bootstrap else ()
    assert rules(repo, *args) == {"baseline-growth"}
    assert rules(repo, "--write-baseline", *args) == {"baseline-growth"}
    assert baseline.read_text() == current


def test_effect_requires_container() -> None:
    with pytest.raises(TypeError, match="container"):
        cast(
            "Callable[[], NodeBoundaryImportCheckEffect]", NodeBoundaryImportCheckEffect
        )()


def test_main_uses_supplied_container(repo: Path) -> None:
    backing = build_container()
    try:
        effect = backing.get_service(NodeBoundaryImportCheckEffect)
        compute = Mock(spec=NodeBoundaryImportCheckCompute)
        compute.handle.return_value = ModelValidationReport.from_findings(
            findings=(), request=ModelValidationRequestRef(profile="default")
        )
        supplied = Mock(spec=ModelONEXContainer)
        supplied.get_service.side_effect = lambda token: (
            effect if token is NodeBoundaryImportCheckEffect else compute
        )
        assert main(["--root", str(repo)], container=supplied) == 0
        compute.handle.assert_called_once()
        assert {call.args[0] for call in supplied.get_service.call_args_list} == {
            NodeBoundaryImportCheckEffect,
            NodeBoundaryImportCheckCompute,
        }
        supplied.close.assert_not_called()
    finally:
        backing.close()


def test_effect_uses_injected_collaborators(repo: Path) -> None:
    source_path = "src/example/client.py"
    baseline = write(repo, DEFAULT_BASELINE, render_baseline(()))
    listing, gatherer, writer = Mock(), Mock(), Mock()
    listing.handle.return_value = ModelGitFileListingOutput(paths=[source_path])
    gatherer.handle.side_effect = [
        ModelSourceFileGatherOutput(
            root=str(repo),
            files=[
                ModelGatheredSourceFile(
                    path=str(repo / source_path),
                    size_bytes=0,
                    source="injected = True\n",
                )
            ],
        ),
        ModelSourceFileGatherOutput(
            root=str(repo),
            files=[
                ModelGatheredSourceFile(
                    path=str(baseline), size_bytes=0, source=render_baseline(())
                )
            ],
        ),
    ]
    services = {
        "GitFileListingInterface": listing,
        "SourceFileGatherInterface": gatherer,
        "ValidationReportWriteInterface": writer,
    }
    container = Mock(spec=ModelONEXContainer)
    container.get_service.side_effect = lambda token: services[token.__name__]
    effect = NodeBoundaryImportCheckEffect(cast(ModelONEXContainer, container))
    result = effect.handle(ModelBoundaryImportCheckRequest(root=str(repo)))
    assert [(file.path, file.source) for file in result.files] == [
        (source_path, "injected = True\n")
    ]
    assert result.baseline_present and result.baseline_edges == ()
    assert listing.handle.call_count == 1
    assert gatherer.handle.call_count == 2
    assert gatherer.handle.call_args_list[0].args[0].explicit_paths == [
        str(repo / source_path)
    ]
    assert gatherer.handle.call_args_list[1].args[0].explicit_paths == [str(baseline)]
    report = ModelValidationReport.from_findings(
        findings=(), request=ModelValidationRequestRef(profile="default")
    )
    effect.write_report(str(repo / "injected-report.json"), report)
    written = writer.handle.call_args.args[0]
    assert written.report is report
    assert written.report_path == str(repo / "injected-report.json")
    assert {
        call.args[0].__name__ for call in container.get_service.call_args_list
    } == set(services)


@pytest.mark.parametrize(
    "missing",
    [
        "GitFileListingInterface",
        "SourceFileGatherInterface",
        "ValidationReportWriteInterface",
    ],
)
def test_effect_refuses_unbound_dependency(missing: str) -> None:
    container = Mock(spec=ModelONEXContainer)

    def resolve(token: type[object]) -> Mock:
        if token.__name__ == missing:
            raise LookupError("dependency unbound")
        return Mock()

    container.get_service.side_effect = resolve
    with pytest.raises(LookupError, match="dependency unbound"):
        NodeBoundaryImportCheckEffect(cast(ModelONEXContainer, container))


def test_effect_contract_dependencies_are_bound() -> None:
    contract = resources.files(
        "omnibase_core.nodes.node_boundary_import_check_effect"
    ).joinpath("contract.yaml")
    dependencies = yaml.safe_load(contract.read_text())["protocol_dependencies"]
    assert {dep["name"] for dep in dependencies} == {
        "GitFileListingInterface",
        "SourceFileGatherInterface",
        "ValidationReportWriteInterface",
    }
    container = build_container()
    try:
        for dependency in dependencies:
            assert dependency["required"] is True
            module, name = dependency["protocol"].split(":")
            protocol = getattr(import_module(module), name)
            assert isinstance(container.get_service(protocol), protocol)
        assert isinstance(
            container.get_service(NodeBoundaryImportCheckEffect),
            NodeBoundaryImportCheckEffect,
        )
    finally:
        container.close()


@pytest.mark.parametrize("change", ["unbound", "missing", "malformed"])
def test_container_reads_contract_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    original = resources.files(
        "omnibase_core.nodes.node_boundary_import_check_effect"
    ).joinpath("contract.yaml")
    document = yaml.safe_load(original.read_text())
    if change == "unbound":
        document["protocol_dependencies"][0]["protocol"] = (
            "example.ports:ProtocolUnbound"
        )
    elif change == "missing":
        document["protocol_dependencies"].pop()
    else:
        document["protocol_dependencies"] = {"unexpected": "mapping"}
    (tmp_path / "contract.yaml").write_text(yaml.safe_dump(document))
    monkeypatch.setattr(
        runtime, "resources", SimpleNamespace(files=lambda package: tmp_path)
    )
    with pytest.raises(ModelOnexError):
        build_container()
