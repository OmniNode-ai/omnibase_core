# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire-contract regressions for multi-document generation errors."""

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.errors.model_onex_error_data import _ModelOnexErrorData
from omnibase_core.models.core.model_multi_doc_generation_result import (
    ModelMultiDocGenerationResult,
)


@pytest.mark.unit
def test_error_field_uses_foundation_serialization_contract() -> None:
    """The DTO carries error wire data, never runtime exception instances."""
    assert (
        ModelMultiDocGenerationResult.model_fields["errors"].annotation
        == list[_ModelOnexErrorData]
    )

    schema = ModelMultiDocGenerationResult.model_json_schema()
    error_items = schema["properties"]["errors"]["items"]
    assert error_items["$ref"].endswith("/_ModelOnexErrorData")


@pytest.mark.unit
def test_error_wire_round_trip_is_typed_and_fail_closed(tmp_path: Path) -> None:
    """Canonical error data round-trips while malformed wire fields are rejected."""
    runtime_error = ModelOnexError(
        message="generation failed",
        correlation_id=None,
        stage="emit",
    )
    error_wire = runtime_error.model_dump()
    payload = {
        "contract_path": tmp_path / "contract.yaml",
        "output_dir": tmp_path / "output",
        "errors": [error_wire],
    }
    result = ModelMultiDocGenerationResult.model_validate(payload)

    restored = ModelMultiDocGenerationResult.model_validate_json(
        result.model_dump_json()
    )

    assert restored == result
    assert restored.errors[0].message == "generation failed"
    assert restored.errors[0].context == {"stage": "emit"}

    with pytest.raises(ValidationError, match="unexpected"):
        ModelMultiDocGenerationResult.model_validate(
            {
                **payload,
                "errors": [{"message": "generation failed", "unexpected": True}],
            }
        )

    with pytest.raises(ValidationError):
        ModelMultiDocGenerationResult.model_validate(
            {
                **payload,
                "errors": [
                    ModelOnexError(message="runtime exception is not wire data")
                ],
            }
        )


@pytest.mark.unit
def test_fresh_process_import_and_schema_use_foundation_wire_type() -> None:
    """A clean interpreter imports the sanctioned foundation contract directly."""
    script = """
from omnibase_core.errors.model_onex_error_data import _ModelOnexErrorData
from omnibase_core.models.core.model_multi_doc_generation_result import ModelMultiDocGenerationResult

assert ModelMultiDocGenerationResult.model_fields["errors"].annotation == list[_ModelOnexErrorData]
assert ModelMultiDocGenerationResult.model_json_schema()["properties"]["errors"]["items"]["$ref"].endswith("/_ModelOnexErrorData")
print("fresh-process-ok")
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "fresh-process-ok"
