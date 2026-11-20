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
    # Shell scripts are callers too: a step or a person runs them by path.
    scripts = root / "scripts"
    for path in sorted(scripts.rglob("*.sh")) if scripts.is_dir() else []:
        texts.append((str(path.relative_to(root)), path.read_text(encoding="utf-8")))
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


# The customer launchers move out of omnibase_core (OMN-25070 AC3, the launcher move):
# only omninode-onex will declare them. A CI step or hook that runs `onex` as a command
# stops working then, so every caller runs the CLI module instead:
# `python -m omnibase_core.cli.cli_commands <args>`. "onex" is also an ordinary word in
# step names, messages and paths, so only a command position counts: the start of a
# line or of a pipeline element, after exec/then/do/time/if/!/env, as the program of
# `uv run [flags]` or `uvx [flags]`, or as a `.../bin/onex` or `$VAR/onex` path.
_LAUNCHER_PREFIX = (
    # a command group's { needs whitespace after it; ${VAR} is not one
    r"(?:^|[;&|(]\s*|\{\s+|\$\(\s*"
    # wrappers that run their arguments as a command
    # a negating ! stands alone as a word (\b cannot sit before it)
    r"|(?<!\S)!\s+"
    r"|\b(?:exec(?:\s+-a\s+\S+)?|then|do|time|if|nohup|command|xargs(?:\s+-\S+)*"
    r"|timeout(?:\s+-\S+)*\s+\S+|stdbuf(?:\s+-\S+)+|sudo(?:\s+-\w+(?:\s+(?!onex\b|omni-agent\b)[^\s-]\S*)?)*"
    r"|(?:uv\s+tool|pipx|poetry|hatch)\s+run(?:\s+--?[\w-]+(?:[= ](?!onex\b|omni-agent\b)[^\s-]\S*)?)*(?:\s+--)?)\s+"
    r"|\benv(?:\s+-\S+)*(?:\s+\w+=\S+)*\s+"
    # leading VAR=value assignments
    r"|^(?:\w+=[^\s(]*\s+)+"
    # a wrapper script that runs its arguments, e.g. scripts/uv-run-worktree-safe.sh
    r"|\S+\.sh\s+"
    r"|\buv\s+run(?:\s+--?[\w-]+(?:[= ](?!onex\b|omni-agent\b)[^\s-]\S*)?)*(?:\s+--)?\s+"
    # a runner held in a variable, e.g. ${UV} run
    r"|\$\{?\w+\}?\s+run(?:\s+--?[\w-]+(?:[= ](?!onex\b|omni-agent\b)[^\s-]\S*)?)*(?:\s+--)?\s+"
    r"|\buvx(?:\s+--?[\w-]+(?:[= ](?!onex\b|omni-agent\b)[^\s-]\S*)?)*\s+)"
)
_LAUNCHER_CALL = re.compile(
    _LAUNCHER_PREFIX
    + r"[\"']?(?:[\w$.{}~/-]*bin/|\$\{?\w+\}?/)?(onex|omni-agent)[\"']?(?=[\s;&|)>]|$)"
)


# A command string handed to a shell runs its contents (-c alone or among combined
# flags, as in -lc or -euxc).
_SHELL_C = re.compile(r"\b(?:ba|z|da)?sh\s+(?:-\w+\s+)*-\w*c\s+(['\"])(.*?)\1")
# A $( ) substitution runs its contents.
_DOLLAR_PAREN = re.compile(r"\$\(([^()]*)\)")
# A backtick substitution runs its contents; an escaped backtick is a literal character.
_BACKTICK = re.compile(r"(?<!\\)`([^`]*?)(?<!\\)`")
# The arguments of echo or printf, each a quoted string or a bare word, up to the next
# command separator; the quoted ones are a printed message, not a command.
_PRINTED = re.compile(
    r"\b(echo|printf)((?:\s+(?:'[^']*'|\"(?:\\.|[^\"\\])*\"|[^\s;&|)'\"]+))*)"
)
_QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
_SINGLE_QUOTED = re.compile(r"'[^']*'")
# Not counted: `docker run|exec <image> onex ...` runs the onex of a container image,
# which is that image's own install, not a launcher this checkout's CI resolves.


def _strip_comment(line: str) -> str:
    """``line`` without a trailing comment; a ``#`` inside quotes is not one."""
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if in_single:
            if ch == "'":
                in_single = False
            continue
        if in_double:
            if ch == '"' and (i == 0 or line[i - 1] != "\\"):
                in_double = False
            continue
        if ch in ("'", '"'):
            if i == 0 or line[i - 1] != "\\":
                if ch == "'":
                    in_single = True
                else:
                    in_double = True
            continue
        if ch == "#" and (i == 0 or line[i - 1].isspace()):
            return line[:i].rstrip()
    return line


def _command_texts(text: str) -> list[str]:
    """``text`` and, recursively, every shell string and substitution it runs."""
    texts = [text]
    for match in _SHELL_C.finditer(text):
        texts.extend(_command_texts(match.group(2)))
    # Inside single quotes a substitution is literal text, so it runs nothing.
    unquoted = _SINGLE_QUOTED.sub("''", text)
    for pattern in (_DOLLAR_PAREN, _BACKTICK):
        for match in pattern.finditer(unquoted):
            texts.extend(_command_texts(match.group(1)))
    return texts


def _launcher_calls(text: str) -> list[str]:
    """Lines of ``text`` that run ``onex`` or ``omni-agent`` as a command."""
    found = []
    # A command continued with a trailing backslash is one logical line.
    for line in re.sub(r"\\\n\s*", " ", text).splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        command = _strip_comment(stripped)
        # What the line runs inside strings and substitutions is read before the
        # printed messages are blanked, so `echo "$(onex --version)"` still counts.
        inner = _command_texts(command)[1:]
        outer = _PRINTED.sub(
            lambda m: m.group(1) + _QUOTED.sub("''", m.group(2)), command
        )
        if any(_LAUNCHER_CALL.search(part) for part in [outer, *inner]):
            found.append(stripped)
    return found


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


@pytest.mark.parametrize(
    "line",
    [
        "uv run onex node node_x",
        "uv run --frozen onex spdx validate",
        "if uv run onex compliance check --help >/dev/null 2>&1; then",
        "onex node node_release_notes_apply_effect \\",
        '"$bin_dir/onex" --version',
        "out=$(onex --version)",
        "uvx --from omnibase-core onex --help",
        "env A=1 OMNIBASE_PATH=/app onex ledger query --stdin",
        "bash scripts/uv-run-worktree-safe.sh onex spdx validate",
        "timeout 60 onex node x",
        "sudo -u runner onex node x",
        "xargs onex node",
        "nohup onex node x &",
        "FOO=1 onex node x",
        "uv tool run onex --help",
        "pipx run onex --help",
        "uv run -- onex --help",
        "uv tool run --from omninode-onex onex --help",
        "test -x x && onex;",
        "out=$(onex)",
        "uv run \\\n  onex node x",
        # a command string handed to a shell, a backtick substitution, a variable runner
        "bash -c 'onex node x'",
        'sh -c "onex --help"',
        "out=`onex --version`",
        "${UV} run onex x",
        "$UV run onex --help",
        # a substitution inside a printed message still runs
        'echo "v: $(uv run onex --version)"',
        'echo "`onex v`"',
        # a # inside quotes is not a comment; combined shell flags still take -c
        'echo "step # 1" && onex x',
        "bash -lc 'onex x'",
        "bash -euxc 'onex x'",
        # a command group or function body
        "run() { onex node x; }",
        # a negated command
        "if ! onex node x; then",
        "! onex x",
    ],
)
def test_a_launcher_command_is_recognised(line: str) -> None:
    assert len(_launcher_calls(line)) == 1, line


@pytest.mark.parametrize(
    "line",
    [
        "name: onex architecture",
        'echo "no onex for the customer"',
        "path plugins/onex/skills",
        "plugins/onex \\",
        "ONEX_STATE=.onex_state",
        # .github/workflows/ci.yml: escaped backticks print literally
        'echo "- declares a node dispatch (\\`onex run-node\\` / \\`onex node\\` /"',
        "uv run python -m omnibase_core.cli.cli_commands compliance check",
        "command -v onex >/dev/null",
        "bash scripts/check.sh plugins/onex",
        'PLUGIN_JSON=$(find "$TMPDIR/onex" -name plugin.json)',
        # words that start a command elsewhere, inside a printed message or a comment
        'echo "if onex is missing, skip"',
        'echo "then onex runs the node"',
        'echo "ok; onex is installed"',
        'echo "do onex node"',
        'echo "time onex took 3s"',
        'echo "(onex)"',
        'echo "a | onex b"',
        "x=1 # then onex x",
        'printf "then onex %s\\n" x',
        # an escaped backtick inside quotes is a literal character, not a substitution
        'say "  Until this is converged, an \\`onex delegate\\` through the plugin"',
        "${SCRIPT_NAME} — Trigger the ONEX build loop via \\`onex run\\`",
        # every quoted argument of a printed message is prose, not only the first
        'echo "a" "then onex b"',
        "echo 'a' 'b; onex c'",
        "printf '%s\\n' \"then onex\"",
        # inside single quotes a substitution is literal text
        "echo '$(onex)'",
        # omniweb m3-customer-pass-chain.yml: a ${VAR} brace is not a command group
        'bin="${RUNNER_TEMP}/onex-venv/bin/onex"',
    ],
)
def test_prose_and_the_module_form_are_not_launcher_calls(line: str) -> None:
    assert _launcher_calls(line) == []


def test_a_launcher_script_under_scripts_is_scanned(tmp_path: Path) -> None:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "roll.sh").write_text("uv run onex spdx fix src\n", encoding="utf-8")
    assert any(
        "scripts/roll.sh" in location and _launcher_calls(text)
        for location, text in _shell_texts(tmp_path)
    )


@pytest.mark.parametrize("root", _registry_roots(), ids=lambda p: p.name)
def test_no_ci_caller_runs_the_onex_launcher(root: Path) -> None:
    callers = [
        f"{location}: {line}"
        for location, text in _shell_texts(root)
        for line in _launcher_calls(text)
    ]
    assert callers == [], (
        "these CI callers run the onex launcher, which only omninode-onex will declare "
        "(OMN-25070); run `python -m omnibase_core.cli.cli_commands <args>` instead:\n  "
        + "\n  ".join(sorted(set(callers)))
    )
