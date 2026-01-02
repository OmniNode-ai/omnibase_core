# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Test for JSON schema drift detection.

This module ensures that the committed JSON schema file matches the schema
generated from the ModelProjectorContract Pydantic model. If these diverge,
either the model changed unexpectedly or the schema file needs regeneration.

Regenerate the schema file with:
    poetry run python -c "
    import json
    from omnibase_core.models.projectors import ModelProjectorContract
    schema = ModelProjectorContract.model_json_schema()
    with open('src/omnibase_core/schemas/projector_contract.schema.json', 'w') as f:
        json.dump(schema, f, indent=2)
    "
"""

import json
from pathlib import Path

import pytest

from omnibase_core.models.projectors import ModelProjectorContract


@pytest.mark.unit
class TestSchemaDrift:
    """Tests to detect unintentional schema changes."""

    def test_schema_matches_committed_file(self) -> None:
        """Verify generated schema matches committed schema file.

        If this test fails, either:
        1. Update the schema file with the command in the module docstring
        2. Or revert your model changes if the schema change was unintentional

        The schema file ensures API contracts remain stable and changes are
        intentional and reviewed.
        """
        # Path from test file to schema file
        schema_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "src"
            / "omnibase_core"
            / "schemas"
            / "projector_contract.schema.json"
        )

        # Generate current schema from model
        generated = ModelProjectorContract.model_json_schema()

        # Verify schema file exists
        assert schema_path.exists(), (
            f"Schema file not found: {schema_path}\n"
            'Generate it with: poetry run python -c "import json; '
            "from omnibase_core.models.projectors import ModelProjectorContract; "
            "schema = ModelProjectorContract.model_json_schema(); "
            "open('src/omnibase_core/schemas/projector_contract.schema.json', 'w').write("
            'json.dumps(schema, indent=2))"'
        )

        # Load committed schema
        with open(schema_path) as f:
            committed = json.load(f)

        # Compare schemas
        assert generated == committed, (
            "Schema drift detected! The generated schema differs from the committed file.\n\n"
            "If this change is intentional, regenerate the schema file:\n"
            '    poetry run python -c "\n'
            "    import json\n"
            "    from omnibase_core.models.projectors import ModelProjectorContract\n"
            "    schema = ModelProjectorContract.model_json_schema()\n"
            "    with open('src/omnibase_core/schemas/projector_contract.schema.json', 'w') as f:\n"
            "        json.dump(schema, f, indent=2)\n"
            '    "\n\n'
            "If unintentional, revert the model changes that caused the drift."
        )

    def test_schema_is_valid_json(self) -> None:
        """Verify the committed schema file is valid JSON."""
        schema_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "src"
            / "omnibase_core"
            / "schemas"
            / "projector_contract.schema.json"
        )

        assert schema_path.exists(), f"Schema file not found: {schema_path}"

        # This will raise JSONDecodeError if invalid
        with open(schema_path) as f:
            schema = json.load(f)

        # Basic JSON Schema structure validation
        assert isinstance(schema, dict), "Schema must be a JSON object"
        assert "type" in schema, "Schema must have a 'type' field"
        assert "properties" in schema, "Schema must have a 'properties' field"
        assert schema["type"] == "object", "Root schema type must be 'object'"

    def test_schema_has_required_definitions(self) -> None:
        """Verify schema contains all expected model definitions."""
        schema_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "src"
            / "omnibase_core"
            / "schemas"
            / "projector_contract.schema.json"
        )

        with open(schema_path) as f:
            schema = json.load(f)

        # Check for expected $defs (nested model definitions)
        expected_defs = {
            "ModelIdempotencyConfig",
            "ModelProjectorBehavior",
            "ModelProjectorColumn",
            "ModelProjectorIndex",
            "ModelProjectorSchema",
            "ModelSemVer",
        }

        assert "$defs" in schema, "Schema must have '$defs' for nested models"
        actual_defs = set(schema["$defs"].keys())

        assert expected_defs <= actual_defs, (
            f"Missing model definitions in schema.\n"
            f"Expected: {expected_defs}\n"
            f"Actual: {actual_defs}\n"
            f"Missing: {expected_defs - actual_defs}"
        )

    def test_schema_required_fields(self) -> None:
        """Verify schema has expected required fields."""
        schema_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "src"
            / "omnibase_core"
            / "schemas"
            / "projector_contract.schema.json"
        )

        with open(schema_path) as f:
            schema = json.load(f)

        expected_required = {
            "projector_kind",
            "projector_id",
            "name",
            "version",
            "aggregate_type",
            "consumed_events",
            "projection_schema",
            "behavior",
        }

        assert "required" in schema, "Schema must have 'required' field"
        actual_required = set(schema["required"])

        assert expected_required == actual_required, (
            f"Required fields mismatch.\n"
            f"Expected: {expected_required}\n"
            f"Actual: {actual_required}"
        )
