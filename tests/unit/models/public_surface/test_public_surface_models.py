# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-26194: typed public-surface models and the Python extraction rules."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_public_surface_kind import EnumPublicSurfaceKind
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.public_surface.model_gate_inputs_manifest import (
    ModelGateInputsManifest,
)
from omnibase_core.models.public_surface.model_public_surface_contract import (
    ModelPublicSurfaceContract,
)
from omnibase_core.models.public_surface.model_public_surface_entry import (
    ModelPublicSurfaceEntry,
)
from omnibase_core.models.public_surface.model_removed_surface_verdict import (
    ModelRemovedSurfaceVerdict,
)
from omnibase_core.models.public_surface.model_surface_extraction_rule import (
    ModelSurfaceExtractionRule,
)
from omnibase_core.models.public_surface.model_surface_extraction_source import (
    ModelSurfaceExtractionSource,
)

pytestmark = pytest.mark.unit

CONTRACT_PATH = (
    Path(__file__).resolve().parents[4]
    / "src/omnibase_core/contracts/public_surface.validation.yaml"
)


def _manifest() -> ModelGateInputsManifest:
    return ModelGateInputsManifest(
        repo="OmniNode-ai/omnibase_core",
        base_sha="a" * 40,
        head_sha="b" * 40,
        graph_snapshot="graph-1",
        rules_sha256="c" * 64,
    )


def _entry(identity: str = "omnibase_core.x.Y") -> ModelPublicSurfaceEntry:
    return ModelPublicSurfaceEntry(
        repo="OmniNode-ai/omnibase_core",
        kind=EnumPublicSurfaceKind.PYTHON_SYMBOL,
        identity=identity,
        path="src/omnibase_core/x.py",
        line=3,
    )


def _rule_row(kind: str, sources: list[dict[str, object]]) -> dict[str, object]:
    return {
        "rule_id": f"{kind}-rule",
        "description": "d",
        "severity": "error",
        "enabled": True,
        "parameters": {"kind": kind, "sources": sources},
    }


def _doc(rows: list[dict[str, object]]) -> dict[str, object]:
    return {"contract_kind": "validation_subcontract", "validation": {"rules": rows}}


_PY = {"parser": "python_ast", "include": ["a/**/*.py"]}
_YAML = {"parser": "yaml_key_path", "include": ["a.yaml"], "key_paths": ["a.b"]}
_TOML = {"parser": "toml_key_path", "include": ["a.toml"], "key_paths": ["a.b"]}


def test_enum_values() -> None:
    assert {k.value for k in EnumPublicSurfaceKind} == {
        "python_symbol",
        "python_module",
        "node",
        "contract_field",
        "topic",
        "overlay_key",
        "endpoint",
        "cli_verb",
    }


def test_entry_is_frozen_and_forbids_extra() -> None:
    entry = _entry()
    assert entry.references == ()
    assert entry.renamed_to is None
    with pytest.raises(ValidationError):
        entry.__setattr__("line", 4)
    with pytest.raises(ValidationError):
        ModelPublicSurfaceEntry(
            repo="r",
            kind=EnumPublicSurfaceKind.NODE,
            identity="i",
            path="p",
            line=1,
            surprise=1,
        )


# AC1 -------------------------------------------------------------------------
def test_ac1_unread_verdict_without_unread_read_raises() -> None:
    with pytest.raises(ValidationError, match="UNREAD"):
        ModelRemovedSurfaceVerdict(
            status="UNREAD", unread_reads=(), inputs_manifest=_manifest()
        )


def test_ac1_refused_verdict_without_consumer_raises() -> None:
    with pytest.raises(ValidationError, match="REFUSED"):
        ModelRemovedSurfaceVerdict(
            status="REFUSED",
            removed_entries=(_entry(),),
            consumers={},
            inputs_manifest=_manifest(),
        )


def test_ac1_verdict_without_inputs_manifest_raises() -> None:
    with pytest.raises(ValidationError, match="inputs_manifest"):
        ModelRemovedSurfaceVerdict.model_validate({"status": "PASSED"})


def test_ac1_valid_verdicts_construct() -> None:
    entry = _entry()
    ModelRemovedSurfaceVerdict(status="PASSED", inputs_manifest=_manifest())
    ModelRemovedSurfaceVerdict(
        status="UNREAD", unread_reads=("graph",), inputs_manifest=_manifest()
    )
    ModelRemovedSurfaceVerdict(
        status="REFUSED",
        removed_entries=(entry,),
        consumers={
            "OmniNode-ai/omnibase_core:python_symbol:omnibase_core.x.Y": (
                "omnimarket:a.py:1",
            )
        },
        inputs_manifest=_manifest(),
    )


# AC2 -------------------------------------------------------------------------
def test_ac2_rule_with_yaml_and_toml_sources_loads() -> None:
    contract = ModelPublicSurfaceContract.from_validation_document(
        _doc([_rule_row("node", [_YAML, _TOML])])
    )
    (rule,) = contract.rules
    assert [s.parser for s in rule.sources] == ["yaml_key_path", "toml_key_path"]
    assert isinstance(rule, ModelSurfaceExtractionRule)
    assert isinstance(rule.sources[0], ModelSurfaceExtractionSource)


def test_ac2_unknown_parser_is_refused_naming_the_row() -> None:
    bad = {"parser": "regex_guess", "include": ["a"]}
    with pytest.raises(
        ModelOnexError, match=r"rules\[1\].*regex_guess|regex_guess.*rules\[1\]"
    ):
        ModelPublicSurfaceContract.from_validation_document(
            _doc([_rule_row("node", [_PY]), _rule_row("topic", [_PY, bad])])
        )


def test_ac2_two_rules_naming_one_kind_are_refused_naming_both_rows() -> None:
    with pytest.raises(ModelOnexError) as info:
        ModelPublicSurfaceContract.from_validation_document(
            _doc(
                [
                    _rule_row("topic", [_PY]),
                    _rule_row("node", [_PY]),
                    _rule_row("topic", [_YAML]),
                ]
            )
        )
    message = str(info.value)
    assert "rules[0]" in message and "rules[2]" in message and "topic" in message


def test_shipped_contract_carries_the_two_python_kinds() -> None:
    contract = ModelPublicSurfaceContract.from_validation_file(CONTRACT_PATH)
    assert {r.kind for r in contract.rules} == {
        EnumPublicSurfaceKind.PYTHON_SYMBOL,
        EnumPublicSurfaceKind.PYTHON_MODULE,
    }
    assert all(s.include for r in contract.rules for s in r.sources)
