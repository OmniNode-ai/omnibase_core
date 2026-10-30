# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Replay of the decisions of the OCC ``cosmetic-lint check`` hook (OMN-20074).

``fixtures/occ_cosmetic_lint/manifest.yaml`` lists trees built from verbatim
omnibase_spi files (at 9c145fb) and from constructed files, with, per tree, the
exit status and the stderr lines that ``cosmetic-lint check`` of
onex_change_control rev 8d7e85bc00e7 produced for it. The handler and the
exported entry point must reproduce them line for line, so a consumer that
changes only ``repo:`` and ``rev:`` sees no difference in what is reported.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path, PurePosixPath

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.nodes.cosmetic_lint.model_cosmetic_github_snapshot import (
    ModelCosmeticGithubSnapshot,
)
from omnibase_core.models.nodes.cosmetic_lint.model_cosmetic_lint_input import (
    ModelCosmeticLintInput,
)
from omnibase_core.models.nodes.cosmetic_lint.model_cosmetic_lint_rules import (
    ModelCosmeticLintRules,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_cosmetic_lint_check_compute import (
    runtime_cosmetic_lint_check as runtime,
)
from omnibase_core.nodes.node_cosmetic_lint_check_compute.handler_cosmetic_lint import (
    HandlerCosmeticLint,
    select_python_paths,
)
from omnibase_core.nodes.node_cosmetic_lint_check_compute.runtime_cosmetic_lint_check import (
    SPEC_RESOURCE,
    build_rules,
    load_rule_rows,
    load_rules,
    load_spec_yaml,
    main,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "occ_cosmetic_lint"
SPEC_FILE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "omnibase_core"
    / "contracts"
    / SPEC_RESOURCE
)
CHECK_PREFIXES = ("spdx", "pyproject", "precommit", "readme", "github")


class _FileSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str | None = None
    fixture: str | None = None
    replace: list[list[str]] = Field(default_factory=list)


class _Case(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    description: str
    files: dict[str, _FileSpec]
    empty_files: list[str] = Field(default_factory=list)
    expected_exit: int
    expected_stderr: list[str]


def _manifest() -> dict[str, object]:
    raw = yaml.safe_load((FIXTURES / "manifest.yaml").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def _cases() -> list[_Case]:
    raw = _manifest()["cases"]
    assert isinstance(raw, list)
    return [_Case(**item) for item in raw]


def _text(spec: _FileSpec) -> str:
    if spec.text is not None:
        return spec.text
    assert spec.fixture is not None
    text = (FIXTURES / spec.fixture).read_text(encoding="utf-8")
    for old, new in spec.replace:
        assert old in text, old
        text = text.replace(old, new)
    return text


def _materialize(root: Path, case: _Case) -> dict[str, str]:
    contents: dict[str, str] = {}
    for rel, spec in case.files.items():
        contents[rel] = _text(spec)
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents[rel], encoding="utf-8")
    for rel in case.empty_files:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    return contents


def _request(case: _Case, contents: dict[str, str]) -> ModelCosmeticLintInput:
    """Build the explicit request the way the EFFECT boundary would."""
    github_files = [p for p in case.empty_files if p.startswith(".github/")]
    github_files += [p for p in contents if p.startswith(".github/")]
    entries: set[str] = set()
    for path in github_files:
        parts = PurePosixPath(path).relative_to(".github").parts
        for depth in range(1, len(parts) + 1):
            entries.add("/".join(parts[:depth]))
    return ModelCosmeticLintInput(
        spec_yaml=load_spec_yaml(),
        rules=load_rules(),
        python_files=[
            ModelSourceFile(path=path, source=source)
            for path, source in contents.items()
            if path.endswith(".py")
        ],
        pyproject_toml=contents.get("pyproject.toml"),
        precommit_config=contents.get(".pre-commit-config.yaml"),
        readme=contents.get("README.md"),
        github=(
            ModelCosmeticGithubSnapshot(entries=sorted(entries)) if entries else None
        ),
    )


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case.id)
def test_handler_reproduces_the_occ_decisions(case: _Case, tmp_path: Path) -> None:
    contents = _materialize(tmp_path, case)
    report = HandlerCosmeticLint().handle(_request(case, contents))
    assert [finding.message for finding in report.findings] == case.expected_stderr
    assert (report.overall_status == "FAIL") == (case.expected_exit == 1)


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case.id)
def test_entry_point_reproduces_the_occ_hook_on_a_tree(
    case: _Case,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _materialize(tmp_path, case)
    monkeypatch.chdir(tmp_path)
    assert main(["check"]) == case.expected_exit
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == case.expected_stderr


def test_entry_point_accepts_no_argument_and_refuses_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    assert main(["fix"]) == 2
    assert main(["check", "--select", "spdx"]) == 2


def test_spec_is_carried_byte_for_byte() -> None:
    # The manifest hash was taken from spec.yaml at the pinned onex_change_control rev.
    assert (
        hashlib.sha256(SPEC_FILE.read_bytes()).hexdigest() == _manifest()["spec_sha256"]
    )
    assert str(_manifest()["source_rev"]).startswith("8d7e85bc00e7")


def test_every_check_class_has_a_pass_a_fail_and_a_positive_control() -> None:
    cases = _cases()
    assert load_rules().checks == CHECK_PREFIXES
    for prefix in CHECK_PREFIXES:
        own = [c for c in cases if c.id.startswith(prefix)]
        assert any(c.expected_exit == 0 for c in own), f"no pass case for {prefix}"
        assert any(
            c.expected_exit == 1 and f"[{prefix}]" in "".join(c.expected_stderr)
            for c in own
        ), f"no fail case for {prefix}"
    control = next(c for c in cases if c.id == "all-classes-fail")
    reported = [
        line.split("[", 1)[1].split("]", 1)[0] for line in control.expected_stderr
    ]
    assert [p for p in CHECK_PREFIXES if p in reported] == list(CHECK_PREFIXES)
    assert reported == sorted(reported, key=CHECK_PREFIXES.index)


def test_verbatim_spi_tree_is_clean_and_a_mutation_of_it_is_not() -> None:
    cases = {c.id: c for c in _cases()}
    assert cases["spi-tree-pass"].expected_stderr == []
    assert cases["pyproject-fail-bare-license"].expected_stderr == [
        'pyproject.toml:0: [pyproject] License should be table format {text = "MIT"}, got bare string "MIT" [fixable]'
    ]


def test_spec_is_data_not_code() -> None:
    spec = yaml.safe_load(load_spec_yaml())
    spec["github"]["required_templates"] = ["CODEOWNERS"]
    request = ModelCosmeticLintInput(
        spec_yaml=yaml.safe_dump(spec),
        rules=load_rules(),
        github=ModelCosmeticGithubSnapshot(entries=["PULL_REQUEST_TEMPLATE.md"]),
    )
    report = HandlerCosmeticLint().handle(request)
    assert [f.message for f in report.findings] == [
        ".github/CODEOWNERS:0: [github] Missing required template: CODEOWNERS"
    ]


def test_select_python_paths_applies_the_spec_exclusions() -> None:
    paths = ["a.py", "pkg/migrations/0001.py", ".venv/lib/x.py", "docs/x.txt", "b/c.py"]
    assert select_python_paths(load_spec_yaml(), paths) == ["a.py", "b/c.py"]


def test_request_models_are_frozen_and_forbid_extra() -> None:
    with pytest.raises(ValueError):
        ModelCosmeticLintInput.model_validate(
            {"spec_yaml": "x", "rules": load_rules(), "surprise": 1}
        )
    for model in (
        ModelCosmeticLintInput,
        ModelCosmeticGithubSnapshot,
        ModelCosmeticLintRules,
    ):
        assert model.model_config["frozen"] is True
        assert model.model_config["extra"] == "forbid"


NODE_DIR = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "omnibase_core"
    / "nodes"
    / "node_cosmetic_lint_check_compute"
)
RULES_FILE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "omnibase_core"
    / "validation"
    / "contracts"
    / "cosmetic_lint.validation.yaml"
)


def test_the_node_contract_binds_the_handler() -> None:
    contract = yaml.safe_load((NODE_DIR / "contract.yaml").read_text(encoding="utf-8"))
    assert contract["node_type"] == "compute"
    module_name, _, class_name = contract["handler_routing"][
        "default_handler"
    ].partition(":")
    assert (NODE_DIR / f"{module_name}.py").is_file()
    assert (NODE_DIR / "runtime_cosmetic_lint_check.py").is_file()
    assert class_name == HandlerCosmeticLint.__name__
    assert HandlerCosmeticLint.__module__.endswith(
        f"node_cosmetic_lint_check_compute.{module_name}"
    )
    assert contract["input_model"].endswith(ModelCosmeticLintInput.__name__)


def test_the_handler_and_runtime_modules_hold_no_table() -> None:
    for module in ("handler_cosmetic_lint.py", "runtime_cosmetic_lint_check.py"):
        tree = ast.parse((NODE_DIR / module).read_text(encoding="utf-8"))
        for node in tree.body:
            if (
                isinstance(node, ast.Assign | ast.AnnAssign)
                and node.value is not None
                and "__all__" not in ast.unparse(node)
            ):
                assert not isinstance(
                    node.value, ast.Tuple | ast.Set | ast.Dict | ast.List
                ), f"{module}:{node.lineno} holds a table"


def _mutated_rows(
    rule_id: str, key: str, value: object
) -> dict[str, ModelValidatorRule]:
    document = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    for row in document["validation"]["rules"]:
        if row["rule_id"] == rule_id:
            assert key in row["parameters"]
            row["parameters"][key] = value
    return load_rule_rows(yaml.safe_dump(document))


def _messages(rules: ModelCosmeticLintRules, **snapshot: object) -> list[str]:
    request = ModelCosmeticLintInput.model_validate(
        {"spec_yaml": load_spec_yaml(), "rules": rules, **snapshot}
    )
    return [f.message for f in HandlerCosmeticLint().handle(request).findings]


def _badge_readme() -> str:
    spec = yaml.safe_load(load_spec_yaml())
    first = spec["readme"]["required_badges"][0]["pattern"]
    return "\n" * 40 + first + "\n"


def _differs(key: tuple[str, str], value: object, **snapshot: object) -> bool:
    base = _messages(load_rules(), **snapshot)
    mutated = _messages(build_rules(_mutated_rows(*key, value)), **snapshot)
    return base != mutated


# every parameters key of the rule rows -> the snapshot on which changing it changes the verdict
_MUTATIONS: dict[tuple[str, str], tuple[object, dict[str, object]]] = {
    ("spdx", "skip_marker"): (
        "no-such-marker",
        {"python_files": [ModelSourceFile(path="a.py", source="# spdx-skip\n")]},
    ),
    ("pyproject", "path"): ("other.toml", {"pyproject_toml": "[project]\n"}),
    ("precommit", "path"): (
        "other.yaml",
        {
            "precommit_config": "repos:\n- repo: https://github.com/astral-sh/ruff-pre-commit\n  rev: v0.0.1\n"
        },
    ),
    ("readme", "path"): ("OTHER.md", {"readme": "no badges\n"}),
    ("readme", "header_lines"): (60, {"readme": _badge_readme()}),
    ("github", "directory"): (
        ".other",
        {"github": ModelCosmeticGithubSnapshot(entries=["workflows"])},
    ),
}


@pytest.mark.parametrize("key", sorted(_MUTATIONS), ids=lambda k: ".".join(k))
def test_mutating_a_rule_parameter_changes_the_verdict(key: tuple[str, str]) -> None:
    value, snapshot = _MUTATIONS[key]
    assert _differs(key, value, **snapshot)


def test_every_rule_parameter_has_a_mutation_test() -> None:
    document = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    declared = {
        (row["rule_id"], name)
        for row in document["validation"]["rules"]
        for name in row["parameters"]
    }
    assert declared - {("cli_usage", "usage_message")} == set(_MUTATIONS)


def test_mutating_the_usage_message_changes_what_the_hook_prints(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["fix"]) == 2
    base = capsys.readouterr().err
    assert base == "usage: handler_cosmetic_lint [check]\n"
    monkeypatch.setattr(
        runtime,
        "load_rule_rows",
        lambda: _mutated_rows("cli_usage", "usage_message", "use it differently\n"),
    )
    assert main(["fix"]) == 2
    assert capsys.readouterr().err == "use it differently\n"


def test_disabling_a_rule_row_drops_its_check() -> None:
    document = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    for row in document["validation"]["rules"]:
        if row["rule_id"] == "readme":
            row["enabled"] = False
    rules = build_rules(load_rule_rows(yaml.safe_dump(document)))
    assert rules.checks == ("spdx", "pyproject", "precommit", "github")
    assert _messages(rules, readme="no badges\n") == []
