# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the canonical-file-shape ratchet (OMN-20304).

Marker strings are assembled at runtime, so this file carries no suppression
comment of its own.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.validators.canonical_file_shape import (
    DEFAULT_BASELINE,
    INDEX,
    GitRepo,
    check,
    count_suppressions,
    declared_gate_baselines,
    is_canonical_location,
    is_code_file,
    main,
    render_baseline,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

NOQA = "# " + "no" + "qa"
FALLBACK_MARK = "# fallback" + "-ok: reason"
IMPERATIVE_MARK = "# imperative" + "-ok"


IDENTITY = ("-c", "user.name=t", "-c", "user.email=t@example.com")


def _env() -> dict[str, str]:
    return scrub_git_location_env()


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *IDENTITY, *args],
        cwd=repo,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "dev")
    _write(tmp_path, "scripts/old_tool.py", "print('old')\n")
    _write(tmp_path, "src/pkg/nodes/node_x/handler.py", "X = 1\n")
    _write(tmp_path, DEFAULT_BASELINE, render_baseline(["scripts/old_tool.py"]))
    _write(tmp_path, "config/topic_allowlist.yaml", "- a\n- b\n")
    _write(tmp_path, "plugins/p/skills/s/SKILL.md", "Dispatch via onex run-node.\n")
    _write(tmp_path, "src/pkg/nodes/node_x/legacy.py", f"y = 1  {NOQA}\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _rules(repo: Path) -> list[str]:
    git = GitRepo(root=repo, env=_env())
    return sorted(f.rule for f in check(git, INDEX, "HEAD"))


def _stage(repo: Path) -> None:
    _git(repo, "add", "-A")


@pytest.mark.parametrize(
    "path",
    [
        "src/pkg/nodes/node_a/handler.py",
        "src/pkg/handlers/handler_a.py",
        "src/pkg/models/model_a.py",
        "src/pkg/protocols/protocol_a.py",
        "src/pkg/contracts/c.py",
        "src/pkg/enums/enum_a.py",
        "tests/unit/test_a.py",
        "src/pkg/tests/test_a.py",
        "docs/examples/a.py",
        "conftest.py",
    ],
)
def test_canonical_locations(path: str) -> None:
    assert is_canonical_location(path)


@pytest.mark.parametrize(
    "path",
    [
        "scripts/a.py",
        "plugins/onex/skills/s/run.py",
        "tools/a.sh",
        "bin/a",
        "src/pkg/runtime/a.py",
        "src/pkg/a.py",
        ".github/scripts/a.py",
    ],
)
def test_noncanonical_locations(path: str) -> None:
    assert not is_canonical_location(path)


def test_code_file_detection() -> None:
    assert is_code_file("a.py", None)
    assert is_code_file("bin/run", b"#!/bin/sh\n")
    assert not is_code_file("Makefile", b"all:\n")
    assert not is_code_file("README.md", None)


def test_clean_tree_passes(repo: Path) -> None:
    _write(repo, "src/pkg/nodes/node_y/handler.py", "Y = 2\n")
    _write(repo, "tests/test_y.py", "def test_y() -> None: ...\n")
    _stage(repo)
    assert _rules(repo) == []


@pytest.mark.parametrize(
    "path",
    [
        "scripts/new_tool.py",
        "plugins/p/skills/s/helper.py",
        "tools/run.sh",
        "src/pkg/runtime/thing.py",
    ],
)
def test_new_noncanonical_file_refused(repo: Path, path: str) -> None:
    _write(repo, path, "x = 1\n")
    _stage(repo)
    assert _rules(repo) == ["noncanonical-file"]


def test_new_shebang_script_without_extension_refused(repo: Path) -> None:
    _write(repo, "bin/tool", "#!/usr/bin/env bash\necho hi\n")
    _stage(repo)
    assert _rules(repo) == ["noncanonical-file"]


def test_baseline_growth_refused(repo: Path) -> None:
    _write(repo, "scripts/new_tool.py", "x = 1\n")
    _write(
        repo,
        DEFAULT_BASELINE,
        render_baseline(["scripts/old_tool.py", "scripts/new_tool.py"]),
    )
    _stage(repo)
    assert _rules(repo) == ["baseline-growth"]


def test_baseline_stale_entry_refused(repo: Path) -> None:
    (repo / "scripts/old_tool.py").unlink()
    _stage(repo)
    assert _rules(repo) == ["baseline-stale"]


def test_baseline_shrink_accepted(repo: Path) -> None:
    (repo / "scripts/old_tool.py").unlink()
    _write(repo, DEFAULT_BASELINE, render_baseline([]))
    _stage(repo)
    assert _rules(repo) == []


BODY = "".join(f"line_{i} = {i}\n" for i in range(20))


def _baselined_tool(repo: Path) -> None:
    """Commit a larger baselined file so a rename survives an edit."""
    _write(repo, "plugins/p/_bin/tool.sh", "#!/bin/sh\n" + BODY)
    _write(
        repo,
        DEFAULT_BASELINE,
        render_baseline(["scripts/old_tool.py", "plugins/p/_bin/tool.sh"]),
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "tool")


def _rename(repo: Path, new: str, extra: str = "") -> None:
    (repo / new).parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "mv", "plugins/p/_bin/tool.sh", new)
    if extra:
        with (repo / new).open("a", encoding="utf-8") as fh:
            fh.write(extra)


NEW_TOOL = "plugins/p/_bin/renamed.sh"
SWAPPED = ["scripts/old_tool.py", NEW_TOOL]


def test_rename_swap_accepted(repo: Path) -> None:
    _baselined_tool(repo)
    _rename(repo, NEW_TOOL)
    _write(repo, DEFAULT_BASELINE, render_baseline(SWAPPED))
    _stage(repo)
    assert _rules(repo) == []


def test_rename_baseline_untouched_accepted(repo: Path) -> None:
    _baselined_tool(repo)
    _rename(repo, NEW_TOOL)
    _stage(repo)
    assert _rules(repo) == []


def test_rename_with_edit_accepted(repo: Path) -> None:
    _baselined_tool(repo)
    _rename(repo, NEW_TOOL, "added = 1\n")
    _write(repo, DEFAULT_BASELINE, render_baseline(SWAPPED))
    _stage(repo)
    assert _rules(repo) == []


def test_rename_of_unbaselined_file_refused(repo: Path) -> None:
    _write(repo, "plugins/p/_bin/free.sh", "#!/bin/sh\n" + BODY)
    _stage(repo)
    _git(repo, "commit", "-q", "-m", "unbaselined")
    _git(repo, "mv", "plugins/p/_bin/free.sh", NEW_TOOL)
    _stage(repo)
    assert "noncanonical-file" in _rules(repo)


def test_rename_plus_extra_script_refused(repo: Path) -> None:
    _baselined_tool(repo)
    _rename(repo, NEW_TOOL)
    _write(repo, "scripts/extra.py", "x = 1\n")
    _write(repo, DEFAULT_BASELINE, render_baseline(SWAPPED))
    _stage(repo)
    assert _rules(repo) == ["noncanonical-file"]


def test_swap_without_detected_rename_refused(repo: Path) -> None:
    _baselined_tool(repo)
    (repo / "plugins/p/_bin/tool.sh").unlink()
    _write(repo, NEW_TOOL, "#!/bin/sh\necho unrelated\n")
    _write(repo, DEFAULT_BASELINE, render_baseline(SWAPPED))
    _stage(repo)
    assert _rules(repo) == ["baseline-growth"]


def test_rename_keeping_old_entry_and_adding_new_refused(repo: Path) -> None:
    _baselined_tool(repo)
    _rename(repo, NEW_TOOL)
    _write(
        repo,
        DEFAULT_BASELINE,
        render_baseline([*SWAPPED, "plugins/p/_bin/tool.sh"]),
    )
    _stage(repo)
    assert "baseline-growth" in _rules(repo)


def test_skill_imperative_growth_refused(repo: Path) -> None:
    _write(
        repo,
        "plugins/p/skills/s/SKILL.md",
        f"Dispatch via onex run-node.\nThen run gh api repos/x  {IMPERATIVE_MARK}\n",
    )
    _stage(repo)
    assert _rules(repo) == ["skill-imperative"]


def test_new_skill_with_imperative_line_refused(repo: Path) -> None:
    _write(repo, "plugins/p/skills/t/SKILL.md", "Run: curl http://example.com/x\n")
    _stage(repo)
    assert _rules(repo) == ["skill-imperative"]


def test_new_exception_file_refused(repo: Path) -> None:
    _write(repo, ".onex_ratchets/foo_waivers.yaml", "- x\n")
    _stage(repo)
    assert _rules(repo) == ["new-exception-file"]


GATE_BASELINE = ".onex_ratchets/direct_model_call_baseline.yaml"


def _gate_config(
    baseline: str, url: str = "https://github.com/OmniNode-ai/omnibase_core"
) -> str:
    return (
        "repos:\n"
        f"  - repo: {url}\n"
        "    rev: abc\n"
        "    hooks:\n"
        "      - id: check-direct-model-call\n"
        f"        args: [--repo, r, --baseline, {baseline}, --base, HEAD]\n"
    )


def test_gate_declared_baseline_accepted(repo: Path) -> None:
    _write(repo, ".pre-commit-config.yaml", _gate_config(GATE_BASELINE))
    _write(repo, GATE_BASELINE, "entries:\n  - a\n  - b\n")
    _stage(repo)
    assert _rules(repo) == []


def test_gate_declared_baseline_only_shrinks_by_gate(repo: Path) -> None:
    _write(repo, ".pre-commit-config.yaml", _gate_config(GATE_BASELINE))
    _write(repo, GATE_BASELINE, "entries:\n  - a\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "gate")
    _write(repo, GATE_BASELINE, "entries:\n  - a\n  - b\n")
    _stage(repo)
    assert _rules(repo) == []


def test_undeclared_baseline_still_refused(repo: Path) -> None:
    _write(repo, ".pre-commit-config.yaml", _gate_config(GATE_BASELINE))
    _write(repo, ".onex_ratchets/other_baseline.yaml", "entries:\n  - a\n")
    _stage(repo)
    assert _rules(repo) == ["new-exception-file"]


def test_baseline_without_any_declaration_refused(repo: Path) -> None:
    _write(repo, GATE_BASELINE, "entries:\n  - a\n")
    _stage(repo)
    assert _rules(repo) == ["new-exception-file"]


def test_declaration_by_a_local_hook_does_not_count(repo: Path) -> None:
    _write(
        repo,
        ".pre-commit-config.yaml",
        _gate_config(GATE_BASELINE, url="local"),
    )
    _write(repo, GATE_BASELINE, "entries:\n  - a\n")
    _stage(repo)
    assert _rules(repo) == ["new-exception-file"]


def test_declared_gate_baselines_forms() -> None:
    assert declared_gate_baselines(None) == frozenset()
    assert declared_gate_baselines("not: [valid") == frozenset()
    text = (
        "repos:\n"
        "  - repo: https://github.com/OmniNode-ai/omnibase_core\n"
        "    hooks:\n"
        "      - id: check-direct-model-call\n"
        "        args: ['--baseline=x/y.yaml']\n"
        "      - id: canonical-file-shape\n"
        "        args: [--baseline, z.txt]\n"
    )
    assert declared_gate_baselines(text) == frozenset({"x/y.yaml"})


def test_exception_entry_growth_refused(repo: Path) -> None:
    _write(repo, "config/topic_allowlist.yaml", "- a\n- b\n- c\n")
    _stage(repo)
    assert _rules(repo) == ["exception-entry-growth"]


def test_exception_entry_shrink_accepted(repo: Path) -> None:
    _write(repo, "config/topic_allowlist.yaml", "- a\n")
    _stage(repo)
    assert _rules(repo) == []


def test_suppression_growth_refused(repo: Path) -> None:
    _write(repo, "src/pkg/nodes/node_x/handler.py", f"X = 1\nZ = 2  {FALLBACK_MARK}\n")
    _stage(repo)
    assert _rules(repo) == ["suppression-growth"]


def test_suppression_kept_count_accepted(repo: Path) -> None:
    _write(repo, "src/pkg/nodes/node_x/legacy.py", f"y = 2  {NOQA}\n")
    _stage(repo)
    assert _rules(repo) == []


def test_suppression_counter() -> None:
    assert count_suppressions(f"a = 1  {NOQA}\nb = 2  {FALLBACK_MARK}\n") == 2
    assert count_suppressions("plain = 'noqa as a word'\n") == 0


def test_validator_source_carries_no_suppression() -> None:
    import omnibase_core.validators.canonical_file_shape as module

    assert count_suppressions(Path(module.__file__).read_text(encoding="utf-8")) == 0
    assert count_suppressions(Path(__file__).read_text(encoding="utf-8")) == 0


def test_main_exit_codes_and_explicit_revisions(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert main([], repo_root=repo, env=_env()) == 0
    _write(repo, "src/pkg/nodes/node_x/legacy.py", f"y = 1  {NOQA}\nz = 2  {NOQA}\n")
    _stage(repo)
    _git(repo, "commit", "-q", "-m", "bad")

    assert main([], repo_root=repo, env=_env()) == 0
    assert main(["--base", base, "--head", "HEAD"], repo_root=repo, env=_env()) == 1
    assert "suppression-growth" in capsys.readouterr().err


def test_write_baseline_refused_when_present(repo: Path) -> None:
    assert main(["--write-baseline"], repo_root=repo, env=_env()) == 1
