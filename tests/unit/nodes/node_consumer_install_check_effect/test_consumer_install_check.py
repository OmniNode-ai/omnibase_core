# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""AC1 to AC4 of OMN-26670: a candidate build is installed into consumer checkouts before merge.

AC1  every consumer the overlay names is installed with the candidate, every entry
     point is imported and the unit tests are collected; the job is wired into CI.
AC2  a failure names the consumer, the import and the missing name.
AC3  a replay of the omnibase-core 0.47.77 change (the removal of
     ``omnibase_core.cli.cli_work_ledger_render``) against a consumer that imported
     it fails; against the fixed consumer it passes.
AC4  the bound comes from the overlay, and a docs-only change does not run the job.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import cast

import pytest
import yaml

from omnibase_core.models.nodes.consumer_install_check.model_command_outcome import (
    ModelCommandOutcome,
)
from omnibase_core.models.nodes.consumer_install_check.model_command_request import (
    ModelCommandRequest,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_install_request import (
    ModelConsumerInstallRequest,
)
from omnibase_core.models.nodes.consumer_install_check.model_consumer_install_result import (
    ModelConsumerInstallResult,
)
from omnibase_core.nodes.node_consumer_install_check_effect import (
    runtime_entry_point_probe,
)
from omnibase_core.nodes.node_consumer_install_check_effect.exec_subprocess import (
    HandlerSubprocessExec,
)
from omnibase_core.nodes.node_consumer_install_check_effect.handler_consumer_install_check import (
    HandlerConsumerInstallCheck,
    parse_collection_output,
)
from omnibase_core.nodes.node_consumer_install_check_effect.runtime_consumer_install_check import (
    build_container,
    main,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
NODE_DIR = REPO_ROOT / "src/omnibase_core/nodes/node_consumer_install_check_effect"
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
REUSABLE = REPO_ROOT / ".github/workflows/consumer-install-check.yml"
OVERLAY = (
    REPO_ROOT / "config/onex/overlays/node_consumer_install_check_effect.overlay.yaml"
)
REMOVED_MODULE = "omnibase_core.cli.cli_work_ledger_render"
REMOVED_IMPORT = f"from {REMOVED_MODULE} import MD_LEDGER_PATH_ENV"


def _overlay(
    tmp_path: Path, *, budget: float = 300.0, fail_unattributed: bool = False
) -> Path:
    document = {
        "schema_version": 1,
        "python_version": "3.12",
        "step_timeout_seconds": 60,
        "total_budget_seconds": budget,
        "max_parallel": 1,
        "fail_on_unattributed": fail_unattributed,
        "consumers": [
            {
                "name": name,
                "distribution": dist,
                "repo_url": f"https://example.invalid/{name}.git",
                "ref": ref,
                "install_args": ["-e", ".", "--group", "dev"],
                "collect_args": ["tests/unit"],
                **({"smoke_script": "tests/ci/smoke.py"} if name == "alpha" else {}),
            }
            for name, dist, ref in (
                ("alpha", "alpha-dist", "dev"),
                ("beta", "beta-dist", "main"),
            )
        ],
        "candidates": [
            {
                "distribution": "cand-dist",
                "import_roots": ["omnibase_core", "cand_pkg"],
                "consumers": ["alpha", "beta"],
            }
        ],
    }
    path = tmp_path / "overlay.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


class _FakeRunner:
    """Records every command; answers the probe, the smoke and the collection with canned data."""

    def __init__(self) -> None:
        self.failures: dict[str, list[dict[str, object]]] = {}
        self.calls: list[tuple[tuple[str, ...], Path | None]] = []
        self.smoke_output = "LATEST-CORE-SMOKE packages=3 modules_tried=9 failed=0\n"

    def handle(self, request: ModelCommandRequest) -> ModelCommandOutcome:
        command = request.argv
        self.calls.append((command, request.cwd))
        if "runtime_entry_point_probe.py" in " ".join(command):
            out = Path(command[command.index("--out") + 1])
            consumer = command[command.index("--distribution") + 1].removesuffix(
                "-dist"
            )
            found = self.failures.get(consumer, [])
            out.write_text(
                json.dumps(
                    {
                        "distribution": consumer,
                        "entry_points": 5,
                        "imported": 5 - len(found),
                        "failures": found,
                    }
                ),
                encoding="utf-8",
            )
            return ModelCommandOutcome(returncode=0, output="")
        if any(part.endswith("tests/ci/smoke.py") for part in command):
            return ModelCommandOutcome(returncode=0, output=self.smoke_output)
        if "--collect-only" in command:
            return ModelCommandOutcome(
                returncode=0, output="42 tests collected in 1.2s\n"
            )
        return ModelCommandOutcome(returncode=0, output="")


def _check(
    request: ModelConsumerInstallRequest,
    failures: dict[str, list[dict[str, object]]] | None = None,
    smoke_output: str | None = None,
) -> tuple[ModelConsumerInstallResult, _FakeRunner]:
    container = build_container(
        command_handler=cast("type[HandlerSubprocessExec]", _FakeRunner)
    )
    runner = cast(
        "_FakeRunner",
        container.get_service(HandlerSubprocessExec),
    )
    runner.failures = failures or {}
    if smoke_output is not None:
        runner.smoke_output = smoke_output
    handler = container.get_service(HandlerConsumerInstallCheck)
    return handler.handle(request), runner


def _request(tmp_path: Path, overlay: Path) -> ModelConsumerInstallRequest:
    return ModelConsumerInstallRequest(
        candidate_distribution="cand-dist",
        candidate_spec="/dist/cand_dist-1.0-py3-none-any.whl",
        overlay_path=overlay,
        work_dir=tmp_path / "work",
    )


def test_ac1_every_overlay_consumer_gets_checkout_install_candidate_probe_and_collection(
    tmp_path: Path,
) -> None:
    result, runner = _check(_request(tmp_path, _overlay(tmp_path)))
    assert result.passed is True
    assert [o.consumer for o in result.outcomes] == ["alpha", "beta"]
    flat = [" ".join(argv) for argv, _ in runner.calls]
    for name, ref in (("alpha", "dev"), ("beta", "main")):
        mine = [c for c in flat if f"/{name}" in c]
        assert any(
            f"fetch --depth 1 https://example.invalid/{name}.git {ref}" in c
            for c in mine
        )
        assert any("uv pip install" in c and "--group dev" in c for c in mine)
        assert any(
            "--no-deps" in c and "cand_dist-1.0-py3-none-any.whl" in c for c in mine
        )
        assert any(
            "runtime_entry_point_probe.py" in c and f"{name}-dist" in c for c in mine
        )
        assert any("--collect-only" in c and "tests/unit" in c for c in mine)
    outcome = result.outcomes[0]
    assert (outcome.entry_points_imported, outcome.tests_collected) == (5, 42)
    # the candidate is installed after the consumer, never before it
    install = [i for i, c in enumerate(flat) if "uv pip install" in c and "alpha" in c]
    assert len(install) == 2 and "--no-deps" in flat[install[1]]


def test_ac1_consumer_ref_comes_from_the_overlay_and_a_replay_may_override_it(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path, _overlay(tmp_path)).model_copy(
        update={"consumer_ref_overrides": (("alpha", "replay-ref"),)}
    )
    _, runner = _check(request)
    flat = [" ".join(argv) for argv, _ in runner.calls]
    assert any("alpha.git replay-ref" in c for c in flat)
    assert any("beta.git main" in c for c in flat)


def test_ac1_the_handler_holds_no_consumer_literal() -> None:
    source = (NODE_DIR / "handler_consumer_install_check.py").read_text(
        encoding="utf-8"
    )
    for literal in ("omnimarket", "omnibase_infra", "OmniNode-ai", "github.com"):
        assert literal not in source, literal


def test_ac1_the_shipped_overlay_names_omnimarket_and_infra_for_core_and_spi() -> None:
    overlay = yaml.safe_load((OVERLAY).read_text(encoding="utf-8"))
    assert {c["name"] for c in overlay["consumers"]} == {"omnimarket", "omnibase_infra"}
    by_candidate = {
        c["distribution"]: set(c["consumers"]) for c in overlay["candidates"]
    }
    assert by_candidate == {
        "omnibase-core": {"omnimarket", "omnibase_infra"},
        "omnibase-spi": {"omnimarket", "omnibase_infra"},
    }
    assert all(c["ref"] == "dev" for c in overlay["consumers"])


def test_ac1_ci_calls_the_reusable_workflow_for_core_and_the_reusable_builds_and_runs_the_node() -> (
    None
):
    call = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"][
        "consumer-install-check"
    ]
    assert call["uses"] == "./.github/workflows/consumer-install-check.yml"
    assert call["with"]["candidate-distribution"] == "omnibase-core"
    steps = yaml.safe_load(REUSABLE.read_text(encoding="utf-8"))["jobs"][
        "consumer-install-check"
    ]["steps"]
    text = " ".join(str(s.get("run", "")) for s in steps)
    assert "uv build --wheel" in text
    assert (
        "omnibase_core.nodes.node_consumer_install_check_effect.runtime_consumer_install_check"
        in text
    )
    assert "node_consumer_install_check_effect.overlay.yaml" in text


def test_ac1_the_consumers_own_smoke_script_runs_by_path_and_is_not_copied(
    tmp_path: Path,
) -> None:
    _, runner = _check(_request(tmp_path, _overlay(tmp_path)))
    smoke = [argv for argv, _ in runner.calls if argv[-1].endswith("tests/ci/smoke.py")]
    assert len(smoke) == 1 and "/alpha/src/" in smoke[0][-1]


def test_ac2_a_smoke_failure_names_consumer_import_and_missing_name(
    tmp_path: Path,
) -> None:
    smoke_output = (
        f"LATEST-CORE-SMOKE FAIL node=node_create_ticket module=omnimarket.nodes.node_create_ticket.core_ticket_guard "
        f"symbol={REMOVED_MODULE} at=src/omnimarket/core_ticket_guard.py:12 "
        f"error=ModuleNotFoundError: No module named '{REMOVED_MODULE}'\n"
        "LATEST-CORE-SMOKE packages=3 modules_tried=9 failed=1\n"
    )
    result, _ = _check(
        _request(tmp_path, _overlay(tmp_path)), smoke_output=smoke_output
    )
    assert result.passed is False
    (line,) = result.failure_lines
    assert "consumer=alpha" in line and f"missing={REMOVED_MODULE}" in line
    assert "core_ticket_guard.py:12" in line


def test_ac2_a_failure_names_consumer_import_and_missing_name(tmp_path: Path) -> None:
    failure = {
        "group": "onex.nodes",
        "name": "node_create_ticket",
        "value": "x.y",
        "error_type": "ModuleNotFoundError",
        "message": f"No module named '{REMOVED_MODULE}'",
        "missing_name": REMOVED_MODULE,
        "import_statement": f"{REMOVED_IMPORT} (src/x/core_ticket_guard.py:12)",
        "frame_files": [
            "/venv/lib/python3.12/site-packages/omnibase_core/cli/__init__.py"
        ],
    }
    result, _ = _check(_request(tmp_path, _overlay(tmp_path)), {"alpha": [failure]})
    assert result.passed is False
    (line,) = result.failure_lines
    assert "consumer=alpha" in line
    assert REMOVED_IMPORT in line
    assert f"missing={REMOVED_MODULE}" in line


def test_ac2_a_collection_error_names_consumer_import_and_missing_name() -> None:
    output = textwrap.dedent(
        """\
        ==================================== ERRORS ====================================
        ________________ ERROR collecting tests/unit/test_guard.py _________________
        tests/unit/test_guard.py:3: in <module>
            from cand_pkg.removed import gone_name
        E   ModuleNotFoundError: No module named 'cand_pkg.removed'
        =========================== short test summary info ============================
        ERROR tests/unit/test_guard.py
        7 tests collected, 1 error in 0.40s
        """
    )
    count, findings = parse_collection_output("alpha", output, ("cand_pkg",))
    assert count == 7
    (finding,) = findings
    assert finding.consumer == "alpha"
    assert "from cand_pkg.removed import gone_name" in finding.import_statement
    assert finding.missing_name == "cand_pkg.removed"
    assert finding.attributed_to_candidate is True


def _fake_dist(site: Path, name: str, entry_points: dict[str, str]) -> None:
    info = site / f"{name.replace('-', '_')}-1.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n", encoding="utf-8"
    )
    body = "[onex.nodes]\n" + "".join(f"{k} = {v}\n" for k, v in entry_points.items())
    (info / "entry_points.txt").write_text(body, encoding="utf-8")


def _run_probe(
    site: Path, dist: str, out: Path, skip_groups: tuple[str, ...] = ()
) -> dict[str, object]:
    env = {"PYTHONPATH": str(site)}
    done = subprocess.run(
        [
            sys.executable,
            "-P",
            str(NODE_DIR / "runtime_entry_point_probe.py"),
            "--distribution",
            dist,
            "--out",
            str(out),
            *[a for g in skip_groups for a in ("--skip-group", g)],
        ],
        env=env,
        cwd=site,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(out.read_text(encoding="utf-8"))


def _replay_site(tmp_path: Path, *, candidate_has_module: bool) -> Path:
    """A consumer whose guard imports the module 0.47.77 removed, over a stand-in core."""
    site = tmp_path / "site"
    (site / "omnibase_core" / "cli").mkdir(parents=True)
    (site / "omnibase_core" / "__init__.py").write_text("", encoding="utf-8")
    (site / "omnibase_core" / "cli" / "__init__.py").write_text("", encoding="utf-8")
    if candidate_has_module:  # 0.47.76 shape
        (site / "omnibase_core" / "cli" / "cli_work_ledger_render.py").write_text(
            'MD_LEDGER_PATH_ENV = "STAND_IN_VALUE"\n', encoding="utf-8"
        )
    (site / "market_pkg").mkdir()
    (site / "market_pkg" / "__init__.py").write_text("", encoding="utf-8")
    (site / "market_pkg" / "core_ticket_guard.py").write_text(
        f"{REMOVED_IMPORT}\n", encoding="utf-8"
    )
    _fake_dist(
        site, "market-dist", {"node_create_ticket": "market_pkg.core_ticket_guard"}
    )
    return site


def test_ac2_the_probe_names_import_line_and_missing_module(tmp_path: Path) -> None:
    site = _replay_site(tmp_path, candidate_has_module=False)
    result = _run_probe(site, "market-dist", tmp_path / "probe.json")
    (failure,) = result["failures"]
    assert failure["missing_name"] == REMOVED_MODULE
    assert REMOVED_IMPORT in failure["import_statement"]
    assert "core_ticket_guard.py:1" in failure["import_statement"]
    assert failure["group"] == "onex.nodes" and failure["name"] == "node_create_ticket"


def test_ac2_the_probe_names_a_removed_symbol_of_a_module_that_remains(
    tmp_path: Path,
) -> None:
    site = _replay_site(tmp_path, candidate_has_module=True)
    (site / "omnibase_core" / "cli" / "cli_work_ledger_render.py").write_text(
        "OTHER = 1\n", encoding="utf-8"
    )
    result = _run_probe(site, "market-dist", tmp_path / "probe.json")
    (failure,) = result["failures"]
    assert failure["missing_name"] == f"{REMOVED_MODULE}.MD_LEDGER_PATH_ENV"


def test_ac3_replay_of_0_47_77_fails_naming_all_three_and_the_fixed_build_passes(
    tmp_path: Path,
) -> None:
    """0.47.77 deleted omnibase_core.cli.cli_work_ledger_render; omnimarket's guard imported it."""
    broken = _run_probe(
        _replay_site(tmp_path / "a", candidate_has_module=False),
        "market-dist",
        tmp_path / "a.json",
    )
    (failure,) = broken["failures"]
    result, _ = _check(_request(tmp_path, _overlay(tmp_path)), {"alpha": [failure]})
    assert result.passed is False
    (line,) = result.failure_lines
    assert (
        "consumer=alpha" in line and REMOVED_IMPORT in line and REMOVED_MODULE in line
    )

    fixed = _run_probe(
        _replay_site(tmp_path / "b", candidate_has_module=True),
        "market-dist",
        tmp_path / "b.json",
    )
    assert fixed["failures"] == []
    ok, _ = _check(_request(tmp_path / "again", _overlay(tmp_path)))
    assert ok.passed is True


def test_ac3_a_failure_that_does_not_touch_the_candidate_is_reported_not_failed(
    tmp_path: Path,
) -> None:
    failure = {
        "group": "onex.cli",
        "name": "x",
        "value": "x:y",
        "error_type": "ModuleNotFoundError",
        "message": "No module named 'unrelated_dep'",
        "missing_name": "unrelated_dep",
        "import_statement": "import unrelated_dep (x.py:1)",
        "frame_files": ["/consumer/x.py"],
    }
    result, _ = _check(_request(tmp_path, _overlay(tmp_path)), {"alpha": [failure]})
    assert result.passed is True
    assert result.outcomes[0].findings[0].attributed_to_candidate is False


def test_ac4_the_bound_comes_from_the_overlay_and_an_overrun_is_flagged(
    tmp_path: Path,
) -> None:
    result, _ = _check(_request(tmp_path, _overlay(tmp_path, budget=1e-9)))
    assert result.budget_seconds == 1e-9
    assert result.over_budget is True
    shipped = yaml.safe_load((OVERLAY).read_text(encoding="utf-8"))
    assert shipped["total_budget_seconds"] <= 300


def test_ac4_the_ci_job_does_not_run_for_a_docs_only_change() -> None:
    call = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"][
        "consumer-install-check"
    ]
    assert call["with"]["docs-only"] == "${{ needs.zone-filter.outputs.docs_only }}"
    steps = yaml.safe_load(REUSABLE.read_text(encoding="utf-8"))["jobs"][
        "consumer-install-check"
    ]["steps"]
    heavy = [s for s in steps if "Docs-only" not in s["name"]]
    assert heavy and all("inputs.docs-only != 'true'" in s["if"] for s in heavy)


def test_ac1_the_cli_exits_nonzero_and_prints_the_failure_for_a_broken_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    failure = {
        "group": "g",
        "name": "n",
        "value": "v",
        "error_type": "ModuleNotFoundError",
        "message": "m",
        "missing_name": REMOVED_MODULE,
        "import_statement": f"{REMOVED_IMPORT} (a.py:1)",
        "frame_files": [],
    }
    container = build_container(
        command_handler=cast("type[HandlerSubprocessExec]", _FakeRunner)
    )
    fake = cast(
        "_FakeRunner",
        container.get_service(HandlerSubprocessExec),
    )
    fake.failures = {"beta": [failure]}
    code = main(
        [
            "--candidate-distribution",
            "cand-dist",
            "--candidate-spec",
            "/dist/x.whl",
            "--overlay",
            str(_overlay(tmp_path)),
            "--work-dir",
            str(tmp_path / "w"),
            "--report",
            str(tmp_path / "report.json"),
        ],
        container=container,
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "consumer=beta" in err and REMOVED_MODULE in err
    assert (
        json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["passed"]
        is False
    )


def test_probe_module_is_stdlib_only() -> None:
    source = Path(runtime_entry_point_probe.__file__).read_text(encoding="utf-8")
    assert "omnibase_core" not in source.replace("omnibase_core.cli", "")


def test_ac1_the_overlay_index_names_the_overlay_file_the_ci_passes() -> None:
    index = yaml.safe_load(
        (REPO_ROOT / "config/onex/overlay_index.yaml").read_text(encoding="utf-8")
    )
    relative = index["overlays"]["node_consumer_install_check_effect"]
    assert (REPO_ROOT / "config/onex" / relative) == OVERLAY and OVERLAY.is_file()
    assert relative in REUSABLE.read_text(encoding="utf-8")


def test_ac2_a_smoke_line_without_a_location_still_names_all_three(
    tmp_path: Path,
) -> None:
    """The smoke script of omnimarket at 2026-11-23 printed no at= field."""
    smoke_output = (
        "LATEST-CORE-SMOKE FAIL node=node_create_ticket "
        "module=omnimarket.nodes.node_create_ticket.handlers.core_ticket_guard "
        f"symbol={REMOVED_MODULE} error=ModuleNotFoundError: No module named '{REMOVED_MODULE}'\n"
        "LATEST-CORE-SMOKE packages=1460 modules_tried=11357 failed=1\n"
    )
    result, _ = _check(
        _request(tmp_path, _overlay(tmp_path)), smoke_output=smoke_output
    )
    (line,) = result.failure_lines
    assert "consumer=alpha" in line and f"missing={REMOVED_MODULE}" in line
    assert "core_ticket_guard" in line
    assert result.outcomes[0].smoke_summary.endswith("failed=1")


def _help_metadata_site(tmp_path: Path) -> Path:
    """A consumer whose onex.cli.help group holds help text (OMN-26615), not module paths."""
    site = _replay_site(tmp_path, candidate_has_module=True)
    entry_points = site / "market_dist-1.0.dist-info" / "entry_points.txt"
    entry_points.write_text(
        entry_points.read_text(encoding="utf-8")
        + "\n[onex.cli.help]\nagent-message = Send a message to an agent\n",
        encoding="utf-8",
    )
    return site


def test_ac1_a_declared_metadata_group_is_not_imported_and_an_importable_group_still_is(
    tmp_path: Path,
) -> None:
    site = _help_metadata_site(tmp_path)
    # Known bad: the group is not declared metadata, so its help text is loaded and fails.
    bad = _run_probe(site, "market-dist", tmp_path / "bad.json")
    assert [f["group"] for f in bad["failures"]] == ["onex.cli.help"]
    # Known good: the overlay declares it metadata; nothing else is skipped.
    good = _run_probe(
        site, "market-dist", tmp_path / "good.json", skip_groups=("onex.cli.help",)
    )
    assert good["failures"] == [] and good["imported"] == 1
    # The skip names a group, never a distribution: a broken onex.nodes entry still fails.
    broken = _run_probe(
        _replay_site(tmp_path / "b", candidate_has_module=False),
        "market-dist",
        tmp_path / "broken.json",
        skip_groups=("onex.cli.help",),
    )
    assert len(broken["failures"]) == 1
