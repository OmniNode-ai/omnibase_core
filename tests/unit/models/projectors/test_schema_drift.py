# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test for JSON schema drift detection.

This module ensures that the committed JSON schema file matches the schema
generated from the ModelProjectorContract Pydantic model. If these diverge,
either the model changed unexpectedly or the schema file needs regeneration.

Regenerate the schema file with:
    uv run python -c "
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


@pytest.fixture
def schema_path() -> Path:
    """Path to the projector contract JSON schema."""
    return (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "omnibase_core"
        / "schemas"
        / "projector_contract.schema.json"
    )


@pytest.mark.unit
class TestSchemaDrift:
    """Tests to detect unintentional schema changes."""

    def test_schema_matches_committed_file(self, schema_path: Path) -> None:
        """Verify generated schema matches committed schema file.

        If this test fails, either:
        1. Update the schema file with the command in the module docstring
        2. Or revert your model changes if the schema change was unintentional

        The schema file ensures API contracts remain stable and changes are
        intentional and reviewed.

        Note:
            The committed schema includes a pattern constraint on consumed_events
            items that is intentionally added beyond what Pydantic generates.
            This pattern validates event names at the JSON Schema level to match
            the Python-level validation in ModelProjectorContract.validate_event_names().
        """
        # Generate current schema from model
        generated = ModelProjectorContract.model_json_schema()

        # Add the event name pattern constraint to consumed_events items.
        # This pattern is intentionally added to the committed schema for JSON Schema
        # validation, matching the Python-level field_validator in ModelProjectorContract.
        # Pydantic's model_json_schema() doesn't export field_validator patterns.
        event_name_pattern = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*\.v[0-9]+$"
        if "properties" in generated and "consumed_events" in generated["properties"]:
            if "items" in generated["properties"]["consumed_events"]:
                generated["properties"]["consumed_events"]["items"]["pattern"] = (
                    event_name_pattern
                )

        # Verify schema file exists
        assert schema_path.exists(), (
            f"Schema file not found: {schema_path}\n"
            'Generate it with: uv run python -c "import json; '
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
            '    uv run python -c "\n'
            "    import json\n"
            "    from omnibase_core.models.projectors import ModelProjectorContract\n"
            "    schema = ModelProjectorContract.model_json_schema()\n"
            "    with open('src/omnibase_core/schemas/projector_contract.schema.json', 'w') as f:\n"
            "        json.dump(schema, f, indent=2)\n"
            '    "\n\n'
            "If unintentional, revert the model changes that caused the drift."
        )

    def test_schema_is_valid_json(self, schema_path: Path) -> None:
        """Verify the committed schema file is valid JSON."""
        assert schema_path.exists(), f"Schema file not found: {schema_path}"

        # This will raise JSONDecodeError if invalid
        with open(schema_path) as f:
            schema = json.load(f)

        # Basic JSON Schema structure validation
        assert isinstance(schema, dict), "Schema must be a JSON object"
        assert "type" in schema, "Schema must have a 'type' field"
        assert "properties" in schema, "Schema must have a 'properties' field"
        assert schema["type"] == "object", "Root schema type must be 'object'"

    def test_schema_has_required_definitions(self, schema_path: Path) -> None:
        """Verify schema contains all expected model definitions."""
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

    def test_schema_required_fields(self, schema_path: Path) -> None:
        """Verify schema has expected required fields."""
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
