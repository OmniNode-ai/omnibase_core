# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule-data tests of the dependency-direction COMPUTE node (OMN-19998, OMN-21518).

Every pattern, name list and message template of the check is a ``parameters`` entry
of a rule row of ``dependency_direction.validation.yaml``. Each test changes one
parameter and sees the observable result change, so a parameter that is read nowhere,
or a table that came back as a module constant, fails here. The node ``contract.yaml``
must bind the handler.
"""

from __future__ import annotations

import ast
import importlib
import itertools
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.enums.enum_dependency_channel import EnumDependencyChannel
from omnibase_core.models.dependency_direction import (
    ModelDependencyDirectionBaselineEntry,
    ModelDependencyDirectionCheckInput,
    ModelDependencyDirectionRules,
    ModelRepoLayer,
    ModelRepoLayerMap,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.nodes.node_dependency_direction_check_effect import (
    matcher_dependency_direction as matcher,
)
from omnibase_core.nodes.node_dependency_direction_check_effect import (
    runtime_dependency_direction_check as runtime,
)
from omnibase_core.nodes.node_dependency_direction_check_effect.handler_dependency_direction import (
    HandlerDependencyDirection,
)
from omnibase_core.validation.checker_dependency_direction import (
    load_dependency_direction_contract,
    load_dependency_direction_rules,
    rules_from_rows,
)

pytestmark = pytest.mark.unit

NODE_DIR = (
    Path(runtime.__file__).resolve().parent
)  # src/omnibase_core/nodes/node_dependency_direction_check_effect
_ORG = "OmniNode-ai"

LAYERS = ModelRepoLayerMap(
    github_org=_ORG,
    repos=(
        ModelRepoLayer(
            repo="omnibase_spi",
            layer=2,
            python_modules=("omnibase_spi",),
            distributions=("omnibase-spi",),
        ),
        ModelRepoLayer(
            repo="onex_change_control",
            layer=2,
            python_modules=("onex_change_control",),
            distributions=("onex-change-control",),
        ),
        ModelRepoLayer(
            repo="omnibase_infra",
            layer=3,
            python_modules=("omnibase_infra",),
            distributions=("omnibase-infra",),
        ),
        ModelRepoLayer(
            repo="omnimarket",
            layer=5,
            python_modules=("omnimarket",),
            distributions=("omnimarket",),
        ),
    ),
)

_RUNS = itertools.count()


class _Env:
    """What a probe may use besides the rules."""

    def __init__(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        self.tmp_path = tmp_path
        self.monkeypatch = monkeypatch
        self.capsys = capsys


Probe = Callable[[ModelDependencyDirectionRules, _Env], object]


def _refs(path: str, source: str, own: str = "omnibase_infra") -> Probe:
    def probe(rules: ModelDependencyDirectionRules, env: _Env) -> object:
        return matcher.extract_references(path, source, LAYERS, own, rules)

    return probe


def _channel(path: str) -> Probe:
    def probe(rules: ModelDependencyDirectionRules, env: _Env) -> object:
        return (matcher.classify_path(path, rules), matcher.is_candidate(path, rules))

    return probe


def _check(
    files: dict[str, str],
    repo: str = "omnibase_infra",
    baseline: tuple[ModelDependencyDirectionBaselineEntry, ...] = (),
    stale: bool = False,
) -> Probe:
    def probe(rules: ModelDependencyDirectionRules, env: _Env) -> object:
        report = HandlerDependencyDirection().handle(
            ModelDependencyDirectionCheckInput(
                repo=repo,
                rules=rules,
                layer_map=LAYERS,
                files=tuple(
                    ModelSourceFile(path=p, source=s) for p, s in files.items()
                ),
                baseline=baseline,
                report_stale_baseline=stale,
            )
        )
        return [(f.severity, f.message, f.remediation) for f in report.findings]

    return probe


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(root),
        },
    )


def _main(files: dict[str, str], *flags: str, pyproject: bool = True) -> Probe:
    """Run the CLI on a throwaway git repository with ``rules`` and return code and output."""

    def probe(rules: ModelDependencyDirectionRules, env: _Env) -> object:
        root = env.tmp_path / f"repo{next(_RUNS)}"
        root.mkdir()
        _git(root, "init", "-q", "-b", "dev")
        if pyproject:
            (root / "pyproject.toml").write_text('[project]\nname = "omnibase-infra"\n')
        for rel, text in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
        if files or pyproject:
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "base")
        env.monkeypatch.setattr(
            runtime, "load_dependency_direction_rules", lambda: rules
        )
        env.capsys.readouterr()
        code = runtime.main(["--root", str(root), *flags])
        return (code, env.capsys.readouterr().out.replace(str(root), "ROOT"))

    return probe


def _baseline_header(rules: ModelDependencyDirectionRules, env: _Env) -> object:
    return runtime.render_baseline(
        "omnibase_infra",
        [ModelSourceFile(path="a.py", source="import omnimarket\n")],
        LAYERS,
        "OMN-1",
        rules,
    )


def _baseline_grew(rules: ModelDependencyDirectionRules, env: _Env) -> object:
    entry = ModelDependencyDirectionBaselineEntry(
        path="a.py",
        channel=EnumDependencyChannel.PYTHON_IMPORT,
        target="omnimarket",
        ticket="OMN-1",
    )
    return runtime.baseline_growth((entry,), (), rules)


_UP = "omnimarket"
_INSTALL = f'RUN uv pip install --no-deps "{_UP} @ file:///workspace/{_UP}"\n'
_WORKFLOW = f"jobs:\n  a:\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          repository: {_ORG}/{_UP}\n"
_UPWARD = {"src/a.py": f"import {_UP}\n"}
_SAME = {"src/a.py": "import onex_change_control\n"}
_BASELINED = (
    ModelDependencyDirectionBaselineEntry(
        path="src/a.py",
        channel=EnumDependencyChannel.PYTHON_IMPORT,
        target=_UP,
        ticket="OMN-19998",
    ),
)
_STALE = (
    ModelDependencyDirectionBaselineEntry(
        path="src/gone.py",
        channel=EnumDependencyChannel.PYTHON_IMPORT,
        target=_UP,
        ticket="OMN-19998",
    ),
)
_NEVER = "(?!x)x"
_MARK = "MUTATED-MARKER"

# (rule_id, parameter key, mutated value, probe that sees the change)
CASES: list[tuple[str, str, object, Probe]] = [
    (
        "reference_channels",
        "install_or_fetch_pattern",
        _NEVER,
        _refs("docker/Dockerfile", _INSTALL),
    ),
    (
        "reference_channels",
        "repository_pattern",
        _NEVER,
        _refs(".github/workflows/ci.yml", _WORKFLOW),
    ),
    (
        "reference_channels",
        "requirement_name_pattern",
        _NEVER,
        _refs("requirements.txt", f"{_UP}==1\n"),
    ),
    (
        "reference_channels",
        "name_separator_pattern",
        "[-]+",
        _refs("requirements.txt", "omnibase_infra==1\n", own=_UP),
    ),
    (
        "reference_channels",
        "token_before_pattern",
        "(?<=Z)",
        _refs("docker/Dockerfile", _INSTALL),
    ),
    (
        "reference_channels",
        "token_after_pattern",
        "(?=Z)",
        _refs("docker/Dockerfile", _INSTALL),
    ),
    (
        "reference_channels",
        "slug_repo_pattern",
        "/(zzz)",
        _refs(".github/workflows/ci.yml", _WORKFLOW),
    ),
    ("reference_channels", "script_suffixes", [".zzz"], _channel("scripts/run.sh")),
    ("reference_channels", "makefile_names", ["Other"], _channel("Makefile")),
    (
        "reference_channels",
        "workflow_dir_prefix",
        ".gitlab/",
        _channel(".github/workflows/ci.yml"),
    ),
    (
        "reference_channels",
        "workflow_suffixes",
        [".zzz"],
        _channel(".github/workflows/ci.yml"),
    ),
    (
        "reference_channels",
        "dockerfile_prefixes",
        ["zzz"],
        _channel("docker/Dockerfile"),
    ),
    (
        "reference_channels",
        "dockerfile_suffixes",
        [".zzz"],
        _channel("docker/app.dockerfile"),
    ),
    (
        "reference_channels",
        "requirements_prefixes",
        ["zzz"],
        _channel("requirements-dev.txt"),
    ),
    (
        "reference_channels",
        "requirements_suffixes",
        [".zzz"],
        _channel("requirements-dev.txt"),
    ),
    (
        "reference_channels",
        "python_suffix",
        ".pyx",
        _refs("src/a.py", f"import {_UP}\n"),
    ),
    (
        "reference_channels",
        "pyproject_name",
        "other.toml",
        _refs("pyproject.toml", f'[project]\ndependencies = ["{_UP}"]\n'),
    ),
    ("reference_channels", "script_dirs", ["bin"], _channel("scripts/run.py")),
    (
        "reference_channels",
        "script_excluded_dirs",
        ["zzz"],
        _channel("scripts/tests/run.py"),
    ),
    (
        "reference_channels",
        "fixture_dirs",
        ["zzz"],
        _refs("tests/fixtures/a.py", f"import {_UP}\n"),
    ),
    (
        "reference_channels",
        "comment_prefix",
        "//",
        _refs("docker/Dockerfile", f"# pip install {_UP}\n"),
    ),
    ("reference_channels", "evidence_limit", 10, _refs("docker/Dockerfile", _INSTALL)),
    ("upward_dependency", "remediation", _MARK, _check(_UPWARD)),
    ("upward_dependency", "violation_message", f"{_MARK} {{path}}", _check(_UPWARD)),
    ("upward_dependency", "direction_same", _MARK, _check(_SAME, repo="omnibase_spi")),
    ("upward_dependency", "direction_above", _MARK, _check(_UPWARD)),
    (
        "upward_dependency",
        "baselined_message",
        f"{_MARK} {{message}}",
        _check(_UPWARD, baseline=_BASELINED),
    ),
    (
        "repo_not_in_layer_map",
        "undeclared_repo_message",
        f"{_MARK} {{repo}}",
        _check(_UPWARD, repo="not_a_repo"),
    ),
    (
        "stale_baseline_entry",
        "stale_message",
        f"{_MARK} {{path}}",
        _check(_UPWARD, baseline=_STALE, stale=True),
    ),
    (
        "baseline_ratchet",
        "ratchet_ref_missing_message",
        f"{_MARK} {{ref}}",
        _main({"src/a.py": "import os\n"}, "--ratchet-base-ref", "0" * 40),
    ),
    ("baseline_ratchet", "baseline_grew_message", f"{_MARK} {{path}}", _baseline_grew),
    (
        "baseline_ratchet",
        "zero_files_message",
        f"{_MARK} {{root}}",
        _main({}, "--repo", "omnibase_infra", pyproject=False),
    ),
    ("baseline_ratchet", "baseline_header", f"# {_MARK}\n", _baseline_header),
    (
        "baseline_ratchet",
        "baseline_spdx_copyright",
        _MARK,
        _baseline_header,
    ),
    ("baseline_ratchet", "baseline_spdx_license", _MARK, _baseline_header),
    (
        "run_summary",
        "ok_message",
        f"{_MARK} {{repo}} {{count}}",
        _main({"src/a.py": "import os\n"}),
    ),
    (
        "run_summary",
        "fail_message",
        f"{_MARK} {{status}} {{repo}}",
        _main({"docker/Dockerfile": _INSTALL}),
    ),
]


def _rows() -> dict[str, Any]:
    return {row.rule_id: row for row in load_dependency_direction_contract().rules}


def _mutated(rule_id: str, key: str, value: object) -> ModelDependencyDirectionRules:
    rows = _rows()
    row = rows[rule_id]
    rows[rule_id] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules_from_rows(rows)


def _case_id(case: tuple[str, str, object, Probe]) -> str:
    return f"{case[0]}.{case[1]}"


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_changing_a_parameter_changes_the_result(
    case: tuple[str, str, object, Probe],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rule_id, key, value, probe = case
    env = _Env(tmp_path, monkeypatch, capsys)
    base = probe(load_dependency_direction_rules(), env)
    assert probe(_mutated(rule_id, key, value), env) != base


def test_every_parameter_of_the_contract_has_a_case() -> None:
    declared = {
        (row.rule_id, key)
        for row in load_dependency_direction_contract().rules
        for key in (row.parameters or {})
    }
    assert declared == {(c[0], c[1]) for c in CASES}


def test_every_rules_field_is_a_contract_parameter() -> None:
    declared = {
        key
        for row in load_dependency_direction_contract().rules
        for key in (row.parameters or {})
    }
    composed_into_baseline_header = {"baseline_spdx_copyright", "baseline_spdx_license"}
    assert declared - composed_into_baseline_header == set(
        ModelDependencyDirectionRules.model_fields
    )


def test_a_missing_parameter_fails_the_contract_load() -> None:
    rows = _rows()
    row = rows["reference_channels"]
    trimmed = {k: v for k, v in (row.parameters or {}).items() if k != "evidence_limit"}
    rows["reference_channels"] = row.model_copy(update={"parameters": trimmed})
    with pytest.raises(Exception, match="evidence_limit"):
        rules_from_rows(rows)


def _module_level_tables(path: Path) -> list[str]:
    """Names bound at module level to a collection, a compiled pattern or a sentence."""
    tables: list[str] = []
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        is_table = (
            (isinstance(value, ast.Set | ast.Tuple) and bool(value.elts))
            or (isinstance(value, ast.Dict) and bool(value.keys))
            or (
                isinstance(value, ast.Call)
                and ast.unparse(value.func)
                in {"frozenset", "set", "dict", "tuple", "re.compile"}
                and bool(value.args or value.keywords)
            )
            or (
                isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and len(value.value.split()) >= 2
            )
        )
        if is_table:
            tables.extend(ast.unparse(t) for t in targets)
    return tables


def test_the_modules_hold_no_rule_table() -> None:
    for path in sorted(NODE_DIR.glob("*.py")):
        assert _module_level_tables(path) == [], path.name


def test_validator_id_is_the_contract_id() -> None:
    assert load_dependency_direction_contract().validator_id == matcher.VALIDATOR_ID


def test_node_contract_binds_the_handler() -> None:
    contract = yaml.safe_load((NODE_DIR / "contract.yaml").read_text(encoding="utf-8"))
    module_name, _, class_name = contract["handler_routing"][
        "default_handler"
    ].partition(":")
    module = importlib.import_module(
        f"{NODE_DIR.parent.parent.name}.nodes.{NODE_DIR.name}.{module_name}"
    )
    assert getattr(module, class_name) is HandlerDependencyDirection
    input_module, _, input_class = contract["input_model"].rpartition(".")
    assert (
        getattr(importlib.import_module(input_module), input_class)
        is ModelDependencyDirectionCheckInput
    )
    assert contract["node_id"] == NODE_DIR.name
