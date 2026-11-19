# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-25070 AC6: CI never depends on an omnibase_core console script T1 removes.

T1 of the customer delivery plan takes the check tools out of the customer install, so the
console scripts omnibase_core declares (all but the customer launchers ``onex`` and
``omni-agent``) can disappear from the published package. Every caller must survive that:

* a workflow or composite action ``run:`` step that executes one of those scripts, directly,
  through ``uv run`` or from ``.venv/bin``, fails once the script is gone;
* a hook ``entry:`` in ``.pre-commit-hooks.yaml`` that names one breaks every repository that
  uses omnibase_core's hooks, and a local hook ``entry:`` breaks this repository;
* the reusable ``validate-docs.yml`` standalone mode installed omnibase_core as a uv tool and
  ran its script, which yields no command once the package declares none.

Callers run ``python -m <module>`` instead. The last case checks that every such module
exists in this checkout and runs as a module, so a misspelt replacement fails here rather
than in a downstream CI run.

The other registry repositories (``src/omnibase_core/contracts/repo_layers.yaml``) are
scanned with the same rule when they are checked out beside this one, as in an
``${OMNI_HOME}/<repo>`` workspace; a CI job holding only this checkout scans this repository.
"""

from __future__ import annotations

import importlib.util
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CUSTOMER_LAUNCHERS = frozenset({"onex", "omni-agent"})


def _removable_scripts() -> frozenset[str]:
    scripts = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["scripts"]
    return frozenset(name for name in scripts if name not in CUSTOMER_LAUNCHERS)


def _registry_roots() -> list[Path]:
    """This checkout, then every registry repository checked out beside it."""
    layers = yaml.safe_load(
        (REPO_ROOT / "src/omnibase_core/contracts/repo_layers.yaml").read_text(
            encoding="utf-8"
        )
    )
    siblings = [REPO_ROOT.parent / entry["repo"] for entry in layers["repos"]]
    return [REPO_ROOT] + [
        path
        for path in siblings
        if path.name != "omnibase_core" and (path / ".git").exists()
    ]


def _shell_texts(root: Path) -> list[tuple[str, str]]:
    """(location, shell text) for every workflow/action run step and hook entry."""
    texts: list[tuple[str, str]] = []
    github = root / ".github"
    for path in sorted(github.rglob("*.y*ml")) if github.is_dir() else []:
        if "workflows" not in path.parts and "actions" not in path.parts:
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        jobs = list((doc.get("jobs") or {}).values()) if isinstance(doc, dict) else []
        runs = (doc.get("runs") or {}) if isinstance(doc, dict) else {}
        step_lists = [job.get("steps") or [] for job in jobs if isinstance(job, dict)]
        step_lists.append(runs.get("steps") or [] if isinstance(runs, dict) else [])
        for steps in step_lists:
            for step in steps:
                if isinstance(step, dict) and isinstance(step.get("run"), str):
                    name = step.get("name") or step.get("id") or "?"
                    texts.append(
                        (f"{path.relative_to(root)} step {name!r}", step["run"])
                    )
    for config in (".pre-commit-hooks.yaml", ".pre-commit-config.yaml"):
        path = root / config
        if not path.is_file():
            continue
        loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        if config == ".pre-commit-hooks.yaml":
            hooks = loaded or []
        else:  # only local hooks run an entry from this checkout's environment
            hooks = [
                hook
                for block in (loaded or {}).get("repos", [])
                if block.get("repo") == "local"
                for hook in block.get("hooks", [])
            ]
        for hook in hooks:
            if isinstance(hook.get("entry"), str):
                texts.append((f"{config} hook {hook['id']!r}", hook["entry"]))
    return texts


def _invocations(text: str, scripts: frozenset[str]) -> list[str]:
    """Script names ``text`` executes as a command.

    A dashed script name standing as a whole word, or as the last part of a ``bin/`` path
    (``.venv/bin/<script>``), is an invocation, except where it is a pre-commit hook id
    handed to ``pre-commit run`` or listed in ``SKIP``: a hook id that shares the script's
    name runs the hook's own entry, which this test checks separately.
    """
    found = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or re.search(
            r"pre-commit\S*\s+run\b|\bSKIP=", stripped
        ):
            continue
        for name in scripts:
            word = rf"(?:(?<=bin/)|(?<![\w./-])){re.escape(name)}(?![\w-])"
            if re.search(word, stripped):
                found.append(name)
    return found


def _hook_ids(root: Path) -> frozenset[str]:
    path = root / ".pre-commit-config.yaml"
    if not path.is_file():
        return frozenset()
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return frozenset(
        hook["id"] for block in doc.get("repos", []) for hook in block.get("hooks", [])
    )


def _own_scripts(root: Path) -> frozenset[str]:
    """Console scripts the scanned repository declares itself.

    A repository that declares a script of the same name runs its own program, which T1
    does not remove (onex_change_control declares its own check-imperative-contracts).
    """
    if root == REPO_ROOT:
        return frozenset()
    path = root / "pyproject.toml"
    if not path.is_file():
        return frozenset()
    project = tomllib.loads(path.read_text(encoding="utf-8")).get("project", {})
    return frozenset(project.get("scripts", {}))


def _offenders(root: Path) -> list[str]:
    removable = _removable_scripts()
    own = _own_scripts(root)
    hook_ids = _hook_ids(root)
    offenders = []
    for location, text in _shell_texts(root):
        # A repository's own script of the same name is exempt only where the step does not
        # fetch omnibase_core itself (`uvx --from omnibase_core`, `uv tool install omnibase_core`):
        # there the name runs core's copy, which T1 removes.
        fetches_core = bool(re.search(r"omnibase[_-]core", text))
        scripts = removable if fetches_core else removable - own
        # A step that drives pre-commit (`pre-commit run "$hook"` over a list of names) names
        # hook ids, which run the hook's entry; the entries are checked on their own.
        runs_precommit = bool(re.search(r"pre-commit\S*\s+run\b", text))
        offenders += [
            f"{location}: {name}"
            for name in _invocations(text, scripts)
            if not (runs_precommit and name in hook_ids)
        ]
    return offenders


def test_a_repository_running_its_own_script_of_that_name_is_not_a_caller(
    tmp_path: Path,
) -> None:
    core_script = sorted(_removable_scripts())[0]

    def repository(name: str, declares_it: bool, run: str = "uv run") -> Path:
        root = tmp_path / name
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "ci.yml").write_text(
            "jobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n"
            f"      - run: {run} {core_script} --verbose\n",
            encoding="utf-8",
        )
        scripts = f'[project.scripts]\n{core_script} = "own.module:main"\n'
        (root / "pyproject.toml").write_text(
            '[project]\nname = "x"\n' + (scripts if declares_it else ""),
            encoding="utf-8",
        )
        return root

    assert _offenders(repository("declares", declares_it=True)) == []
    assert _offenders(repository("borrows", declares_it=False)) != []
    # Declaring the name does not exempt a step that runs omnibase_core's own copy.
    assert (
        _offenders(
            repository(
                "declares_but_fetches_core",
                declares_it=True,
                run="uvx --from omnibase_core",
            )
        )
        != []
    )


@pytest.mark.parametrize("root", _registry_roots(), ids=lambda p: p.name)
def test_no_ci_caller_runs_a_removable_console_script(root: Path) -> None:
    offenders = _offenders(root)
    assert offenders == [], (
        "these CI callers run an omnibase_core console script that OMN-25070 (T1) removes "
        "from the customer install; run `python -m <module>` instead:\n  "
        + "\n  ".join(sorted(set(offenders)))
    )


def test_standalone_validate_docs_needs_no_installed_script() -> None:
    workflow = (REPO_ROOT / ".github/workflows/validate-docs.yml").read_text(
        encoding="utf-8"
    )
    assert "uv tool install omnibase_core" not in workflow, (
        "standalone mode must not rely on a console script from a uv tool install of "
        "omnibase_core; run the module with `uv run --no-project --with omnibase_core`"
    )
    assert "--with omnibase_core python -m" in workflow


def test_every_python_dash_m_target_runs_as_a_module() -> None:
    targets = set()
    for _, text in _shell_texts(REPO_ROOT):
        targets.update(re.findall(r"python3?\s+-m\s+(omnibase_core[\w.]*)", text))
    assert targets, "no python -m caller found; the scan itself is broken"
    broken = []
    for module in sorted(targets):
        spec = importlib.util.find_spec(module)
        if spec is None or spec.origin is None:
            broken.append(f"{module}: not importable")
            continue
        source = Path(spec.origin).read_text(encoding="utf-8")
        is_package_main = Path(spec.origin).name == "__main__.py"
        if not is_package_main and not re.search(
            r"^if __name__ == [\"']__main__[\"']:", source, re.M
        ):
            if spec.submodule_search_locations and importlib.util.find_spec(
                f"{module}.__main__"
            ):
                continue
            broken.append(f"{module}: no `if __name__ == '__main__'` block")
    assert broken == [], "python -m targets that cannot run:\n  " + "\n  ".join(broken)
