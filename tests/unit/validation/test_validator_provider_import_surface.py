# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A provider change removes nothing its consumers import (OMN-22478).

The failing control is the shape omnibase_infra#5683 had: a package removed from the
provider, its directory left holding compiled leftovers, and a consumer that loads it
at module scope, with every test of the provider passing.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.validation.model_provider_import_surface_input import (
    ModelProviderImportSurfaceInput,
)
from omnibase_core.validation.checker_provider_import_surface import (
    RULE_NOTHING_READ,
    RULE_REMOVED,
    RULE_UNPARSEABLE,
    check_provider_import_surface,
    check_something_read,
    provider_module_fact,
)
from omnibase_core.validation.validator_provider_import_surface import (
    ValidatorProviderImportSurface,
    read_provider_tree,
)

pytestmark = pytest.mark.unit

PACKAGE = "prov"
OLD_PACKAGE_INIT = "prov/handlers/models/infisical/__init__.py"
OLD_IMPORT = "from prov.handlers.models.infisical import Config\n"
TREE: dict[str, str] = {
    "prov/__init__.py": "",
    "prov/handlers/__init__.py": "",
    "prov/handlers/models/__init__.py": "",
    OLD_PACKAGE_INIT: "class Config:\n    pass\n",
    "prov/models/__init__.py": "VALUE = 1\n",
    "prov/models/security.py": "class Config:\n    pass\n",
}


def _write(root: Path, tree: dict[str, str]) -> Path:
    for relative, source in tree.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


def _without(*paths: str) -> dict[str, str]:
    return {key: value for key, value in TREE.items() if key not in paths}


@pytest.fixture
def validator_rules() -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in ValidatorProviderImportSurface().contract.rules}


def _issues(
    tmp_path: Path,
    rules: dict[str, ModelValidatorRule],
    head: dict[str, str],
    consumer: str,
    base: dict[str, str] = TREE,
) -> list[str]:
    request = ModelProviderImportSurfaceInput(
        provider_package=PACKAGE,
        head=read_provider_tree(_write(tmp_path / "head", head), PACKAGE),
        base=read_provider_tree(_write(tmp_path / "base", base), PACKAGE),
        consumers=(ModelSourceFile(path="consumer.py", source=consumer),),
    )
    return [i.code or "" for i in check_provider_import_surface(request, rules)]


def test_removed_package_a_consumer_loads_is_refused(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    head = _write(tmp_path / "head", _without(OLD_PACKAGE_INIT))
    leftover = head / "prov/handlers/models/infisical/__pycache__"
    leftover.mkdir(parents=True)
    (leftover / "__init__.cpython-313.pyc").write_bytes(b"\x00")
    request = ModelProviderImportSurfaceInput(
        provider_package=PACKAGE,
        head=read_provider_tree(head, PACKAGE),
        base=read_provider_tree(_write(tmp_path / "base", TREE), PACKAGE),
        consumers=(ModelSourceFile(path="consumer.py", source=OLD_IMPORT),),
    )
    issues = check_provider_import_surface(request, validator_rules)
    assert [i.code for i in issues] == [RULE_REMOVED]
    assert issues[0].line_number == 1
    assert "prov.handlers.models.infisical.Config" in issues[0].message


def test_old_path_kept_as_a_reexport_passes(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    head = {
        **TREE,
        OLD_PACKAGE_INIT: "from prov.models.security import Config\n",
    }
    assert _issues(tmp_path, validator_rules, head, OLD_IMPORT) == []


def test_alias_assignment_counts_as_the_name(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    head = {
        **TREE,
        OLD_PACKAGE_INIT: "from prov.models.security import New\nConfig = New\n",
    }
    assert _issues(tmp_path, validator_rules, head, OLD_IMPORT) == []


def test_name_removed_from_a_module_that_stays_is_refused(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    head = {**TREE, OLD_PACKAGE_INIT: "class Other:\n    pass\n"}
    assert _issues(tmp_path, validator_rules, head, OLD_IMPORT) == [RULE_REMOVED]


def test_function_scope_import_counts(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    consumer = "def f():\n    from prov.handlers.models.infisical import Config\n"
    assert _issues(tmp_path, validator_rules, _without(OLD_PACKAGE_INIT), consumer) == [
        RULE_REMOVED
    ]


def test_plain_import_statement_counts(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    consumer = "import prov.handlers.models.infisical as i\n"
    assert _issues(tmp_path, validator_rules, _without(OLD_PACKAGE_INIT), consumer) == [
        RULE_REMOVED
    ]


@pytest.mark.parametrize(
    "consumer",
    [
        f"from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    {OLD_IMPORT}",
        f"import typing\nif typing.TYPE_CHECKING:\n    {OLD_IMPORT}",
    ],
)
def test_type_checking_import_does_not_count(
    tmp_path: Path,
    validator_rules: dict[str, ModelValidatorRule],
    consumer: str,
) -> None:
    assert (
        _issues(tmp_path, validator_rules, _without(OLD_PACKAGE_INIT), consumer) == []
    )


def test_runtime_branch_of_a_type_checking_guard_counts(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    consumer = f"if TYPE_CHECKING:\n    pass\nelse:\n    {OLD_IMPORT}"
    assert _issues(tmp_path, validator_rules, _without(OLD_PACKAGE_INIT), consumer) == [
        RULE_REMOVED
    ]


def test_import_already_broken_at_the_base_is_not_this_changes_doing(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    consumer = "from prov.bus.kafka_producer import Client\n"
    assert _issues(tmp_path, validator_rules, TREE, consumer) == []


def test_removing_what_no_consumer_imports_passes(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    consumer = "from prov.models.security import Config\n"
    assert (
        _issues(tmp_path, validator_rules, _without(OLD_PACKAGE_INIT), consumer) == []
    )


def test_other_packages_and_relative_imports_are_not_read(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    consumer = "import provider_other\nfrom .prov import thing\nfrom provx.a import b\n"
    assert (
        _issues(tmp_path, validator_rules, _without(OLD_PACKAGE_INIT), consumer) == []
    )


def test_submodule_imported_from_its_package_resolves(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    consumer = "from prov.models import security\n"
    assert _issues(tmp_path / "kept", validator_rules, TREE, consumer) == []
    head = _without("prov/models/security.py")
    assert _issues(tmp_path / "gone", validator_rules, head, consumer) == [RULE_REMOVED]


@pytest.mark.parametrize(
    "source",
    [
        "from elsewhere import *\n",
        "def __getattr__(name):\n    raise AttributeError(name)\n",
        "def broken(:\n",
    ],
)
def test_module_static_reading_cannot_list_is_opaque(source: str) -> None:
    assert provider_module_fact("m", source).opaque is True


def test_names_in_conditional_branches_count() -> None:
    source = (
        "try:\n    import fast as Impl\nexcept ImportError:\n    Other = 1\n"
        "if X:\n    Value: int = 1\n"
    )
    assert {"Impl", "Other", "Value"} <= provider_module_fact("m", source).names


def test_consumer_that_does_not_parse_is_refused(
    tmp_path: Path, validator_rules: dict[str, ModelValidatorRule]
) -> None:
    assert _issues(tmp_path, validator_rules, TREE, "def broken(:\n") == [
        RULE_UNPARSEABLE
    ]


@pytest.mark.parametrize(
    ("head", "base", "consumers", "expected"),
    [
        ((), (), (), 3),
        (("h",), ("b",), (), 1),
        ((), ("b",), ("c",), 1),
        (("h",), (), ("c",), 1),
        (("h",), ("b",), ("c",), 0),
    ],
)
def test_a_run_that_read_nothing_is_refused(
    validator_rules: dict[str, ModelValidatorRule],
    head: tuple[str, ...],
    base: tuple[str, ...],
    consumers: tuple[str, ...],
    expected: int,
) -> None:
    request = ModelProviderImportSurfaceInput(
        provider_package=PACKAGE,
        head=tuple(provider_module_fact(m, "") for m in head),
        base=tuple(provider_module_fact(m, "") for m in base),
        consumers=tuple(ModelSourceFile(path=c, source="") for c in consumers),
    )
    issues = check_something_read(request, validator_rules)
    assert len(issues) == expected
    assert {i.code for i in issues} <= {RULE_NOTHING_READ}


def _cli(head: Path, base: Path, *consumers: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validation.validator_provider_import_surface",
            "--provider-package",
            PACKAGE,
            "--provider-head",
            str(head),
            "--provider-base",
            str(base),
            *map(str, consumers),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_refuses_the_removal_and_passes_the_reexport(tmp_path: Path) -> None:
    base = _write(tmp_path / "base", TREE)
    consumer = _write(tmp_path / "consumer", {"pkg/uses.py": OLD_IMPORT})
    removed = _write(tmp_path / "removed", _without(OLD_PACKAGE_INIT))
    kept = _write(
        tmp_path / "kept",
        {**TREE, OLD_PACKAGE_INIT: "from prov.models.security import Config\n"},
    )
    refused = _cli(removed, base, consumer)
    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert "prov.handlers.models.infisical.Config" in refused.stdout
    passed = _cli(kept, base, consumer)
    assert passed.returncode == 0, passed.stdout + passed.stderr


def test_cli_refuses_a_consumer_path_with_no_source(tmp_path: Path) -> None:
    base = _write(tmp_path / "base", TREE)
    empty = tmp_path / "empty"
    empty.mkdir()
    refused = _cli(base, base, empty)
    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert "No consumer source was read" in refused.stdout
