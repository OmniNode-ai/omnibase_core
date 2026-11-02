# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Stub checker/validator parity, contract parameters and report writing (OMN-22003).

Ports every scenario of the script suite, replacing its placeholder assertions
with real checker, file validator and generic-runtime verdicts.
"""

from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    RuleParameterValue,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    main_for_reference,
    validator_class,
)
from omnibase_core.validation.checker_stub_implementations import (
    check_stub_implementations,
)
from omnibase_core.validation.validator_stub_implementations import (
    ValidatorStubImplementations,
)

pytestmark = pytest.mark.unit

_LEADER = "#"

_REFERENCE = "omnibase_core.validation.validator_stub_implementations:ValidatorStubImplementations"
_STUB = "def unfinished():\n    pass\n"


def _contract() -> ModelValidatorSubcontract:
    return ValidatorStubImplementations().contract


def _with_parameter(key: str, value: RuleParameterValue) -> ModelValidatorSubcontract:
    contract = _contract()
    rules = [
        rule.model_copy(update={"parameters": {**(rule.parameters or {}), key: value}})
        for rule in contract.rules
    ]
    return contract.model_copy(update={"rules": rules})


def _check(
    tmp_path: Path, source: str, name: str = "module.py"
) -> tuple[ModelValidationIssue, ...]:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return check_stub_implementations(path, name, path.read_bytes(), _contract().rules)


def test_todo_marker_approval_is_line_local() -> None:
    from omnibase_core.validation.todo_marker.handler import scan_source

    source = (
        f"# TODO detector literal {_LEADER} onex-allow-todo-marker OMN-17522 detector literal\n"
        "# FIXME genuine unfinished work"
    )
    assert [finding.line for finding in scan_source(source).findings] == [2]


@pytest.mark.parametrize(
    ("body", "kind"),
    [
        ('"""This is a stub."""\n    pass', "only_pass"),
        ('"""This is a stub."""\n    ...', "only_ellipsis"),
        ('raise NotImplementedError("unfinished")', "not_implemented_error"),
        ('"""This function does nothing."""', "empty_body"),
        ("pass\n    return True", "pass_return"),
        ('"""TODO: implement this function."""\n    return None', "todo_in_docstring"),
    ],
)
def test_detection_patterns(tmp_path: Path, body: str, kind: str) -> None:
    issues = _check(tmp_path, f"def stub_function():\n    {body}\n")
    assert [issue.rule_name for issue in issues] == [kind]
    assert issues[0].file_path == tmp_path / "module.py"
    expected_line = 2 if kind in {"not_implemented_error", "pass_return"} else 1
    assert issues[0].line_number == expected_line


def test_staleness_marker_is_not_a_generic_stub_synonym(tmp_path: Path) -> None:
    assert not _check(
        tmp_path,
        'def describe():\n    """Describe the stub detector contract."""\n    return None\n',
    )


def test_todo_docstring_remains_a_real_violation(tmp_path: Path) -> None:
    issues = _check(
        tmp_path,
        'def unfinished():\n    """TODO: provide an implementation."""\n    return None\n',
    )
    assert [issue.code for issue in issues] == ["todo_in_docstring"]


@pytest.mark.parametrize("marker", ["TODO", "FIXME", "XXX", "todo", "fixme", "xxx"])
def test_work_item_markers(tmp_path: Path, marker: str) -> None:
    assert _check(tmp_path, f'def f():\n    """{marker}: finish."""\n    return None\n')


@pytest.mark.parametrize(
    "base",
    [
        "ABC",
        "ABCMeta",
        "abc.ABC",
        "abc.ABCMeta",
        "Protocol",
        "typing.Protocol",
        "Protocol[T]",
        "typing.Protocol[T]",
    ],
)
def test_exclude_abstract_and_protocol_classes(tmp_path: Path, base: str) -> None:
    assert not _check(
        tmp_path, f"class Base({base}):\n    def method(self):\n        pass\n"
    )


@pytest.mark.parametrize(
    "decorator", ["abstractmethod", "abc.abstractmethod", "overload", "typing.overload"]
)
def test_exclude_decorated_functions(tmp_path: Path, decorator: str) -> None:
    assert not _check(tmp_path, f"@{decorator}\ndef f():\n    pass\n")


def test_exclude_pyi_file(tmp_path: Path) -> None:
    assert not _check(tmp_path, _STUB, "module.pyi")


@pytest.mark.parametrize("marker", [f"{_LEADER} stub-ok", f"{_LEADER} noqa: stub"])
def test_exclude_stub_ok_comment(tmp_path: Path, marker: str) -> None:
    assert not _check(tmp_path, f"def intentional_stub():  {marker}\n    pass\n")
    assert not _check(
        tmp_path, f"def intentional_stub():\n    raise NotImplementedError  {marker}\n"
    )
    assert _check(tmp_path, f"def unapproved():\n    pass  {marker}\n")


def test_exclude_dunder_methods(tmp_path: Path) -> None:
    assert not _check(
        tmp_path,
        "class C:\n    def __str__(self):\n        pass\n    def __repr__(self):\n        pass\n    def __eq__(self, other):\n        pass\n",
    )
    assert _check(tmp_path, "class C:\n    def __init__(self):\n        pass\n")


@pytest.mark.parametrize(
    "name",
    [
        "test_something.py",
        "tests/conftest.py",
        "tests/fixture.py",
        "examples/demo.py",
        "prototypes/demo.py",
        "archived/old.py",
        "archive/old.py",
        "conftest.py",
        "src/test_helper.py",
    ],
)
def test_default_exclusions(tmp_path: Path, name: str) -> None:
    # The old script sees directory separators before directory exclusion names.
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_STUB, encoding="utf-8")
    assert not check_stub_implementations(
        path, f"./{name}", path.read_bytes(), _contract().rules
    )


@pytest.mark.parametrize(
    "source",
    [
        'def valid_function(data):\n    """Process and return data."""\n    if not data:\n        raise ValueError("empty")\n    return [item.strip() for item in data]\n',
        "def valid_function(condition):\n    if condition:\n        result = process()\n    else:\n        pass\n    return result\n",
        "class Child(Parent):\n    def __init__(self):\n        super().__init__()\n",
    ],
)
def test_valid_implementations(tmp_path: Path, source: str) -> None:
    assert not _check(tmp_path, source)


@pytest.mark.parametrize(
    "source",
    [
        "async def f():\n    pass\n",
        "def f():\n    raise builtins.NotImplementedError('unfinished')\n",
        "def f():\n    raise NotImplementedError\n",
        "def outer():\n    def inner():\n        pass\n    return inner\n",
    ],
)
def test_additional_detection_shapes(tmp_path: Path, source: str) -> None:
    assert len(_check(tmp_path, source)) == 1


@pytest.mark.parametrize(
    "source",
    [
        "def f():\n    if condition:\n        raise NotImplementedError\n",
        "def f():\n    raise builtins.NotImplementedError\n",
        "class C(ABC[T]):\n    def __str__(self):\n        pass\n",
        f"def outer():  {_LEADER} stub-ok\n    def inner():\n        pass\n",
        "class C(ABC):\n    class Inner:\n        def __str__(self):\n            pass\n",
    ],
)
def test_legacy_scope_and_raise_boundaries(tmp_path: Path, source: str) -> None:
    assert not _check(tmp_path, source)


def test_nested_class_resets_exemption_and_restores_outer_scope(tmp_path: Path) -> None:
    source = "class Outer(ABC):\n    class Inner:\n        def f(self):\n            pass\n    def exempt(self):\n        pass\n"
    assert [i.line_number for i in _check(tmp_path, source)] == [3]


def test_pattern_precedence_and_multiple_findings(tmp_path: Path) -> None:
    assert [
        i.code for i in _check(tmp_path, 'def f():\n    """TODO"""\n    pass\n')
    ] == ["only_pass"]
    assert [
        i.code
        for i in _check(
            tmp_path,
            'def f():\n    """TODO"""\n    pass\n    return None\n    raise NotImplementedError\n',
        )
    ] == ["not_implemented_error"]
    assert [
        i.code
        for i in _check(
            tmp_path,
            'def f():\n    """TODO"""\n    pass\n    return None\n    pass\n    return None\n',
        )
    ] == ["pass_return", "pass_return", "todo_in_docstring"]


def test_load_config_file(tmp_path: Path) -> None:
    # The contract replaces --config; excluded_functions was inert in the script.
    contract = _with_parameter("exempt_files", ["custom_stub.py"])
    config_path = tmp_path / "custom.validation.yaml"
    config_path.write_text(
        yaml.safe_dump({"validation": contract.model_dump(mode="json")}),
        encoding="utf-8",
    )
    loaded = ModelValidatorSubcontract.model_validate(
        yaml.safe_load(config_path.read_text())["validation"]
    )
    assert not check_stub_implementations(
        Path("custom_stub.py"), "custom_stub.py", _STUB.encode(), loaded.rules
    )
    contract = _with_parameter("exempt_path_markers", ["/custom_path/"])
    assert not check_stub_implementations(
        Path("module.py"), "src/custom_path/module.py", _STUB.encode(), contract.rules
    )


@pytest.mark.parametrize("content", [b"def broken_syntax(:\n    pass\n", b"\xff\xfe"])
def test_error_handling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: bytes
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "broken.py"
    target.write_bytes(content)
    assert not check_stub_implementations(
        target, target.name, content, _contract().rules
    )
    assert ValidatorStubImplementations().validate_file(target).is_valid


def test_unreadable_file_handling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(_path: Path) -> bytes:
        raise PermissionError("unreadable fixture")

    monkeypatch.setattr(Path, "read_bytes", refuse)
    assert not ValidatorStubImplementations()._validate_file(
        tmp_path / "module.py", _contract()
    )


def test_missing_file_handling(tmp_path: Path) -> None:
    assert main_for_reference([_REFERENCE, str(tmp_path / "missing.py")]) == 1


def test_multiple_files_and_directory_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    first = tmp_path / "first.py"
    second = tmp_path / "nested/second.py"
    second.parent.mkdir()
    first.write_text(_STUB, encoding="utf-8")
    second.write_text("def f():\n    ...\n", encoding="utf-8")
    (tmp_path / "excluded.pyi").write_text(_STUB, encoding="utf-8")
    validator = ValidatorStubImplementations()
    explicit = validator.validate([first, second])
    recursive = validator.validate(tmp_path)
    assert explicit.issues == recursive.issues
    assert [i.file_path for i in explicit.issues] == [first, second]


@pytest.mark.parametrize("valid", [True, False])
def test_runtime_output_and_report_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    valid: bool,
) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "module.py"
    source = "def f():\n    return None\n" if valid else _STUB
    target.write_text(source, encoding="utf-8")
    assert validator_class(_REFERENCE) is ValidatorStubImplementations
    assert main_for_reference([_REFERENCE, str(target), "--verbose"]) == (
        0 if valid else 1
    )
    report = json.loads(
        (
            tmp_path / ".onex_state/validation/stub_implementations.report.json"
        ).read_text()
    )
    assert len(report["findings"]) == (0 if valid else 1)
    output = capsys.readouterr().out
    if not valid:
        assert "only_pass" in output
        assert report["findings"][0]["rule_id"] == "only_pass"
        assert report["findings"][0]["location"] == "module.py:1"
        assert "Implement actual logic" in report["findings"][0]["message"]
    assert target.read_text() == source


@pytest.mark.parametrize(
    ("name", "fragment"),
    [
        ("__init__", "Initialize instance attributes"),
        ("get_data", "Implement getter logic"),
        ("set_data", "Implement setter logic"),
        ("validate_data", "Implement validation logic"),
        ("process_data", "Implement processing logic"),
        ("other", "Implement actual logic"),
    ],
)
def test_fix_suggestion_output(tmp_path: Path, name: str, fragment: str) -> None:
    assert fragment in _check(tmp_path, f"def {name}():\n    pass\n")[0].message


def test_documented_suggestion_excerpt(tmp_path: Path) -> None:
    docstring = "A" * 90
    issue = _check(tmp_path, f'def f():\n    """{docstring}"""\n    pass\n')[0]
    assert f"{'A' * 80}..." in issue.message
    assert "A" * 81 not in issue.message


def test_checker_is_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    rules = _contract().rules

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker performed I/O")

    monkeypatch.setattr(builtins, "open", refuse)
    for name in ("read_text", "read_bytes", "open"):
        monkeypatch.setattr(Path, name, refuse)
    assert check_stub_implementations(
        Path("module.py"), "module.py", _STUB.encode(), rules
    )


@pytest.mark.parametrize("rule_id", [rule.rule_id for rule in _contract().rules])
def test_disabled_rules(tmp_path: Path, rule_id: str) -> None:
    contract = _contract()
    rules = [
        r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
        for r in contract.rules
    ]
    source = 'def f():\n    """TODO"""\n    pass\n    return None\n\ndef g():\n    pass\n\ndef h():\n    ...\n\ndef i():\n    raise NotImplementedError\n\ndef j():\n    """documentation"""\n'
    target = tmp_path / "module.py"
    target.write_text(source, encoding="utf-8")
    issues = check_stub_implementations(target, target.name, target.read_bytes(), rules)
    assert rule_id not in [issue.rule_name for issue in issues]
    assert len(issues) == 5


@pytest.mark.parametrize("key", sorted(_contract().rules[0].parameters or {}))
def test_missing_parameter_fails_to_load(key: str) -> None:
    rule = _contract().rules[0]
    parameters = dict(rule.parameters or {})
    del parameters[key]
    with pytest.raises(ModelOnexError):
        check_stub_implementations(
            Path("module.py"),
            "module.py",
            _STUB.encode(),
            [rule.model_copy(update={"parameters": parameters})],
        )


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("kind", "bogus"),
        ("path_pattern", "("),
        ("single_statement_count", True),
        ("docstring_excerpt_length", -1),
        ("suggestion_prefixes", []),
        ("work_item_pattern", ""),
        ("approval_markers", [""]),
    ],
)
def test_invalid_parameters_fail_to_load(key: str, value: RuleParameterValue) -> None:
    with pytest.raises(ModelOnexError):
        check_stub_implementations(
            Path("module.py"),
            "module.py",
            _STUB.encode(),
            _with_parameter(key, value).rules,
        )


def test_message_and_remediation_are_contract_parameters(tmp_path: Path) -> None:
    contract = _with_parameter("message", "custom {function_name}")
    contract = contract.model_copy(
        update={
            "rules": [
                r.model_copy(
                    update={
                        "parameters": {**(r.parameters or {}), "remediation": "repair"}
                    }
                )
                for r in contract.rules
            ]
        }
    )
    issue = check_stub_implementations(
        tmp_path / "module.py", "module.py", _STUB.encode(), contract.rules
    )[0]
    assert issue.message == "custom unfinished -- repair"


def test_invalid_message_template_fails_to_load() -> None:
    contract = _with_parameter("message", "{unknown}")
    with pytest.raises(ModelOnexError, match="message template"):
        check_stub_implementations(
            Path("module.py"), "module.py", _STUB.encode(), contract.rules
        )


@pytest.fixture
def sample_stub_file(tmp_path: Path) -> Path:
    """Create a sample file with various stub patterns."""
    code = '''
"""Sample module with various stub patterns."""

from abc import ABC, abstractmethod
from typing import Protocol


class ValidClass:
    """A valid class with proper implementations."""

    def __init__(self):
        """Initialize the class."""
        self.data = []

    def valid_method(self):
        """A properly implemented method."""
        return len(self.data)


class StubClass:
    """A class with stub methods."""

    def stub_pass(self):
        """Stub using pass."""
        pass

    def stub_ellipsis(self):
        """Stub using ellipsis."""
        ...

    def stub_not_implemented(self):
        """Stub using NotImplementedError."""
        raise NotImplementedError("TODO: implement this")

    def stub_with_todo(self):
        """TODO: implement this method."""
        return None


class MyProtocol(Protocol):
    """Protocol class - stubs are OK here."""

    def protocol_method(self):
        """Protocol methods can be stubs."""
        ...


class MyAbstract(ABC):
    """Abstract class - stubs are OK here."""

    @abstractmethod
    def abstract_method(self):
        """Abstract methods can be stubs."""
        pass
'''

    file_path = tmp_path / "sample_stub.py"
    file_path.write_text(code)
    return file_path


@pytest.fixture
def sample_valid_file(tmp_path: Path) -> Path:
    """Create a sample file with valid implementations."""
    code = '''
"""Sample module with valid implementations."""


def process_data(data: list) -> list:
    """Process and validate data."""
    if not data:
        raise ValueError("Data cannot be empty")

    result = []
    for item in data:
        if item is not None:
            result.append(str(item).strip())

    return result


def calculate(x: int, y: int) -> int:
    """Calculate sum with validation."""
    if not isinstance(x, int) or not isinstance(y, int):
        raise TypeError("Arguments must be integers")

    return x + y


class DataProcessor:
    """Data processor with full implementation."""

    def __init__(self, config: dict):
        """Initialize processor with config."""
        self.config = config
        self.results = []

    def process(self, data: list) -> list:
        """Process data according to config."""
        processed = []
        for item in data:
            if self._should_include(item):
                processed.append(self._transform(item))
        return processed

    def _should_include(self, item) -> bool:
        """Check if item should be included."""
        return item is not None

    def _transform(self, item):
        """Transform item according to config."""
        return str(item).upper()
'''

    file_path = tmp_path / "sample_valid.py"
    file_path.write_text(code)
    return file_path


def test_sample_files(
    sample_stub_file: Path, sample_valid_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(sample_stub_file.parent)
    result = ValidatorStubImplementations().validate(
        [sample_stub_file, sample_valid_file]
    )
    assert sorted(issue.code for issue in result.issues if issue.code is not None) == [
        "not_implemented_error",
        "only_ellipsis",
        "only_pass",
        "todo_in_docstring",
    ]
    assert all(issue.file_path == sample_stub_file for issue in result.issues)
