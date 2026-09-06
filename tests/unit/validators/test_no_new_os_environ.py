# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Adversarial regression coverage for the raw-environment access gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators import no_new_os_environ as validator
from omnibase_core.validators.environment_reader_inventory import (
    READER_INVENTORY_BY_PATH,
    unassigned_reader_paths,
)


def _write(tmp_path: Path, relative_path: str, source: str) -> Path:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.unit
@pytest.mark.parametrize("root", ["src", "tests", "examples", "scripts"])
@pytest.mark.parametrize(
    ("source", "required_line"),
    [
        (
            "import os\nenvironment = os.environ\nVALUE = environment['TOKEN']\n",
            3,
        ),
        ("import os\nget = os.getenv\nVALUE = get('TOKEN')\n", 3),
        ("import os\nalias = os\nVALUE = alias.environ['TOKEN']\n", 3),
        ("import os\nVALUE = getattr(os, 'environ')['TOKEN']\n", 2),
        (
            "import os\nattribute = 'getenv'\nget = getattr(os, attribute)\n"
            "VALUE = get('TOKEN')\n",
            3,
        ),
    ],
)
def test_alias_and_getattr_readers_are_rejected_in_every_scanned_root(
    tmp_path: Path,
    root: str,
    source: str,
    required_line: int,
) -> None:
    """No source, test, example, or script path can bypass the AST gate."""
    findings = validator.validate_file(_write(tmp_path, f"{root}/reader.py", source))

    assert required_line in {finding.line for finding in findings}


@pytest.mark.unit
def test_module_alias_is_resolved_inside_a_function_scope(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "reader.py",
        "import os\nalias = os\ndef read() -> str | None:\n    return alias.getenv('TOKEN')\n",
    )

    assert 4 in {finding.line for finding in validator.validate_file(path)}


@pytest.mark.unit
def test_function_scope_shadowing_does_not_misclassify_a_local_mapping(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        "reader.py",
        "import os\nenvironment = os.environ\ndef read() -> str:\n"
        "    environment = {'TOKEN': 'typed'}\n    return environment['TOKEN']\n",
    )

    assert [finding.line for finding in validator.validate_file(path)] == [2]


@pytest.mark.unit
def test_from_os_function_alias_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "reader.py",
        "from os import getenv as get\nVALUE = get('TOKEN')\n",
    )

    assert [finding.line for finding in validator.validate_file(path)] == [2]


@pytest.mark.unit
def test_exact_capture_operation_is_the_only_bootstrap_exemption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write(
        tmp_path,
        "bootstrap/environment_bootstrap.py",
        "import os\nclass ModelEnvironmentBootstrap:\n    @classmethod\n"
        "    def capture_process_environment(cls, *, declared_keys):\n"
        "        return cls.from_mapping(os.environ, declared_keys=declared_keys)\n",
    )
    monkeypatch.setattr(validator, "_BOOTSTRAP_MODULE", path.resolve())

    assert validator.validate_file(path) == []


@pytest.mark.unit
def test_bootstrap_module_does_not_exempt_a_second_raw_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write(
        tmp_path,
        "bootstrap/environment_bootstrap.py",
        "import os\nclass ModelEnvironmentBootstrap:\n    @classmethod\n"
        "    def capture_process_environment(cls, *, declared_keys):\n"
        "        return cls.from_mapping(os.environ, declared_keys=declared_keys)\n"
        "def rogue() -> str | None:\n    return os.getenv('TOKEN')\n",
    )
    monkeypatch.setattr(validator, "_BOOTSTRAP_MODULE", path.resolve())

    assert [finding.line for finding in validator.validate_file(path)] == [7]


@pytest.mark.unit
@pytest.mark.parametrize(
    "source",
    [
        "import os\ndef capture_process_environment(cls, *, declared_keys):\n"
        "    return cls.from_mapping(os.environ, declared_keys=declared_keys)\n",
        "import os\nclass ForeignBootstrap:\n    @classmethod\n"
        "    def capture_process_environment(cls, *, declared_keys):\n"
        "        return cls.from_mapping(os.environ, declared_keys=declared_keys)\n",
        "import os\nclass ModelEnvironmentBootstrap:\n"
        "    def capture_process_environment(cls, *, declared_keys):\n"
        "        return cls.from_mapping(os.environ, declared_keys=declared_keys)\n",
    ],
)
def test_capture_name_alone_cannot_claim_the_bootstrap_exemption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    path = _write(tmp_path, "bootstrap/environment_bootstrap.py", source)
    monkeypatch.setattr(validator, "_BOOTSTRAP_MODULE", path.resolve())

    assert len(validator.validate_file(path)) == 1


@pytest.mark.unit
def test_validation_aggregates_every_supplied_path(tmp_path: Path) -> None:
    first = _write(tmp_path, "first.py", "import os\nos.environ['ONE']\n")
    second = _write(tmp_path, "second.py", "import os\nos.getenv('TWO')\n")

    assert len(validator.validate_paths([first, second])) == 2


@pytest.mark.unit
def test_validation_reports_an_explicit_missing_python_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.py"

    findings = validator.validate_paths([missing])

    assert len(findings) == 1
    assert findings[0].var_name == "<unreadable>"


@pytest.mark.unit
def test_validation_reports_invalid_utf8_as_unreadable(tmp_path: Path) -> None:
    path = tmp_path / "invalid-encoding.py"
    path.write_bytes(b"import os\n\xff\n")

    findings = validator.validate_file(path)

    assert len(findings) == 1
    assert findings[0].var_name == "<unreadable>"


@pytest.mark.unit
def test_ast_column_is_character_offset_after_non_ascii_prefix(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "reader.py",
        "import os\néé = 1; os.getenv('TOKEN')\n",
    )

    findings = validator.validate_file(path)

    assert [(finding.line, finding.col) for finding in findings] == [(2, 8)]


@pytest.mark.unit
def test_removed_src_argument_cannot_conceal_a_root() -> None:
    with pytest.raises(SystemExit):
        validator._parse_args(["--all", "--src", "src"])


@pytest.mark.unit
def test_main_all_scans_each_of_the_four_default_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    roots = ("src", "tests", "examples", "scripts")
    for root in roots:
        _write(tmp_path, f"{root}/reader.py", "import os\nos.getenv('TOKEN')\n")
    monkeypatch.chdir(tmp_path)

    assert validator.main(["--all"]) == 1

    stderr = capsys.readouterr().err
    assert all(f"{root}/reader.py" in stderr for root in roots)


@pytest.mark.unit
def test_main_reports_an_unreadable_python_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing.py"

    assert validator.main([str(missing)]) == 1

    assert "<unreadable>" in capsys.readouterr().err


@pytest.mark.unit
def test_main_reports_a_python_syntax_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "invalid.py", "def unfinished(:\n")

    assert validator.main([str(path)]) == 1

    assert "<syntax-error>" in capsys.readouterr().err


@pytest.mark.unit
def test_inventory_assigns_every_approved_reader_path_to_a_disposition() -> None:
    assigned_path = Path("src/omnibase_core/artifacts/artifact_store.py")

    assignment = READER_INVENTORY_BY_PATH[assigned_path.as_posix()]

    assert assignment.owner == "OMN-17744"
    assert assignment.disposition == "migrate-to-typed-bootstrap-injection"
    assert unassigned_reader_paths([assigned_path]) == ()


@pytest.mark.unit
def test_inventory_report_marks_a_new_reader_path_unassigned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path, "src/new_reader.py", "import os\nos.getenv('TOKEN')\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(validator, "_DEFAULT_ROOTS", (Path("src"),))

    assert validator.main(["--all", "--inventory"]) == 1

    stdout = capsys.readouterr().out
    assert "unassigned=1" in stdout
    assert "src/new_reader.py: UNASSIGNED" in stdout
