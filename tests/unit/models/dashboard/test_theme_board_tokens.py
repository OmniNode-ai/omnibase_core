# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the board tokens of ModelRendererThemeContract (OMN-21998).

View-centric interfaces plan S2, Tokens: the contract gains the tokens the floor
board needs so no renderer takes a colour, font or motion value from a page
literal.

* AC1 — the contract declares the tokens and an instance missing any is refused.
* AC2 — every bundled instance carries them and the content digest moves with
  any one of them.
* AC3 — the emitted JSON Schema lists them.
* AC4 — the new colour tokens are accepted by ``is_color_token_name`` (and so by
  the widget configs that name a colour token), the non-colour ones are refused,
  and a hex literal is still refused.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.models.dashboard import (
    ModelChartSeriesConfig,
    ModelMetricThreshold,
    ModelRendererThemeContract,
    ModelThemeInstance,
)
from omnibase_core.utils.util_theme_catalog import (
    THEME_CATALOG_ROOT,
    compute_theme_content_digest,
    load_packaged_theme_catalog,
    load_theme_instance,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

#: state tint -> the existing status colour token the tint is a low-opacity form of
_TINT_FOR_STATUS = {
    "color_tint_ok": "color_status_success",
    "color_tint_warn": "color_status_warning",
    "color_tint_stop": "color_status_error",
}
_NEW_COLOR_TOKENS = (*_TINT_FOR_STATUS, "color_neutral_idle", "color_focus_ring")
_NEW_NON_COLOR_TOKENS = (
    "font_family_display",
    "font_family_mono",
    "motion_duration",
    "motion_easing",
)
_NEW_TOKENS = (*_NEW_COLOR_TOKENS, *_NEW_NON_COLOR_TOKENS)
_SHIPPED_THEME_IDS = ("onex.theme.light", "onex.theme.dark", "onex.theme.warm")
_EIGHT_DIGIT_HEX = re.compile(r"^#([0-9a-fA-F]{6})([0-9a-fA-F]{2})$")


def _shipped_documents() -> list[Path]:
    return sorted(THEME_CATALOG_ROOT.rglob("*.yaml"))


def _shipped_document_dict(theme_id: str) -> dict[str, Any]:
    (document,) = [p for p in _shipped_documents() if p.parent.name == theme_id]
    loaded = yaml.safe_load(document.read_text())
    assert isinstance(loaded, dict)
    return loaded


# ---------------------------------------------------------------------------
# AC1 — the contract declares the tokens; an instance missing one is refused
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThemeBoardTokensContract:
    @pytest.mark.parametrize("token", _NEW_TOKENS)
    def test_theme_board_tokens_are_declared_required_fields(self, token: str) -> None:
        field = ModelRendererThemeContract.model_fields[token]
        assert field.is_required()

    @pytest.mark.parametrize("token", _NEW_TOKENS)
    def test_theme_board_tokens_instance_missing_one_is_refused(
        self, token: str
    ) -> None:
        document = _shipped_document_dict("onex.theme.dark")
        del document["tokens"][token]
        with pytest.raises(ValidationError) as exc_info:
            ModelThemeInstance.model_validate(document)
        assert any(error["loc"][-1] == token for error in exc_info.value.errors())

    @pytest.mark.parametrize("token", _NEW_TOKENS)
    def test_theme_board_tokens_empty_value_is_refused(self, token: str) -> None:
        document = _shipped_document_dict("onex.theme.dark")
        document["tokens"][token] = ""
        with pytest.raises(ValidationError):
            ModelThemeInstance.model_validate(document)

    def test_theme_board_tokens_move_the_schema_version(self) -> None:
        """Adding token fields is a schema change, so the version axis moves."""
        for theme_id in _SHIPPED_THEME_IDS:
            document = _shipped_document_dict(theme_id)
            assert (
                document["schema_version"]["major"],
                document["schema_version"]["minor"],
            ) >= (1, 1)
            assert document["schema_version"] == document["tokens"]["contract_version"]


# ---------------------------------------------------------------------------
# AC2 — bundled instances carry them; the digest moves with them
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThemeCatalogBoardTokens:
    @pytest.mark.parametrize("theme_id", _SHIPPED_THEME_IDS)
    def test_theme_catalog_instance_carries_every_board_token(
        self, theme_id: str
    ) -> None:
        document = _shipped_document_dict(theme_id)
        for token in _NEW_TOKENS:
            assert document["tokens"].get(token), f"{theme_id} has no {token}"

    def test_theme_catalog_ships_light_and_dark_with_distinct_board_values(
        self,
    ) -> None:
        light = _shipped_document_dict("onex.theme.light")["tokens"]
        dark = _shipped_document_dict("onex.theme.dark")["tokens"]
        for token in _TINT_FOR_STATUS:
            assert light[token] != dark[token]

    @pytest.mark.parametrize("theme_id", _SHIPPED_THEME_IDS)
    def test_theme_catalog_tint_is_a_low_opacity_form_of_the_status_colour(
        self, theme_id: str
    ) -> None:
        tokens = _shipped_document_dict(theme_id)["tokens"]
        for tint, status in _TINT_FOR_STATUS.items():
            match = _EIGHT_DIGIT_HEX.match(tokens[tint])
            assert match, f"{theme_id}.{tint} is not an 8-digit hex colour"
            assert f"#{match.group(1)}".lower() == tokens[status].lower()
            assert 0 < int(match.group(2), 16) <= 0x40

    def test_theme_catalog_digest_is_recomputed_from_the_published_values(
        self,
    ) -> None:
        catalog = load_packaged_theme_catalog()
        assert len(catalog.entries) == len(_SHIPPED_THEME_IDS)
        for entry in catalog.entries:
            instance = load_theme_instance(THEME_CATALOG_ROOT / entry.source_path)
            assert entry.content_digest == compute_theme_content_digest(instance)

    @pytest.mark.parametrize("token", _NEW_TOKENS)
    def test_theme_digest_moves_when_a_board_token_changes(self, token: str) -> None:
        base = load_theme_instance(
            THEME_CATALOG_ROOT / "onex.theme.dark" / "1.1.0.yaml"
        )
        changed = base.model_copy(
            update={
                "tokens": base.tokens.model_copy(
                    update={token: f"{getattr(base.tokens, token)} "}
                )
            }
        )
        assert compute_theme_content_digest(changed) != compute_theme_content_digest(
            base
        )


# ---------------------------------------------------------------------------
# AC3 — the emitted JSON Schema lists the tokens
# ---------------------------------------------------------------------------


def _emit_combined_schema(target: Path) -> dict[str, Any]:
    path = _REPO_ROOT / "scripts" / "emit_ts_types.py"
    spec = importlib.util.spec_from_file_location("_emit_ts_types_board_tokens", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    saved_argv = list(sys.argv)
    try:
        spec.loader.exec_module(module)
        sys.argv = ["emit_ts_types.py", str(target)]
        assert module.main() == 0
    finally:
        sys.argv = saved_argv
        sys.modules.pop(spec.name, None)
    payload = json.loads(target.read_text())
    assert isinstance(payload, dict)
    return payload


@pytest.mark.unit
class TestThemeBoardTokensSchema:
    def test_theme_contract_json_schema_lists_every_board_token(self) -> None:
        schema = ModelRendererThemeContract.model_json_schema()
        for token in _NEW_TOKENS:
            assert token in schema["properties"]
            assert token in schema["required"]

    def test_theme_instance_json_schema_embeds_every_board_token(self) -> None:
        defs = ModelThemeInstance.model_json_schema()["$defs"]
        for token in _NEW_TOKENS:
            assert token in defs["ModelRendererThemeContract"]["properties"]

    def test_theme_schema_emitted_by_the_ts_emitter_lists_every_board_token(
        self, tmp_path: Path
    ) -> None:
        payload = _emit_combined_schema(tmp_path / "onex-models.json")
        emitted = payload["$defs"]["ModelRendererThemeContract"]
        for token in _NEW_TOKENS:
            assert token in emitted["properties"]
            assert token in emitted["required"]


# ---------------------------------------------------------------------------
# AC4 — colour tokens are names, never literals
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsColorTokenNameBoardTokens:
    @pytest.mark.parametrize("token", _NEW_COLOR_TOKENS)
    def test_is_color_token_name_accepts_the_new_colour_tokens(
        self, token: str
    ) -> None:
        assert ModelRendererThemeContract.is_color_token_name(token) is True

    @pytest.mark.parametrize("token", _NEW_NON_COLOR_TOKENS)
    def test_is_color_token_name_refuses_the_new_non_colour_tokens(
        self, token: str
    ) -> None:
        assert ModelRendererThemeContract.is_color_token_name(token) is False

    @pytest.mark.parametrize("token", _NEW_COLOR_TOKENS)
    def test_is_color_token_name_new_colour_token_is_accepted_by_widget_configs(
        self, token: str
    ) -> None:
        series = ModelChartSeriesConfig(name="s", data_key="k", color=token)
        threshold = ModelMetricThreshold(value=1.0, color=token)
        assert series.color == token
        assert threshold.color == token

    @pytest.mark.parametrize("literal", ["#22c55e26", "#22c55e", "rgb(34, 197, 94)"])
    def test_is_color_token_name_refuses_a_hex_literal_in_widget_configs(
        self, literal: str
    ) -> None:
        assert ModelRendererThemeContract.is_color_token_name(literal) is False
        with pytest.raises(ValidationError):
            ModelChartSeriesConfig(name="s", data_key="k", color=literal)
        with pytest.raises(ValidationError):
            ModelMetricThreshold(value=1.0, color=literal)

    @pytest.mark.parametrize("token", _NEW_NON_COLOR_TOKENS)
    def test_is_color_token_name_non_colour_token_is_refused_by_widget_configs(
        self, token: str
    ) -> None:
        with pytest.raises(ValidationError):
            ModelChartSeriesConfig(name="s", data_key="k", color=token)
