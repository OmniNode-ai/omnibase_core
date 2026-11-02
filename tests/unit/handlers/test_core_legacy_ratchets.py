# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Slice A: a staged finding cannot hide below a whole-tree allowance."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[3]
RUNTIME = "omnibase_core.nodes.node_finding_baseline_check_effect.runtime_legacy_ratchet_check"

CASES = (
    (
        "substrate-silent-except-pass",
        "try:\n    int('x')\nexcept ValueError:\n    pass\n",
    ),
    ("substrate-env-silent-fallback", "import os\nx = os.getenv('X', 'fallback')\n"),
    (
        "substrate-identity-field-optionality",
        "from pydantic import BaseModel\nclass M(BaseModel):\n    session_id: str | None = None\n",
    ),
    (
        "substrate-loose-typing-internal",
        "from pydantic import BaseModel\nfrom typing import Any\nclass M(BaseModel):\n    value: Any\n",
    ),
    (
        "substrate-protocol-kwargs-object",
        "from typing import Protocol\nclass P(Protocol):\n    def f(self, **kwargs: object) -> None: ...\n",
    ),
    (
        "validate-stubbed-functionality",
        "def calculate():\n    raise NotImplementedError('pending')\n",
    ),
    ("validate-model-dump-json-mode", "value.model_dump()\n"),
    (
        "validate-union-usage",
        "from typing import Optional\nvalue: Optional[str] = None\n",
    ),
)


def test_hook_config_has_no_global_allowances_and_pyright_refuses_at_commit() -> None:
    text = (ROOT / ".pre-commit-config.yaml").read_text()
    assert "--max-violations" not in text
    hooks = {
        h["id"]: h
        for repo in yaml.safe_load(text)["repos"]
        for h in repo.get("hooks", [])
    }
    for hook_id, _ in CASES:
        assert "--baseline" in hooks[hook_id]["entry"]
        assert hooks[hook_id]["pass_filenames"] is True
    assert "pre-commit" in hooks["pyright-type-check"]["stages"]
    config = json.loads((ROOT / "pyrightconfig.json").read_text())
    for rule in ("reportReturnType", "reportArgumentType", "reportAssignmentType"):
        assert config[rule] == "error"


@pytest.mark.parametrize(("hook", "source"), CASES)
def test_new_duplicate_and_stale_findings_refused_without_rewriting(
    hook: str,
    source: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main = importlib.import_module(RUNTIME).main
    monkeypatch.chdir(tmp_path)
    path = Path("src/module.py")
    path.parent.mkdir()
    path.write_text(source)
    baseline = f"{hook}.yaml"
    args = ["--hook", hook, "--baseline", baseline, str(path)]
    assert main(args) == 1
    assert capsys.readouterr().out.count("FAIL:") == 1
    assert main([*args, "--write-baseline"]) == 0
    Path(baseline).write_text(
        "# Burn-down ticket: OMN-22012. Zero target: 2026-11-16.\n"
        + Path(baseline).read_text()
    )
    before = Path(baseline).read_bytes()
    assert main(args) == 0
    assert Path(baseline).read_bytes() == before
    assert all(
        e["text"].startswith("sha256:")
        for e in yaml.safe_load(Path(baseline).read_text())["entries"]
    )
    path.write_text("\n\n" + source)
    assert main(args) == 0
    path.write_text(source + source)
    assert main(args) == 1
    assert main([*args, "--write-baseline"]) == 1
    assert Path(baseline).read_bytes() == before
    path.write_text("value: str = 'clean'\n")
    assert main(args) == 1
    assert main([*args, "--write-baseline"]) == 0
    assert yaml.safe_load(Path(baseline).read_text())["entries"] == []
    assert (
        Path(baseline)
        .read_text()
        .startswith("# Burn-down ticket: OMN-22012. Zero target: 2026-11-16.\n")
    )
    assert main(args) == 0


@pytest.mark.parametrize(
    "source",
    [
        "def f() -> str:\n    return 1\n",
        "def f(x: str) -> str:\n    return x\nf(1)\n",
        "value: str = 1\n",
    ],
)
def test_pyright_each_enabled_rule_refuses_one_finding(
    source: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main = importlib.import_module(RUNTIME).main
    monkeypatch.chdir(tmp_path)
    path = Path("type_error.py")
    path.write_text(source)
    args = [
        "--hook",
        "pyright-type-check",
        "--project",
        str(ROOT / "pyrightconfig.json"),
        str(path),
    ]
    assert main(args) == 1
    assert capsys.readouterr().out.count("FAIL:") == 1
    path.write_text("value: str = 'clean'\n")
    assert main(args) == 0


@pytest.mark.parametrize(
    ("hook", "fixture"),
    [
        ("no-except-swallow", "except_swallow"),
        ("validate-union-usage", "optional_union"),
        ("pyright-type-check", "type_error"),
    ],
)
def test_precommit_files_refuses_one_canary_and_admits_clean_form(
    hook: str,
    fixture: str,
    tmp_path: Path,
) -> None:
    """Exercise the deployed adapter, using the repository's actual hook row."""
    raw = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    row = next(
        h for repo in raw["repos"] for h in repo.get("hooks", []) if h["id"] == hook
    )
    row = dict(row)
    row["entry"] = row["entry"].replace("uv run", f"uv run --project {ROOT}")
    if hook == "pyright-type-check":
        row["entry"] += f" --project {ROOT / 'pyrightconfig.json'}"
    config = tmp_path / "hooks.yaml"
    config.write_text(yaml.safe_dump({"repos": [{"repo": "local", "hooks": [row]}]}))
    if hook == "no-except-swallow":
        baseline = tmp_path / ".onex_ratchets" / "except_swallow_baseline.yaml"
        baseline.parent.mkdir()
        baseline.write_text("{}\n")
    env = scrub_git_location_env()
    env["PRE_COMMIT_HOME"] = str(tmp_path / "cache")
    subprocess.run(
        ["git", "init", "--quiet", str(tmp_path)],
        env=scrub_git_location_env(env),
        check=True,
    )
    target = tmp_path / "src" / "omnibase_core" / "models" / f"{fixture}.py"
    target.parent.mkdir(parents=True)
    target.write_text(
        (
            ROOT / "tests/fixtures/validation/core_legacy" / f"{fixture}.py.txt"
        ).read_text()
    )
    command = [
        sys.executable,
        "-m",
        "pre_commit",
        "run",
        hook,
        "--config",
        str(config),
        "--files",
        str(target.relative_to(tmp_path)),
        "--verbose",
    ]
    result = subprocess.run(
        command,
        cwd=tmp_path,
        env=scrub_git_location_env(env),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    if hook == "no-except-swallow":
        assert result.stdout.count("[ERROR]") == 1, result.stdout
    else:
        assert result.stdout.count("FAIL:") == 1, result.stdout
    target.write_text("value: str = 'clean'\n")
    result = subprocess.run(
        command,
        cwd=tmp_path,
        env=scrub_git_location_env(env),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_baseline_edits_cannot_add_a_committed_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from omnibase_core.nodes.node_finding_baseline_check_effect import (
        runtime_finding_baseline_check as baseline_runtime,
    )

    main = importlib.import_module(RUNTIME).main
    monkeypatch.chdir(tmp_path)
    path = Path("src/module.py")
    path.parent.mkdir()
    source = "value.model_dump()\n"
    path.write_text(source)
    args = [
        "--hook",
        "validate-model-dump-json-mode",
        "--baseline",
        "baseline.yaml",
        str(path),
    ]
    assert main([*args, "--write-baseline"]) == 0
    committed = Path("baseline.yaml").read_text()
    # Model the two git reads deterministically; this engine never commits.
    monkeypatch.setattr(
        baseline_runtime.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, committed, ""),
    )
    document = yaml.safe_load(committed)
    document["entries"].append(document["entries"][0])
    Path("baseline.yaml").write_text(yaml.safe_dump(document))
    path.write_text(source + source)
    assert main(args) == 1
    assert "baseline only shrinks" in capsys.readouterr().out
    Path("baseline.yaml").unlink()
    assert main([*args, "--write-baseline"]) == 1
    assert not Path("baseline.yaml").exists()


@pytest.mark.parametrize(
    "source",
    [
        "from typing import Optional as Maybe\nvalue: Maybe[str]\n",
        "import typing as t\nvalue: t.Optional[str]\n",
        "from typing import Union\nvalue: Union[str, None]\n",
        "import typing\nvalue: typing.Union[None, str]\n",
    ],
)
def test_optional_syntax_cannot_hide_behind_a_typing_alias(source: str) -> None:
    from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
        ModelSourceFile,
    )

    runtime = importlib.import_module(RUNTIME)
    rule = next(
        r for r in runtime.load_rules().rules if r.hook == "validate-union-usage"
    )
    result = runtime.detect_sources(
        rule, (ModelSourceFile(path="src/module.py", source=source),)
    )
    assert len(result.findings) == 1


def test_modern_nullable_union_and_existing_suppression_pass() -> None:
    from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
        ModelSourceFile,
    )

    runtime = importlib.import_module(RUNTIME)
    rule = next(
        r for r in runtime.load_rules().rules if r.hook == "validate-union-usage"
    )
    marker_name = "union-ok"
    for source in (
        "value: str | None\n",
        f"from typing import Optional\n# {marker_name}: reviewed\nvalue: Optional[str]\n",
    ):
        result = runtime.detect_sources(
            rule, (ModelSourceFile(path="src/module.py", source=source),)
        )
        assert not result.findings


def test_commit_hook_refuses_one_added_finding_in_a_staged_baselined_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = importlib.import_module(RUNTIME).main
    monkeypatch.chdir(tmp_path)
    raw = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    row = next(
        h
        for repo in raw["repos"]
        for h in repo.get("hooks", [])
        if h["id"] == "validate-model-dump-json-mode"
    )
    row = dict(row)
    row["entry"] = row["entry"].replace("uv run", f"uv run --project {ROOT}")
    config = Path("hooks.yaml")
    config.write_text(yaml.safe_dump({"repos": [{"repo": "local", "hooks": [row]}]}))
    env = scrub_git_location_env()
    env["PRE_COMMIT_HOME"] = str(tmp_path / "cache")
    subprocess.run(
        ["git", "init", "--quiet"], env=scrub_git_location_env(env), check=True
    )
    target = Path("src/module.py")
    target.parent.mkdir()
    target.write_text("value.model_dump()\n")
    baseline = ".onex_ratchets/validate-model-dump-json-mode.yaml"
    assert (
        main(
            [
                "--hook",
                row["id"],
                "--baseline",
                baseline,
                str(target),
                "--write-baseline",
            ]
        )
        == 0
    )
    before = Path(baseline).read_bytes()
    command = [
        sys.executable,
        "-m",
        "pre_commit",
        "run",
        row["id"],
        "--config",
        str(config),
        "--verbose",
    ]
    subprocess.run(
        ["git", "add", str(target), str(config)],
        env=scrub_git_location_env(env),
        check=True,
    )
    admitted = subprocess.run(
        command,
        env=scrub_git_location_env(env),
        capture_output=True,
        text=True,
        check=False,
    )
    assert admitted.returncode == 0, admitted.stdout + admitted.stderr
    target.write_text("value.model_dump()\nother.model_dump()\n")
    subprocess.run(
        ["git", "add", str(target)], env=scrub_git_location_env(env), check=True
    )
    refused = subprocess.run(
        command,
        env=scrub_git_location_env(env),
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert refused.stdout.count("FAIL:") == 1, refused.stdout
    assert Path(baseline).read_bytes() == before
