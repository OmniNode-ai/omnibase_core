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

from omnibase_core.nodes.node_direct_model_call_check_compute import (
    HandlerDirectModelCallCompute,
    ModelDirectModelCallBaselineEntry,
    ModelDirectModelCallFinding,
    ModelDirectModelCallScanInput,
    ModelDirectModelCallSourceFile,
)
from omnibase_core.nodes.node_direct_model_call_check_compute.handler import (
    added_entries,
    compare_with_baseline,
    is_sanctioned,
)
from omnibase_core.nodes.node_direct_model_call_check_compute.runtime_direct_model_call import (
    load_policy,
    main,
)

pytestmark = pytest.mark.unit

SAMPLES = Path(__file__).parent / "samples"


def _source(name: str, path: str | None = None) -> ModelDirectModelCallSourceFile:
    text = (SAMPLES / f"{name}.txt").read_text("utf-8")
    return ModelDirectModelCallSourceFile(path=path or name, content=text)


def _scan(
    *files: ModelDirectModelCallSourceFile, repo: str = "omnimarket"
) -> tuple[ModelDirectModelCallFinding, ...]:
    handler = HandlerDirectModelCallCompute(load_policy())
    return handler.handle(ModelDirectModelCallScanInput(repo=repo, files=files))


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
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_cli_refuses_planted_sample_and_accepts_clean(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "clean.py").write_text((SAMPLES / "clean.py.txt").read_text("utf-8"))
    _git(tmp_path, "add", "clean.py")
    assert main(["--repo", "omnimarket", "--repo-root", str(tmp_path)]) == 0
    (tmp_path / "s5g.py").write_text((SAMPLES / "s5g.py.txt").read_text("utf-8"))
    _git(tmp_path, "add", "s5g.py")
    assert main(["--repo", "omnimarket", "--repo-root", str(tmp_path)]) == 1
