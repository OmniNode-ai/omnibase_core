# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17696 acceptance checks: the node-metadata entrypoint JSON wire."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from omnibase_core.models.core.model_extracted_block import ModelExtractedBlock
from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock

_URI = "python://main.py"

_PROBE = """
import json
from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock
payload = json.loads(sys.argv[1])
block = ModelNodeMetadataBlock.model_validate(payload)
dumped = json.loads(block.model_dump_json())
assert dumped["entrypoint"] == "python://main.py", dumped["entrypoint"]
assert ModelNodeMetadataBlock.model_validate_json(block.model_dump_json()) == block
"""


def _payload() -> dict[str, object]:
    return {
        "name": "test-node",
        "version": {"major": 1, "minor": 0, "patch": 0},
        "author": "OmniNode",
        "created_at": "2026-01-01T00:00:00Z",
        "last_modified_at": "2026-01-01T00:00:00Z",
        "hash": "a" * 64,
        "entrypoint": _URI,
        "namespace": "onex.tools.test",
    }


@pytest.mark.unit
def test_model_dump_json_emits_canonical_entrypoint_uri_string() -> None:
    block = ModelNodeMetadataBlock.model_validate(_payload())
    assert json.loads(block.model_dump_json())["entrypoint"] == _URI


@pytest.mark.unit
def test_model_validate_json_round_trips_exactly() -> None:
    block = ModelNodeMetadataBlock.model_validate(_payload())
    restored = ModelNodeMetadataBlock.model_validate_json(block.model_dump_json())
    assert restored == block
    assert restored.model_dump_json() == block.model_dump_json()


@pytest.mark.unit
def test_canonical_uri_validates_and_malformed_entrypoints_fail_closed() -> None:
    assert ModelNodeMetadataBlock.model_validate(_payload()).entrypoint.to_uri() == _URI
    for bad in ("not-a-uri", "", 7, None):
        with pytest.raises(Exception):
            ModelNodeMetadataBlock.model_validate({**_payload(), "entrypoint": bad})


@pytest.mark.unit
def test_populated_extracted_block_round_trips_through_json() -> None:
    block = ModelExtractedBlock.model_validate({"metadata": _payload(), "body": "b"})
    restored = ModelExtractedBlock.model_validate_json(block.model_dump_json())
    assert restored == block
    assert json.loads(block.model_dump_json())["metadata"]["entrypoint"] == _URI


@pytest.mark.unit
def test_fresh_process_round_trip_needs_no_rebuild() -> None:
    subprocess.run(
        [sys.executable, "-c", "import sys\n" + _PROBE, json.dumps(_payload())],
        check=True,
        text=True,
        capture_output=True,
    )


@pytest.mark.unit
def test_concurrent_round_trips_are_identical() -> None:
    def run(_: int) -> str:
        block = ModelNodeMetadataBlock.model_validate(_payload())
        return str(json.loads(block.model_dump_json())["entrypoint"])

    with ThreadPoolExecutor(max_workers=8) as executor:
        assert list(executor.map(run, range(32))) == [_URI] * 32


@pytest.mark.unit
def test_dictionary_entrypoint_input_is_not_accepted() -> None:
    dictionary = {**_payload(), "entrypoint": {"type": "python", "target": "main.py"}}
    with pytest.raises(Exception, match="entrypoint must be"):
        ModelNodeMetadataBlock.model_validate(dictionary)
