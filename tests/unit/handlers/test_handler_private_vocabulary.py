# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the private-vocabulary resolution handler (OMN-21494, plan task T0.1).

Every validator that reads an operator-private vocabulary resolves it by name
through the container: ``HandlerPrivateVocabulary`` (pure, contract injected)
chooses the path in the contract's precedence order, the read effect observes
it, and the handler judges the fact. An explicit path comes first, then the
vocabulary's environment variable, then the workspace config root. A required
vocabulary that none of the three supplies is one refusal line naming the
setting. The cache age bound is a value of the vocabulary contract, never of the
handler. Fixture vocabularies are synthetic and hold no real name.
"""

from __future__ import annotations

import ast
import builtins
import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_private_vocabulary_source import (
    EnumPrivateVocabularySource,
)
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers import handler_private_vocabulary as handler_module
from omnibase_core.handlers.handler_private_vocabulary import HandlerPrivateVocabulary
from omnibase_core.handlers.handler_private_vocabulary_resolution import (
    PACKAGED_CONTRACT,
    build_container,
    resolve_private_vocabulary,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.private_vocabulary import (
    ModelPrivateVocabularyContract,
    ModelPrivateVocabularyFileFact,
    ModelPrivateVocabularyRequest,
    ModelPrivateVocabularyResolution,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
_HYGIENE = "public_repo_hygiene"
_HYGIENE_ENV = "OMNI_HYGIENE_VOCAB_PATH"
_ROOT_ENV = "ONEX_WORKSPACE_CONFIG_ROOT"
_DENYLIST = "hardcoded_model_config_lab_denylist"


def load_contract() -> ModelPrivateVocabularyContract:
    return load_yaml_content_as_model(
        PACKAGED_CONTRACT.read_text(encoding="utf-8"), ModelPrivateVocabularyContract
    )


@pytest.fixture(scope="module")
def container() -> ModelONEXContainer:
    return build_container()


def _hygiene_relative_path() -> str:
    entry = next(e for e in load_contract().vocabularies if e.name == _HYGIENE)
    return entry.relative_path


def _write(path: Path, body: str = "schema_version: 1\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _resolve(
    container: ModelONEXContainer,
    name: str = _HYGIENE,
    *,
    explicit: Path | None = None,
    environment: dict[str, str] | None = None,
) -> ModelPrivateVocabularyResolution:
    return resolve_private_vocabulary(
        container,
        name,
        environment=environment or {},
        now=_NOW,
        explicit_path=explicit,
    )


def test_packaged_contract_names_the_hygiene_vocabulary_and_its_setting() -> None:
    contract = load_contract()
    entry = next(e for e in contract.vocabularies if e.name == _HYGIENE)
    assert entry.env_var == _HYGIENE_ENV
    assert entry.required is True
    denylist = next(e for e in contract.vocabularies if e.name == _DENYLIST)
    assert denylist.required is False


def test_explicit_path_wins_over_environment_and_config_root(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    explicit = _write(tmp_path / "explicit.yaml")
    from_env = _write(tmp_path / "env.yaml")
    root = tmp_path / "root"
    _write(root / _hygiene_relative_path())
    result = _resolve(
        container,
        explicit=explicit,
        environment={_HYGIENE_ENV: str(from_env), _ROOT_ENV: str(root)},
    )
    assert result.path == explicit
    assert result.source is EnumPrivateVocabularySource.EXPLICIT


def test_environment_wins_over_config_root(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    from_env = _write(tmp_path / "env.yaml")
    root = tmp_path / "root"
    _write(root / _hygiene_relative_path())
    result = _resolve(
        container, environment={_HYGIENE_ENV: str(from_env), _ROOT_ENV: str(root)}
    )
    assert result.path == from_env
    assert result.source is EnumPrivateVocabularySource.ENVIRONMENT


def test_unset_variable_resolves_a_vocabulary_at_the_config_root(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    """The T0.1 falsifier: the variable is unset and the vocabulary sits at the
    config root, so the read succeeds instead of refusing."""
    root = tmp_path / "root"
    placed = _write(root / _hygiene_relative_path(), "schema_version: 1\n")
    result = _resolve(container, environment={_ROOT_ENV: str(root)})
    assert result.found is True
    assert result.path == placed
    assert result.source is EnumPrivateVocabularySource.WORKSPACE_CONFIG_ROOT
    assert result.text == "schema_version: 1\n"


def test_config_root_falls_back_to_the_omnibase_internal_sibling_of_home(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    home = tmp_path / "omni_home"
    home.mkdir()
    placed = _write(tmp_path / "omnibase_internal" / _hygiene_relative_path())
    result = _resolve(container, environment={"OMNI_HOME": str(home)})
    assert result.path is not None
    assert result.path.resolve() == placed.resolve()


def test_required_vocabulary_unset_everywhere_is_one_line_naming_the_setting(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    with pytest.raises(ModelOnexError) as caught:
        _resolve(container, environment={_ROOT_ENV: str(tmp_path / "empty-root")})
    message = caught.value.message
    assert _HYGIENE_ENV in message
    assert "\n" not in message


def test_required_vocabulary_with_no_root_at_all_is_the_same_refusal(
    container: ModelONEXContainer,
) -> None:
    with pytest.raises(ModelOnexError) as caught:
        _resolve(container)
    assert _HYGIENE_ENV in caught.value.message
    assert "\n" not in caught.value.message


def test_optional_vocabulary_unset_everywhere_is_not_found_not_a_refusal(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    result = _resolve(container, _DENYLIST, environment={_ROOT_ENV: str(tmp_path)})
    assert result.found is False
    assert result.path is None
    assert result.text is None
    assert result.source is None


def test_optional_vocabulary_resolves_from_the_config_root(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    entry = next(e for e in load_contract().vocabularies if e.name == _DENYLIST)
    placed = _write(tmp_path / entry.relative_path, "retired_values: []\n")
    result = _resolve(container, _DENYLIST, environment={_ROOT_ENV: str(tmp_path)})
    assert result.found is True
    assert result.path == placed


def test_an_environment_path_that_is_not_a_file_refuses_naming_the_variable(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    with pytest.raises(ModelOnexError) as caught:
        _resolve(container, environment={_HYGIENE_ENV: str(tmp_path / "missing.yaml")})
    assert _HYGIENE_ENV in caught.value.message
    assert "\n" not in caught.value.message


def test_an_explicit_path_that_is_not_a_file_refuses_even_when_optional(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(ModelOnexError) as caught:
        _resolve(container, _DENYLIST, explicit=missing)
    assert str(missing) in caught.value.message


def test_an_unknown_vocabulary_name_is_refused(container: ModelONEXContainer) -> None:
    with pytest.raises(ModelOnexError) as caught:
        _resolve(container, "no_such_vocabulary")
    assert "no_such_vocabulary" in caught.value.message


def _aged_contract_file(tmp_path: Path, max_age_days: int) -> Path:
    document = {
        "schema_version": 1,
        "workspace_config_root": {
            "env_var": _ROOT_ENV,
            "home_env_var": "OMNI_HOME",
            "home_sibling": "omnibase_internal",
        },
        "vocabularies": [
            {
                "name": "aged",
                "env_var": "AGED_VOCAB_PATH",
                "relative_path": "vocabularies/aged.yaml",
                "required": True,
                "resolved_at_key": "resolved_at",
                "max_age_days": max_age_days,
            }
        ],
    }
    return _write(tmp_path / "aged_contract.yaml", yaml.safe_dump(document))


def _aged_vocabulary(tmp_path: Path, days_old: int) -> Path:
    stamp = (_NOW - timedelta(days=days_old)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return _write(tmp_path / "aged.yaml", f'resolved_at: "{stamp}"\n')


@pytest.mark.parametrize(
    ("max_age_days", "expected_exceeded"), [(5, True), (30, False)]
)
def test_the_age_bound_is_the_contract_value_not_the_handlers(
    tmp_path: Path, max_age_days: int, expected_exceeded: bool
) -> None:
    path = _aged_vocabulary(tmp_path, days_old=10)
    aged = build_container(_aged_contract_file(tmp_path, max_age_days))
    result = _resolve(aged, "aged", explicit=path)
    assert result.age_days == 10
    assert result.max_age_days == max_age_days
    assert result.age_exceeded is expected_exceeded


def test_the_packaged_age_bound_is_read_from_the_contract_data_file() -> None:
    document = yaml.safe_load(PACKAGED_CONTRACT.read_text(encoding="utf-8"))
    declared = {v["name"]: v["max_age_days"] for v in document["vocabularies"]}
    bound = next(
        e.max_age_days for e in load_contract().vocabularies if e.name == _HYGIENE
    )
    assert bound == declared[_HYGIENE]
    assert "max_age" not in Path(handler_module.__file__).read_text(
        encoding="utf-8"
    ).replace("max_age_days", "")


def test_a_vocabulary_without_a_declared_bound_reports_no_age(
    container: ModelONEXContainer, tmp_path: Path
) -> None:
    entry = next(e for e in load_contract().vocabularies if e.name == _DENYLIST)
    _write(tmp_path / entry.relative_path, "retired_values: []\n")
    result = _resolve(container, _DENYLIST, environment={_ROOT_ENV: str(tmp_path)})
    assert result.age_days is None
    assert result.max_age_days is None
    assert result.age_exceeded is False


def test_an_unparseable_timestamp_is_refused_naming_the_key(tmp_path: Path) -> None:
    path = _write(tmp_path / "aged.yaml", 'resolved_at: "not a time"\n')
    aged = build_container(_aged_contract_file(tmp_path, 30))
    with pytest.raises(ModelOnexError) as caught:
        _resolve(aged, "aged", explicit=path)
    assert "resolved_at" in caught.value.message


# --- the handler is pure and takes its contract by injection ----------------


def _pure_handler() -> HandlerPrivateVocabulary:
    return build_container().get_service(HandlerPrivateVocabulary)


def _forbid(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("the pure handler performed I/O")


def test_the_handler_judges_facts_with_every_read_patched_to_raise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    handler = _pure_handler()
    path = tmp_path / "vocabulary.yaml"
    request = ModelPrivateVocabularyRequest(
        vocabulary_name=_HYGIENE,
        explicit_path=path,
        environment={},
        now=_NOW,
    )
    fact = ModelPrivateVocabularyFileFact(
        path=path, is_file=True, text="schema_version: 1\n", error=None
    )
    monkeypatch.setattr(builtins, "open", _forbid)
    monkeypatch.setattr(Path, "read_text", _forbid)
    monkeypatch.setattr(Path, "is_file", _forbid)
    monkeypatch.setattr(Path, "exists", _forbid)
    planned = handler.plan(request)
    assert planned is not None
    assert planned.path == path
    result = handler.handle(request.model_copy(update={"file_fact": fact}))
    assert result.found is True
    assert result.text == "schema_version: 1\n"


def test_the_handler_module_reads_no_clock_environment_or_file() -> None:
    tree = ast.parse(Path(handler_module.__file__).read_text(encoding="utf-8"))
    called = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert called.isdisjoint(
        {"now", "utcnow", "open", "read_text", "is_file", "getenv"}
    )
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "os" not in imported


def test_the_handler_has_no_default_contract_and_no_console_entry() -> None:
    parameters = inspect.signature(HandlerPrivateVocabulary).parameters
    assert list(parameters) == ["container"]
    assert parameters["container"].default is inspect.Parameter.empty
    assert not hasattr(handler_module, "main")
    assert not hasattr(handler_module, "request_from_process")
    assert not hasattr(handler_module, "load_contract")


def test_a_fact_for_another_path_is_refused(tmp_path: Path) -> None:
    handler = _pure_handler()
    request = ModelPrivateVocabularyRequest(
        vocabulary_name=_HYGIENE,
        explicit_path=tmp_path / "a.yaml",
        environment={},
        now=_NOW,
        file_fact=ModelPrivateVocabularyFileFact(
            path=tmp_path / "b.yaml", is_file=True, text="x: 1\n", error=None
        ),
    )
    with pytest.raises(ModelOnexError):
        handler.handle(request)
