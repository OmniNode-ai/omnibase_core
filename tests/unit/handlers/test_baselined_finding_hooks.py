# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shrink-only baseline contract for check-no-dict-any and check-no-backward-compat.

Both hooks run the same shared baseline handler; every behaviour below is asserted
once per hook (OMN-21501, plan task T2.1 core slice).
"""

from __future__ import annotations

import importlib
import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_FILE = REPO_ROOT / ".pre-commit-hooks.yaml"
BASELINE = ".onex/baselines/hook.yaml"
# Assembled so this fixture is not itself read as a suppression comment.
EXCLUDE_TOKEN = "ONEX_" + "EXCLUDE"


@dataclass(frozen=True)
class Hook:
    hook_id: str
    module: str
    header: str
    finding: str
    other_finding: str
    clean: str


HOOKS = (
    Hook(
        hook_id="check-no-dict-any",
        module="omnibase_core.handlers.handler_dict_any_cli",
        header="from typing import Any\n",
        finding="values: dict[str, Any] = {}",
        other_finding="other: dict[str, Any] = {}",
        clean="values: int = 0",
    ),
    Hook(
        hook_id="check-no-backward-compat",
        module="omnibase_core.handlers.handler_backward_compat_cli",
        header="",
        finding="# kept for backward compatibility with old callers",
        other_finding="# legacy support for the previous release",
        clean="# plain explanatory note",
    ),
)


@pytest.fixture(params=HOOKS, ids=lambda hook: hook.hook_id)
def hook(request: pytest.FixtureRequest) -> Hook:
    result: Hook = request.param
    return result


@pytest.fixture
def run(
    hook: Hook,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> Callable[..., tuple[int, str]]:
    """Run the hook's CLI inside ``tmp_path`` and return (exit code, stdout)."""
    monkeypatch.chdir(tmp_path)
    main = importlib.import_module(hook.module).main

    def _run(*args: str) -> tuple[int, str]:
        capsys.readouterr()
        code = main(list(args))
        return code, capsys.readouterr().out

    return _run


def write(tmp_path: Path, hook: Hook, name: str, *body: str, lead: int = 0) -> Path:
    path = tmp_path / "src" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(hook.header + "\n" * lead + "\n".join(body) + "\n", "utf-8")
    return path


def entries(tmp_path: Path) -> list[dict[str, str]]:
    document = yaml.safe_load((tmp_path / BASELINE).read_text("utf-8"))
    result: list[dict[str, str]] = document["entries"]
    return result


def seed(tmp_path: Path, hook: Hook, run: Callable[..., tuple[int, str]]) -> None:
    """A tree with one baselined finding in src/old.py and a written baseline."""
    write(tmp_path, hook, "old.py", hook.finding)
    code, out = run("--dir", "src", "--baseline", BASELINE, "--write-baseline")
    assert code == 0, out
    assert len(entries(tmp_path)) == 1


def test_a_new_finding_fails_and_names_only_the_new_one(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    seed(tmp_path, hook, run)
    write(tmp_path, hook, "fresh.py", hook.other_finding)
    code, out = run("--dir", "src", "--baseline", BASELINE)
    assert code == 1
    assert "fresh.py" in out
    assert "old.py" not in out


def test_b_baselined_finding_passes(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    seed(tmp_path, hook, run)
    code, out = run("--dir", "src", "--baseline", BASELINE)
    assert code == 0, out


def test_c_removed_finding_is_stale_until_write_baseline_shrinks_it(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    seed(tmp_path, hook, run)
    write(tmp_path, hook, "old.py", hook.clean)
    code, out = run("--dir", "src", "--baseline", BASELINE)
    assert code == 1
    assert "--write-baseline" in out
    assert "old.py" in out
    code, out = run("--dir", "src", "--baseline", BASELINE, "--write-baseline")
    assert code == 0, out
    assert entries(tmp_path) == []
    code, out = run("--dir", "src", "--baseline", BASELINE)
    assert code == 0, out


def test_d_write_baseline_refuses_to_add_an_entry(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    seed(tmp_path, hook, run)
    before = (tmp_path / BASELINE).read_text("utf-8")
    write(tmp_path, hook, "fresh.py", hook.other_finding)
    code, out = run("--dir", "src", "--baseline", BASELINE, "--write-baseline")
    assert code == 1
    assert "fresh.py" in out
    assert (tmp_path / BASELINE).read_text("utf-8") == before


def test_e_second_identical_finding_fails_and_a_moved_finding_passes(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    seed(tmp_path, hook, run)
    write(tmp_path, hook, "old.py", hook.finding, lead=7)
    code, out = run("--dir", "src", "--baseline", BASELINE)
    assert code == 0, out
    write(tmp_path, hook, "old.py", hook.finding, hook.finding, lead=7)
    code, out = run("--dir", "src", "--baseline", BASELINE)
    assert code == 1
    assert "old.py" in out


def test_without_baseline_every_finding_fails(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    write(tmp_path, hook, "old.py", hook.finding)
    write(tmp_path, hook, "fresh.py", hook.other_finding)
    code, out = run("--dir", "src")
    assert code == 1
    assert "old.py" in out
    assert "fresh.py" in out
    write(tmp_path, hook, "old.py", hook.clean)
    write(tmp_path, hook, "fresh.py", hook.clean)
    code, out = run("--dir", "src")
    assert code == 0, out


def test_write_baseline_creates_an_absent_file_with_the_documented_document(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    write(tmp_path, hook, "old.py", hook.finding)
    assert not (tmp_path / BASELINE).exists()
    code, out = run("--dir", "src", "--baseline", BASELINE, "--write-baseline")
    assert code == 0, out
    document = yaml.safe_load((tmp_path / BASELINE).read_text("utf-8"))
    assert document["schema_version"] == 1
    assert document["hook"] == hook.hook_id
    (entry,) = document["entries"]
    assert set(entry) == {"path", "rule", "text"}
    assert entry["path"] == "src/old.py"
    assert entry["text"] == hook.finding


def test_baseline_of_another_hook_is_refused(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    seed(tmp_path, hook, run)
    document = yaml.safe_load((tmp_path / BASELINE).read_text("utf-8"))
    document["hook"] = "check-something-else"
    (tmp_path / BASELINE).write_text(yaml.safe_dump(document), "utf-8")
    code, out = run("--dir", "src", "--baseline", BASELINE)
    assert code == 1
    assert "check-something-else" in out


def test_baseline_with_an_unknown_field_is_refused(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    seed(tmp_path, hook, run)
    document = yaml.safe_load((tmp_path / BASELINE).read_text("utf-8"))
    document["surprise"] = True
    (tmp_path / BASELINE).write_text(yaml.safe_dump(document), "utf-8")
    code, _ = run("--dir", "src", "--baseline", BASELINE)
    assert code == 1


def test_file_mode_honours_the_baseline_and_judges_staleness_for_passed_files_only(
    hook: Hook, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    write(tmp_path, hook, "a.py", hook.finding)
    write(tmp_path, hook, "b.py", hook.other_finding)
    code, out = run("--dir", "src", "--baseline", BASELINE, "--write-baseline")
    assert code == 0, out
    assert len(entries(tmp_path)) == 2
    write(tmp_path, hook, "b.py", hook.clean)
    code, out = run("src/a.py", "--baseline", BASELINE)
    assert code == 0, out
    code, out = run("src/b.py", "--baseline", BASELINE)
    assert code == 1
    assert "--write-baseline" in out
    code, out = run("src/b.py", "--baseline", BASELINE, "--write-baseline")
    assert code == 0, out
    assert [entry["path"] for entry in entries(tmp_path)] == ["src/a.py"]
    write(tmp_path, hook, "c.py", hook.finding)
    code, out = run("src/c.py", "--baseline", BASELINE)
    assert code == 1
    assert "c.py" in out


def test_dict_any_decorator_and_comment_exemptions_still_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from omnibase_core.handlers.handler_dict_any_cli import main

    monkeypatch.chdir(tmp_path)
    source = tmp_path / "src" / "exempt.py"
    source.parent.mkdir()
    source.write_text(
        "from typing import Any\n"
        "def allow_dict_any(fn): return fn\n"
        "def allow_dict_str_any(reason): return lambda fn: fn\n"
        "\n"
        "@allow_dict_any\n"
        "def plain(x: dict[str, Any]) -> None: ...\n"
        "\n"
        '@allow_dict_str_any("wire payload")\n'
        "class Wire:\n"
        "    value: dict[str, Any]\n"
        "\n"
        f"# {EXCLUDE_TOKEN}: dict_str_any\n"
        "def excluded(x: dict[str, Any]) -> None: ...\n",
        "utf-8",
    )
    assert main(["--dir", "src"]) == 0, capsys.readouterr().out
    source.write_text(
        source.read_text("utf-8")
        + "\n" * 8
        + "def bare(x: dict[str, Any]) -> None: ...\n",
        "utf-8",
    )
    assert main(["--dir", "src"]) == 1


def test_dict_any_skips_the_path_classes_the_rule_data_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from omnibase_core.handlers.handler_dict_any_cli import main

    monkeypatch.chdir(tmp_path)
    skipped = tmp_path / "src" / "pkg" / "types" / "aliases.py"
    skipped.parent.mkdir(parents=True)
    skipped.write_text("from typing import Any\nx: dict[str, Any] = {}\n", "utf-8")
    assert main(["--dir", "src"]) == 0, capsys.readouterr().out


def test_g_manifest_declares_both_hook_ids_with_a_self_contained_entry() -> None:
    raw = yaml.safe_load(HOOKS_FILE.read_text("utf-8"))
    by_id = {entry["id"]: entry for entry in raw}
    for hook in HOOKS:
        assert hook.hook_id in by_id, f"{hook.hook_id} missing from the manifest"
        entry = by_id[hook.hook_id]
        # language: python builds its own environment from the checked-out hook
        # repo; a script entry or a system entry would lean on core's dev venv.
        assert entry["language"] == "python"
        assert entry["entry"] == f"python -m {hook.module}"
        assert importlib.util.find_spec(hook.module) is not None
    assert by_id["check-no-backward-compat"]["args"] == ["--dir", "src/"]
    assert by_id["check-no-dict-any"]["pass_filenames"] is True
