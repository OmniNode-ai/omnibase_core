# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Schema/runtime parity for the canonical node-metadata entrypoint wire."""

import importlib
from typing import Protocol, cast

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_extracted_block import ModelExtractedBlock
from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock


class _JsonSchemaModule(Protocol):
    """Typed surface used from the runtime jsonschema dependency."""

    ValidationError: type[Exception]

    def validate(self, instance: object, schema: object) -> None: ...


jsonschema = cast(_JsonSchemaModule, importlib.import_module("jsonschema"))


def _metadata_payload() -> dict[str, object]:
    return {
        "uuid": "00000000-0000-4000-8000-000000000001",
        "name": "test-node",
        "version": {"major": 1, "minor": 0, "patch": 0},
        "author": "OmniNode",
        "created_at": "2026-01-01T00:00:00Z",
        "last_modified_at": "2026-01-01T00:00:00Z",
        "hash": "a" * 64,
        "entrypoint": "python://main.py",
        "namespace": "onex.tools.test",
    }


@pytest.mark.unit
def test_entrypoint_validation_schema_matches_runtime_wire() -> None:
    """Canonical URI input is valid; dictionary compatibility input is not."""
    schema = ModelNodeMetadataBlock.model_json_schema(mode="validation")
    payload = _metadata_payload()

    jsonschema.validate(payload, schema)
    assert ModelNodeMetadataBlock.model_validate(payload).entrypoint.to_uri() == (
        "python://main.py"
    )

    dictionary_entrypoint = {
        **payload,
        "entrypoint": {"type": "python", "target": "main.py"},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dictionary_entrypoint, schema)
    with pytest.raises(ModelOnexError, match="entrypoint must be"):
        ModelNodeMetadataBlock.model_validate(dictionary_entrypoint)

    malformed_entrypoint = {**payload, "entrypoint": "not-a-uri"}
    with pytest.raises(ModelOnexError, match="Invalid entrypoint URI"):
        ModelNodeMetadataBlock.model_validate(malformed_entrypoint)


@pytest.mark.unit
def test_nested_extracted_block_schema_preserves_entrypoint_contract() -> None:
    """The canonical entrypoint shape remains truthful through the owning DTO."""
    schema = ModelExtractedBlock.model_json_schema(mode="validation")
    payload = {"metadata": _metadata_payload(), "body": "body"}

    jsonschema.validate(payload, schema)
    assert ModelExtractedBlock.model_validate(payload).metadata is not None

    dictionary_entrypoint = {
        "metadata": {
            **_metadata_payload(),
            "entrypoint": {"type": "python", "target": "main.py"},
        },
        "body": "body",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dictionary_entrypoint, schema)
    with pytest.raises(ModelOnexError, match="entrypoint must be"):
        ModelExtractedBlock.model_validate(dictionary_entrypoint)
