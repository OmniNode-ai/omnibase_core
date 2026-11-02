# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Single-class checker, contract and validator regressions (OMN-22003).

Ports both canonical-path regressions from the retired script's tests and
exercises the legacy scope, enum and path rules through the real checker.
"""

from __future__ import annotations

import builtins
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums import EnumSeverity
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    RuleParameterValue,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.validation.checker_single_class_per_file import (
    check_single_class_per_file,
)
from omnibase_core.validation.validator_single_class_per_file import (
    ValidatorSingleClassPerFile,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_MULTIPLE = b"class First:\n    pass\n\nclass Second:\n    pass\n"
_CANONICAL_PATHS = (
    "src/omnibase_core/models/delegation/wire/model_delegation_terminal_v2.py",
    "src/omnibase_core/validators/pydantic_extra_forbid.py",
)


def _contract() -> ModelValidatorSubcontract:
    return ValidatorSingleClassPerFile().contract


def _with_parameter(
    key: str, value: RuleParameterValue | None
) -> ModelValidatorSubcontract:
    contract = _contract()
    rule = contract.rules[0]
    parameters = dict(rule.parameters or {})
    if value is None:
        del parameters[key]
    else:
        parameters[key] = value
    return contract.model_copy(
        update={"rules": [rule.model_copy(update={"parameters": parameters})]}
    )


def _check(
    path: Path,
    *,
    relative: str = "src/module.py",
    repository_relative: str | None = None,
    contract: ModelValidatorSubcontract | None = None,
) -> tuple[ModelValidationIssue, ...]:
    return check_single_class_per_file(
        path,
        relative,
        path.read_bytes(),
        (contract or _contract()).rules,
        repository_relative_path=repository_relative,
    )


@pytest.fixture
def target(tmp_path: Path) -> Path:
    path = tmp_path / "module.py"
    path.write_bytes(_MULTIPLE)
    return path


@pytest.mark.parametrize("canonical", _CANONICAL_PATHS)
def test_canonical_exception_is_scoped_to_its_repository_path(
    canonical: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Port both old tests: relative/absolute canonical paths and violating shadows."""
    relative_path = Path(canonical)
    absolute_path = _ROOT / relative_path
    validator = ValidatorSingleClassPerFile()
    assert validator.validate_file(relative_path).is_valid
    assert validator.validate_file(absolute_path).is_valid

    shadow_parent = tmp_path.parent / f"single_class_scope_shadow_{tmp_path.name}"
    shadow_parent.mkdir()
    shadow_path = shadow_parent / relative_path.name
    shadow_path.write_bytes(_MULTIPLE)
    assert _check(shadow_path) != ()
    assert _check(shadow_path, relative=canonical, repository_relative=canonical) == ()
    monkeypatch.chdir(shadow_parent)
    assert not validator.validate_file(shadow_path).is_valid


@pytest.mark.parametrize("canonical", _CANONICAL_PATHS)
def test_matching_relative_path_in_another_repository_is_not_exempt(
    canonical: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shadow = tmp_path / canonical
    shadow.parent.mkdir(parents=True)
    shadow.write_bytes(_MULTIPLE)
    monkeypatch.chdir(tmp_path)
    assert not ValidatorSingleClassPerFile().validate_file(Path(canonical)).is_valid


@pytest.mark.parametrize(
    ("source", "refused"),
    [
        ("", False),
        ("def helper():\n    pass\n", False),
        ("class Only:\n    pass\n", False),
        (_MULTIPLE.decode(), True),
        ("class First(Enum):\n    pass\nclass Second(Enum):\n    pass\n", False),
        (
            "class First(enum.Enum):\n    pass\nclass Second(enum.Enum):\n    pass\n",
            False,
        ),
        ("class First(IntEnum):\n    pass\nclass Second(StrEnum):\n    pass\n", False),
        (
            "class First(enum.IntEnum):\n    pass\nclass Second(enum.StrEnum):\n    pass\n",
            False,
        ),
        (
            "class First(CustomEnumBase):\n    pass\nclass Second(EnumLike):\n    pass\n",
            False,
        ),
        ("class First(Enum):\n    pass\nclass Second:\n    pass\n", True),
        (
            "class First(StrEnum):\n    pass\nclass Second:\n    pass\nclass Third:\n    pass\n",
            True,
        ),
        (
            "class First(enum_like):\n    pass\nclass Second(enum_like):\n    pass\n",
            True,
        ),
        (
            "class First(factory()):\n    pass\nclass Second(factory()):\n    pass\n",
            True,
        ),
        (
            "class First(Generic[Enum]):\n    pass\nclass Second(Generic[Enum]):\n    pass\n",
            True,
        ),
        ("class Outer:\n    class Inner:\n        pass\n", False),
        (
            "def helper():\n    class Local:\n        pass\nclass Only:\n    pass\n",
            False,
        ),
        (
            "async def helper():\n    class Local:\n        pass\nclass Only:\n    pass\n",
            False,
        ),
        (
            "class Outer:\n    def helper(self):\n        class Local:\n            pass\n",
            False,
        ),
        (
            "if enabled:\n    class First:\n        pass\nclass Second:\n    pass\n",
            True,
        ),
        # Preserve the original visitor's boolean reset after a nested function.
        (
            "def outer():\n    def inner():\n        pass\n    class Local:\n        pass\nclass Only:\n    pass\n",
            True,
        ),
        ("class Broken(:\n", False),
        ("class First:\n    pass\nclass Second:\n    pass\nsyntax error\n", False),
    ],
)
def test_legacy_class_shapes(source: str, refused: bool, target: Path) -> None:
    target.write_text(source, encoding="utf-8")
    assert bool(_check(target)) is refused


def test_undecodable_source_is_skipped(target: Path) -> None:
    target.write_bytes(_MULTIPLE + b"\xff")
    assert _check(target) == ()


@pytest.mark.parametrize(
    "relative",
    [
        "src/tests/module.py",
        "src/test_module.py",
        "src/test_helpers/module.py",
        "src/archived/module.py",
        "src/archive/module.py",
        "repo/scripts/validation/module.py",
        "src/__init__.py",
        "src/singleton_holders.py",
        "src/validation/example/models.py",
        "src/module.txt",
    ],
)
def test_path_exemptions(relative: str, target: Path) -> None:
    assert _check(target, relative=relative) == ()


@pytest.mark.parametrize(
    "relative",
    [
        "tests/fixtures/module.py",
        "test_module.py",
        "archive/module.py",
        "scripts/validation/module.py",
        "src/module_test.py",
        "src/module_tests/module.py",
        "src/models.py",
        "src/validation_like/models.py",
        "src/other/model_delegation_terminal_v2.py",
        "src/other/pydantic_extra_forbid.py",
    ],
)
def test_paths_outside_the_literal_legacy_exemptions_are_judged(
    relative: str, target: Path
) -> None:
    assert _check(target, relative=relative) != ()


@pytest.mark.parametrize(
    "name", (_contract().rules[0].parameters or {})["exempt_names"]
)
def test_every_exempt_basename_is_honored(name: str, target: Path) -> None:
    assert _check(target, relative=f"src/{name}") == ()


def test_issue_has_contract_message_counts_location_and_severity(target: Path) -> None:
    target.write_bytes(_MULTIPLE + b"\nclass Signal(Enum):\n    pass\n")
    issues = _check(target)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == issue.rule_name == "multiple_classes"
    assert issue.file_path == target
    assert issue.line_number == 1
    assert issue.severity == EnumSeverity.ERROR
    assert issue.message.startswith(
        "Found 2 non-enum class(es) and 1 enum(s) in same file -- "
    )


def test_disabled_rule_emits_nothing(target: Path) -> None:
    contract = _contract()
    disabled = contract.model_copy(
        update={
            "rules": [
                rule.model_copy(update={"enabled": False}) for rule in contract.rules
            ]
        }
    )
    assert _check(target, contract=disabled) == ()


_PARAMETERS = sorted(_contract().rules[0].parameters or {})


@pytest.mark.parametrize("key", _PARAMETERS)
def test_missing_parameter_fails_to_load(key: str, target: Path) -> None:
    with pytest.raises(ModelOnexError, match="parameter"):
        _check(target, contract=_with_parameter(key, None))


@pytest.mark.parametrize(
    ("key", "value", "relative", "repository_relative"),
    [
        ("path_pattern", r"\.txt$", "src/module.py", None),
        ("exempt_path_markers", ["/module"], "src/module.py", None),
        ("exempt_names", ["module.py"], "src/module.py", None),
        (
            "exempt_repository_paths",
            ["src/module.py"],
            "src/module.py",
            "src/module.py",
        ),
        ("scoped_exempt_name", "module.py", "src/validation/module.py", None),
        ("scoped_exempt_path_marker", "src/", "src/models.py", None),
        ("enum_base_name_fragment", "object", "src/module.py", None),
        ("max_classes", 2, "src/module.py", None),
    ],
)
def test_rule_parameters_control_the_verdict(
    key: str,
    value: RuleParameterValue,
    relative: str,
    repository_relative: str | None,
    target: Path,
) -> None:
    if key == "enum_base_name_fragment":
        target.write_text(
            "class First(object):\n    pass\nclass Second(object):\n    pass\n"
        )
    assert _check(target, relative=relative, repository_relative=repository_relative)
    assert (
        _check(
            target,
            relative=relative,
            repository_relative=repository_relative,
            contract=_with_parameter(key, value),
        )
        == ()
    )


@pytest.mark.parametrize("key", ["message", "remediation"])
def test_message_parameters_control_the_issue_text(key: str, target: Path) -> None:
    issues = _check(target, contract=_with_parameter(key, "replacement-marker"))
    assert len(issues) == 1 and "replacement-marker" in issues[0].message


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("path_pattern", "("),
        ("max_classes", -1),
        ("max_classes", True),
        ("max_classes", "one"),
        ("exempt_names", "module.py"),
        ("exempt_path_markers", [""]),
        ("enum_base_name_fragment", ""),
        ("message", "{unknown}"),
        ("message", "{"),
        ("message", "{}"),
    ],
)
def test_unreadable_parameters_fail_to_load(
    key: str, value: RuleParameterValue, target: Path
) -> None:
    with pytest.raises(ModelOnexError, match="parameter"):
        _check(target, contract=_with_parameter(key, value))


def test_checker_is_pure_facts_in_issues_out(monkeypatch: pytest.MonkeyPatch) -> None:
    rules = _contract().rules

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker performed I/O")

    for name in ("read_text", "read_bytes", "open", "resolve", "cwd"):
        monkeypatch.setattr(Path, name, refuse)
    monkeypatch.setattr(builtins, "open", refuse)
    issues = check_single_class_per_file(
        Path("module.py"), "module.py", _MULTIPLE, rules
    )
    assert len(issues) == 1


def test_validator_reads_without_writing_and_expands_directories(
    target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(target.parent)
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    validator = ValidatorSingleClassPerFile()
    result = validator.validate(Path())
    assert not result.is_valid
    assert validator.get_exit_code(result) == 1
    assert [issue.file_path for issue in result.issues] == [Path(target.name)]
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before


def test_validator_skips_unreadable_files(
    target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(target.parent)

    def refuse(_path: Path) -> bytes:
        raise PermissionError("unreadable fixture")

    monkeypatch.setattr(Path, "read_bytes", refuse)
    assert ValidatorSingleClassPerFile().validate_file(Path(target.name)).is_valid


@pytest.mark.parametrize("absolute", [False, True])
def test_legacy_path_markers_survive_target_expansion(
    absolute: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "tests"
    directory.mkdir()
    path = directory / "fixture.py"
    path.write_bytes(_MULTIPLE)
    monkeypatch.chdir(tmp_path)
    validator = ValidatorSingleClassPerFile()
    file_target = path if absolute else Path("tests/fixture.py")
    directory_target = directory if absolute else Path("tests")
    assert validator.validate_file(file_target).is_valid is absolute
    assert validator.validate(directory_target).is_valid is absolute


def test_directory_scans_keep_symlinked_files_and_their_lexical_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "src" / "test_helpers" / "fixture.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(_MULTIPLE)
    alias = source.parent.parent / "module.py"
    alias.symlink_to(source)
    monkeypatch.chdir(tmp_path)
    result = ValidatorSingleClassPerFile().validate(Path("src"))
    assert [issue.file_path for issue in result.issues] == [Path("src/module.py")]


def test_generic_runtime_writes_the_verdict_through_the_report_node(
    target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(target.parent)
    report = target.parent / "report.json"
    code = main(
        ValidatorSingleClassPerFile,
        [target.name, "--report-json", str(report)],
        container_factory=build_validator_container,
    )
    assert code == 1
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["provenance"]["validators_run"] == ["single_class_per_file"]
    assert len(data["findings"]) == 1
    assert data["findings"][0]["rule_id"] == "multiple_classes"
    assert data["findings"][0]["location"] == "module.py:1"


def test_hook_uses_generic_runtime_and_retains_its_identity() -> None:
    data = yaml.safe_load(
        (_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    hook = next(
        hook
        for repo in data["repos"]
        for hook in repo.get("hooks", [])
        if hook["id"] == "onex-single-class-per-file"
    )
    assert hook["entry"] == (
        "env -u PYTHONPATH uv run python -m "
        "omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run "
        "omnibase_core.validation.validator_single_class_per_file:ValidatorSingleClassPerFile"
    )
    assert hook["pass_filenames"] is True
    assert hook["files"] == r"^src/.*\.py$"
    assert hook["stages"] == ["pre-commit"]
