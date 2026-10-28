# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the private-vocabulary resolution handler (OMN-21433, plan task T0.1).

Every validator that reads an operator-private vocabulary resolves it by name
through ``HandlerPrivateVocabulary``: an explicit path first, then the
vocabulary's environment variable, then the workspace config root. A required
vocabulary that none of the three supplies is one refusal line naming the
setting. The cache age bound is a value of the vocabulary contract, never of the
handler. Fixture vocabularies are synthetic and hold no real name.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from omnibase_core.enums.enum_private_vocabulary_source import (
    EnumPrivateVocabularySource,
)
from omnibase_core.handlers.handler_private_vocabulary import (
    DEFAULT_CONTRACT,
    HandlerPrivateVocabulary,
    load_contract,
    main,
)
from omnibase_core.models.private_vocabulary import (
    ModelPrivateVocabularyContract,
    ModelPrivateVocabularyRequest,
)

from omnibase_core.errors.model_onex_error import ModelOnexError

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
_HYGIENE = "public_repo_hygiene"
_HYGIENE_ENV = "OMNI_HYGIENE_VOCAB_PATH"
_ROOT_ENV = "ONEX_WORKSPACE_CONFIG_ROOT"
_DENYLIST = "hardcoded_model_config_lab_denylist"


def _hygiene_relative_path() -> str:
    entry = next(e for e in load_contract().vocabularies if e.name == _HYGIENE)
    return entry.relative_path


def _write(path: Path, body: str = "schema_version: 1\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _request(
    name: str = _HYGIENE,
    *,
    explicit: Path | None = None,
    environment: dict[str, str] | None = None,
) -> ModelPrivateVocabularyRequest:
    return ModelPrivateVocabularyRequest(
        vocabulary_name=name,
        explicit_path=explicit,
        environment=environment or {},
        now=_NOW,
    )


def test_packaged_contract_names_the_hygiene_vocabulary_and_its_setting() -> None:
    contract = load_contract(DEFAULT_CONTRACT)
    entry = next(e for e in contract.vocabularies if e.name == _HYGIENE)
    assert entry.env_var == _HYGIENE_ENV
    assert entry.required is True
    denylist = next(e for e in contract.vocabularies if e.name == _DENYLIST)
    assert denylist.required is False


def test_explicit_path_wins_over_environment_and_config_root(tmp_path: Path) -> None:
    explicit = _write(tmp_path / "explicit.yaml")
    from_env = _write(tmp_path / "env.yaml")
    root = tmp_path / "root"
    _write(root / _hygiene_relative_path())
    result = HandlerPrivateVocabulary().handle(
        _request(
            explicit=explicit,
            environment={_HYGIENE_ENV: str(from_env), _ROOT_ENV: str(root)},
        )
    )
    assert result.path == explicit
    assert result.source is EnumPrivateVocabularySource.EXPLICIT


def test_environment_wins_over_config_root(tmp_path: Path) -> None:
    from_env = _write(tmp_path / "env.yaml")
    root = tmp_path / "root"
    _write(root / _hygiene_relative_path())
    result = HandlerPrivateVocabulary().handle(
        _request(environment={_HYGIENE_ENV: str(from_env), _ROOT_ENV: str(root)})
    )
    assert result.path == from_env
    assert result.source is EnumPrivateVocabularySource.ENVIRONMENT


def test_unset_variable_resolves_a_vocabulary_at_the_config_root(
    tmp_path: Path,
) -> None:
    """The T0.1 falsifier: the variable is unset and the vocabulary sits at the
    config root, so the read succeeds instead of refusing."""
    root = tmp_path / "root"
    placed = _write(root / _hygiene_relative_path(), "schema_version: 1\n")
    result = HandlerPrivateVocabulary().handle(
        _request(environment={_ROOT_ENV: str(root)})
    )
    assert result.found is True
    assert result.path == placed
    assert result.source is EnumPrivateVocabularySource.WORKSPACE_CONFIG_ROOT
    assert result.text == "schema_version: 1\n"


def test_config_root_falls_back_to_the_omnibase_internal_sibling_of_home(
    tmp_path: Path,
) -> None:
    home = tmp_path / "omni_home"
    home.mkdir()
    placed = _write(tmp_path / "omnibase_internal" / _hygiene_relative_path())
    result = HandlerPrivateVocabulary().handle(
        _request(environment={"OMNI_HOME": str(home)})
    )
    assert result.path is not None
    assert result.path.resolve() == placed.resolve()


def test_required_vocabulary_unset_everywhere_is_one_line_naming_the_setting(
    tmp_path: Path,
) -> None:
    with pytest.raises(ModelOnexError) as caught:
        HandlerPrivateVocabulary().handle(
            _request(environment={_ROOT_ENV: str(tmp_path / "empty-root")})
        )
    message = caught.value.message
    assert _HYGIENE_ENV in message
    assert "\n" not in message


def test_required_vocabulary_with_no_root_at_all_is_the_same_refusal() -> None:
    with pytest.raises(ModelOnexError) as caught:
        HandlerPrivateVocabulary().handle(_request())
    assert _HYGIENE_ENV in caught.value.message
    assert "\n" not in caught.value.message


def test_optional_vocabulary_unset_everywhere_is_not_found_not_a_refusal(
    tmp_path: Path,
) -> None:
    result = HandlerPrivateVocabulary().handle(
        _request(_DENYLIST, environment={_ROOT_ENV: str(tmp_path)})
    )
    assert result.found is False
    assert result.path is None
    assert result.text is None
    assert result.source is None


def test_optional_vocabulary_resolves_from_the_config_root(tmp_path: Path) -> None:
    entry = next(e for e in load_contract().vocabularies if e.name == _DENYLIST)
    placed = _write(tmp_path / entry.relative_path, "retired_values: []\n")
    result = HandlerPrivateVocabulary().handle(
        _request(_DENYLIST, environment={_ROOT_ENV: str(tmp_path)})
    )
    assert result.found is True
    assert result.path == placed


def test_an_environment_path_that_is_not_a_file_refuses_naming_the_variable(
    tmp_path: Path,
) -> None:
    with pytest.raises(ModelOnexError) as caught:
        HandlerPrivateVocabulary().handle(
            _request(environment={_HYGIENE_ENV: str(tmp_path / "missing.yaml")})
        )
    assert _HYGIENE_ENV in caught.value.message
    assert "\n" not in caught.value.message


def test_an_explicit_path_that_is_not_a_file_refuses_even_when_optional(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(ModelOnexError) as caught:
        HandlerPrivateVocabulary().handle(_request(_DENYLIST, explicit=missing))
    assert str(missing) in caught.value.message


def test_an_unknown_vocabulary_name_is_refused() -> None:
    with pytest.raises(ModelOnexError) as caught:
        HandlerPrivateVocabulary().handle(_request("no_such_vocabulary"))
    assert "no_such_vocabulary" in caught.value.message


def _aged_contract(max_age_days: int) -> ModelPrivateVocabularyContract:
    return ModelPrivateVocabularyContract.model_validate(
        {
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
    )


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
    result = HandlerPrivateVocabulary(_aged_contract(max_age_days)).handle(
        ModelPrivateVocabularyRequest(
            vocabulary_name="aged",
            explicit_path=path,
            environment={},
            now=_NOW,
        )
    )
    assert result.age_days == 10
    assert result.max_age_days == max_age_days
    assert result.age_exceeded is expected_exceeded


def test_a_vocabulary_without_a_declared_bound_reports_no_age(tmp_path: Path) -> None:
    entry = next(e for e in load_contract().vocabularies if e.name == _DENYLIST)
    _write(tmp_path / entry.relative_path, "retired_values: []\n")
    result = HandlerPrivateVocabulary().handle(
        _request(_DENYLIST, environment={_ROOT_ENV: str(tmp_path)})
    )
    assert result.age_days is None
    assert result.max_age_days is None
    assert result.age_exceeded is False


def test_an_unparseable_timestamp_is_refused_naming_the_key(tmp_path: Path) -> None:
    path = _write(tmp_path / "aged.yaml", 'resolved_at: "not a time"\n')
    with pytest.raises(ModelOnexError) as caught:
        HandlerPrivateVocabulary(_aged_contract(30)).handle(
            ModelPrivateVocabularyRequest(
                vocabulary_name="aged",
                explicit_path=path,
                environment={},
                now=_NOW,
            )
        )
    assert "resolved_at" in caught.value.message


def test_cli_prints_the_resolved_path_with_the_variable_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "root"
    placed = _write(root / _hygiene_relative_path())
    monkeypatch.delenv(_HYGIENE_ENV, raising=False)
    monkeypatch.setenv(_ROOT_ENV, str(root))
    assert main(["--name", _HYGIENE]) == 0
    assert capsys.readouterr().out.strip() == str(placed)


def test_cli_unset_required_vocabulary_is_one_refusal_line_naming_the_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(_HYGIENE_ENV, raising=False)
    monkeypatch.setenv(_ROOT_ENV, str(tmp_path / "empty-root"))
    assert main(["--name", _HYGIENE]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert len(lines) == 1
    assert _HYGIENE_ENV in lines[0]
