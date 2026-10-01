# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Positive control for check-direct-model-call (OMN-20295).

The planted samples are the gates-and-delegation readiness audit's S5a (an
HTTP call to a chat-completions endpoint), S5c (a shell-out to crush), S5g
(the S5a call with no literal URL) and S6 (the lab crush runner's shape), plus
a cross-file caller, the shell exec of ``claude -p`` and ``llama-cli``, and a
clean sample the gate must accept. Each sample must be refused; the clean one
must not.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest

from omnibase_core.enums.enum_direct_model_call_kind import EnumDirectModelCallKind
from omnibase_core.models.nodes.direct_model_call_check import (
    ModelDirectModelCallBaselineEntry,
    ModelDirectModelCallCheckInput,
    ModelDirectModelCallFinding,
    ModelDirectModelCallSourceFile,
)
from omnibase_core.nodes.node_direct_model_call_check_compute import (
    HandlerDirectModelCallCompute,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._baseline import (
    added_entries,
    compare_with_baseline,
)
from omnibase_core.nodes.node_direct_model_call_check_compute._policy_patterns import (
    is_sanctioned,
)
from omnibase_core.nodes.node_direct_model_call_check_effect.handler import (
    HandlerDirectModelCallCheckEffect,
)
from omnibase_core.nodes.node_direct_model_call_check_effect.runtime_direct_model_call import (
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

load_policy = HandlerDirectModelCallCheckEffect.load_policy

SAMPLES = Path(__file__).parent / "samples"


def _source(name: str, path: str | None = None) -> ModelDirectModelCallSourceFile:
    text = (SAMPLES / f"{name}.txt").read_text("utf-8")
    return ModelDirectModelCallSourceFile(path=path or name, content=text)


def _scan(
    *files: ModelDirectModelCallSourceFile, repo: str = "omnimarket"
) -> tuple[ModelDirectModelCallFinding, ...]:
    verdict = HandlerDirectModelCallCompute().handle(
        ModelDirectModelCallCheckInput(
            policy=load_policy(), repo=repo, files=files, today=date(2026, 10, 1)
        )
    )
    return verdict.findings


@pytest.mark.parametrize(
    ("sample", "kind", "target"),
    [
        ("s5a.py", "http", "http"),
        ("s5c.py", "cli_exec", "crush"),
        ("s5g.py", "http", "http"),
        ("s6.py", "cli_exec", "crush"),
        ("s6.py", "http", "http"),
    ],
)
def test_audit_sample_is_refused(sample: str, kind: str, target: str) -> None:
    findings = _scan(_source(sample))
    assert any(f.kind == kind and f.target == target for f in findings), findings


def test_clean_sample_is_accepted() -> None:
    assert _scan(_source("clean.py")) == ()


def test_caller_in_another_file_is_refused() -> None:
    findings = _scan(_source("s5c.py"), _source("caller.py"))
    assert any(
        f.path == "caller.py"
        and f.kind == "call_via"
        and f.target == "s5c.py::run_agent"
        for f in findings
    ), findings


def test_shell_exec_of_print_mode_claude_and_llama_cli_is_refused() -> None:
    findings = _scan(_source("shell_clis.sh"))
    assert {f.target for f in findings if f.kind == "cli_exec"} >= {
        "claude",
        "llama-cli",
    }


def test_sample_inside_a_sanctioned_package_is_accepted() -> None:
    path = "src/omnimarket/nodes/node_llm_delegation_call_effect/handlers/s5a.py"
    assert is_sanctioned(load_policy(), "omnimarket", path)
    assert _scan(_source("s5a.py", path)) == ()


def test_same_sample_in_a_repo_with_no_sanctioned_package_is_refused() -> None:
    path = "src/omnimarket/nodes/node_llm_delegation_call_effect/handlers/s5a.py"
    assert _scan(_source("s5a.py", path), repo="omniclaude")


def test_policy_sanctioned_packages_are_pinned() -> None:
    assert load_policy().sanctioned_packages == {
        "omnimarket": ("src/omnimarket/nodes/node_llm_delegation_call_effect/**",),
        "omnibase_infra": (
            "src/omnibase_infra/nodes/node_llm_inference_effect/**",
            "src/omnibase_infra/nodes/node_llm_completion_effect/**",
        ),
        "omniclaude": (),
        "omniclaude-internal": (),
        "omnibase_internal": (),
    }


def _entry(
    finding: ModelDirectModelCallFinding, ticket: str = "OMN-20290"
) -> ModelDirectModelCallBaselineEntry:
    return ModelDirectModelCallBaselineEntry(
        path=finding.path,
        kind=finding.kind,
        symbol=finding.symbol,
        target=finding.target,
        ticket=ticket,
        expires=date(2099, 1, 1),
    )


def test_baseline_covers_an_existing_site_and_refuses_a_new_one() -> None:
    old = _scan(_source("s5c.py"))
    baseline = [_entry(f) for f in old]
    assert not compare_with_baseline(old, baseline, date(2026, 10, 1)).new
    both = _scan(_source("s5c.py"), _source("s5a.py"))
    new = compare_with_baseline(both, baseline, date(2026, 10, 1)).new
    assert [f.path for f in new] == ["s5a.py"]


def test_baseline_entry_without_its_site_is_stale() -> None:
    baseline = [_entry(f) for f in _scan(_source("s5c.py"))]
    assert compare_with_baseline((), baseline, date(2026, 10, 1)).stale


def test_baseline_growth_against_base_is_refused() -> None:
    base = [_entry(f) for f in _scan(_source("s5c.py"))]
    head = base + [_entry(f) for f in _scan(_source("s5a.py"))]
    assert added_entries(base, head)
    assert not added_entries(head, base)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env=scrub_git_location_env(),
    )


def test_cli_refuses_planted_sample_and_accepts_clean(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "clean.py").write_text((SAMPLES / "clean.py.txt").read_text("utf-8"))
    _git(tmp_path, "add", "clean.py")
    assert main(["--repo", "omnimarket", "--repo-root", str(tmp_path)]) == 0
    (tmp_path / "s5g.py").write_text((SAMPLES / "s5g.py.txt").read_text("utf-8"))
    _git(tmp_path, "add", "s5g.py")
    assert main(["--repo", "omnimarket", "--repo-root", str(tmp_path)]) == 1


def test_ratchet_verdict_refuses_growth_against_base() -> None:
    old = _scan(_source("s5c.py"))
    base = tuple(_entry(f) for f in old)
    files = (_source("s5c.py"), _source("s5a.py"))
    findings = _scan(*files)
    head = tuple(_entry(f) for f in findings)
    verdict = HandlerDirectModelCallCompute().handle(
        ModelDirectModelCallCheckInput(
            policy=load_policy(),
            repo="omnimarket",
            files=files,
            today=date(2026, 10, 1),
            baseline_path="baseline.yaml",
            baseline=head,
            base_ref="origin/dev",
            base_baseline=base,
        )
    )
    assert not verdict.passed
    assert not verdict.new
    assert [e.path for e in verdict.grown] == ["s5a.py"]


def test_finding_kind_is_the_enum() -> None:
    kinds = {f.kind for f in _scan(_source("s5c.py"), _source("caller.py"))}
    assert kinds == {EnumDirectModelCallKind.CLI_EXEC, EnumDirectModelCallKind.CALL_VIA}
