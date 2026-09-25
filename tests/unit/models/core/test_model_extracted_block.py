# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime-completeness regressions for ``ModelExtractedBlock``."""

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_extracted_block import ModelExtractedBlock
from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock


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


def _validate_and_describe(_: int) -> tuple[str, str]:
    result = ModelExtractedBlock.model_validate(
        {"metadata": _metadata_payload(), "body": "body"}
    )
    restored = ModelExtractedBlock.model_validate_json(result.model_dump_json())
    schema = json.dumps(ModelExtractedBlock.model_json_schema(), sort_keys=True)
    return restored.model_dump_json(), schema


@pytest.mark.unit
def test_fresh_process_schema_is_complete_before_other_model_imports() -> None:
    """A clean interpreter resolves the canonical metadata type without rebuilding."""
    script = """
from omnibase_core.models.core.model_extracted_block import ModelExtractedBlock
from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock

annotation = ModelExtractedBlock.model_fields["metadata"].annotation
assert "ForwardRef" not in repr(annotation)
schema = ModelExtractedBlock.model_json_schema()
assert schema["additionalProperties"] is False
assert "ModelNodeMetadataBlock" in schema["$defs"]
assert "model_rebuild" not in ModelExtractedBlock.__dict__
payload = {
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
result = ModelExtractedBlock.model_validate({"metadata": payload, "body": "body"})
assert ModelExtractedBlock.model_validate_json(result.model_dump_json()) == result
print("fresh-process-schema-ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "fresh-process-schema-ok"


@pytest.mark.unit
def test_metadata_validation_and_json_round_trip_use_canonical_model() -> None:
    """Nested metadata validates as its canonical model and survives JSON transport."""
    result = ModelExtractedBlock.model_validate(
        {"metadata": _metadata_payload(), "body": "body"}
    )

    assert isinstance(result.metadata, ModelNodeMetadataBlock)
    assert ModelExtractedBlock.model_validate_json(result.model_dump_json()) == result
    dumped = json.loads(result.model_dump_json())
    assert dumped["metadata"]["entrypoint"] == "python://main.py"

    with pytest.raises(ValidationError, match="unexpected"):
        ModelExtractedBlock.model_validate(
            {"metadata": _metadata_payload(), "body": "body", "unexpected": True}
        )

    invalid_metadata = {**_metadata_payload(), "version": "not-semver"}
    with pytest.raises(ValidationError, match=r"metadata\.version"):
        ModelExtractedBlock.model_validate(
            {"metadata": invalid_metadata, "body": "body"}
        )

    with pytest.raises(ModelOnexError, match="entrypoint must be"):
        ModelNodeMetadataBlock.model_validate(
            {
                **_metadata_payload(),
                "entrypoint": {"type": "python", "target": "main.py"},
            }
        )

    with pytest.raises(ValidationError, match="nested_unexpected"):
        ModelExtractedBlock.model_validate(
            {
                "metadata": {
                    **_metadata_payload(),
                    "nested_unexpected": True,
                },
                "body": "body",
            }
        )


@pytest.mark.unit
def test_concurrent_schema_and_validation_are_deterministic() -> None:
    """Concurrent first-class use needs no shared rebuild or import-order mutation."""
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(_validate_and_describe, range(32)))

    assert len(set(results)) == 1
