# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for validating example YAML handler contracts.

Tests that example YAML files in examples/contracts/handlers/ can be loaded
and deserialized into ModelHandlerContract without validation errors.

This ensures the documentation examples remain valid and consistent with
the Pydantic model schema.
"""

from pathlib import Path

import pytest

from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model


@pytest.mark.unit
class TestHandlerContractExamples:
    """Validate example YAML handler contracts deserialize correctly."""

    @pytest.fixture
    def examples_dir(self) -> Path:
        """Return the path to the handler contract examples directory."""
        # Navigate from tests/unit/models/contracts/ to examples/contracts/handlers/
        return Path(__file__).parents[4] / "examples" / "contracts" / "handlers"

    def test_examples_directory_exists(self, examples_dir: Path) -> None:
        """Ensure the examples directory exists."""
        assert examples_dir.exists(), f"Examples directory not found: {examples_dir}"
        assert examples_dir.is_dir(), f"Path is not a directory: {examples_dir}"

    def test_effect_handler_example_loads(self, examples_dir: Path) -> None:
        """Ensure effect_handler.yaml deserializes without errors."""
        yaml_path = examples_dir / "effect_handler.yaml"
        assert yaml_path.exists(), f"Example file not found: {yaml_path}"

        contract = load_and_validate_yaml_model(yaml_path, ModelHandlerContract)

        # Validate key fields are populated correctly
        assert contract.handler_id == "effect.database.user_repository"
        assert contract.name == "User Repository"
        assert contract.version == "2.0.0"
        assert contract.descriptor.handler_kind == "effect"
        assert contract.descriptor.purity == "side_effecting"
        assert contract.descriptor.idempotent is True
        assert contract.descriptor.timeout_ms == 30000

        # Validate capability inputs
        assert len(contract.capability_inputs) == 2
        db_cap = contract.capability_inputs[0]
        assert db_cap.alias == "db"
        assert db_cap.capability == "database.relational"
        assert db_cap.strict is True

        cache_cap = contract.capability_inputs[1]
        assert cache_cap.alias == "cache"
        assert cache_cap.capability == "cache.distributed"
        assert cache_cap.strict is False  # Optional

        # Validate capability outputs
        assert "user.created" in contract.capability_outputs
        assert "user.updated" in contract.capability_outputs
        assert "user.deleted" in contract.capability_outputs

        # Validate execution constraints
        assert contract.execution_constraints is not None
        assert "capability:auth" in contract.execution_constraints.requires_before
        assert "capability:audit" in contract.execution_constraints.requires_after

        # Validate lifecycle flags
        assert contract.supports_lifecycle is True
        assert contract.supports_health_check is True
        assert contract.supports_provisioning is True

        # Validate tags and metadata
        assert "database" in contract.tags
        assert "effect" in contract.tags
        assert contract.metadata.get("owner") == "user-platform-team"

    def test_reducer_handler_example_loads(self, examples_dir: Path) -> None:
        """Ensure reducer_handler.yaml deserializes without errors."""
        yaml_path = examples_dir / "reducer_handler.yaml"
        assert yaml_path.exists(), f"Example file not found: {yaml_path}"

        contract = load_and_validate_yaml_model(yaml_path, ModelHandlerContract)

        # Validate key fields are populated correctly
        assert contract.handler_id == "reducer.registration.user"
        assert contract.name == "User Registration Reducer"
        assert contract.version == "1.2.0"
        assert contract.descriptor.handler_kind == "reducer"
        assert contract.descriptor.purity == "side_effecting"
        assert contract.descriptor.idempotent is True
        assert contract.descriptor.timeout_ms == 30000

        # Validate capability inputs
        assert len(contract.capability_inputs) == 2
        aliases = contract.get_capability_aliases()
        assert "db" in aliases
        assert "event_bus" in aliases

        # Validate capability outputs
        assert "registration.started" in contract.capability_outputs
        assert "registration.completed" in contract.capability_outputs
        assert "registration.failed" in contract.capability_outputs

        # Validate execution constraints
        assert contract.execution_constraints is not None
        assert contract.execution_constraints.must_run is True
        assert contract.execution_constraints.can_run_parallel is False

        # Validate lifecycle flags
        assert contract.supports_lifecycle is True
        assert contract.supports_health_check is True
        assert contract.supports_provisioning is False

        # Validate tags
        assert "reducer" in contract.tags
        assert "fsm" in contract.tags

    def test_compute_handler_example_loads(self, examples_dir: Path) -> None:
        """Ensure compute_handler.yaml deserializes without errors."""
        yaml_path = examples_dir / "compute_handler.yaml"
        assert yaml_path.exists(), f"Example file not found: {yaml_path}"

        contract = load_and_validate_yaml_model(yaml_path, ModelHandlerContract)

        # Validate key fields are populated correctly
        assert contract.handler_id == "compute.schema.validator"
        assert contract.name == "Schema Validator"
        assert contract.version == "1.0.0"
        assert contract.descriptor.handler_kind == "compute"
        assert contract.descriptor.purity == "pure"
        assert contract.descriptor.idempotent is True
        assert contract.descriptor.timeout_ms == 5000

        # Compute handlers typically have no capability inputs
        assert len(contract.capability_inputs) == 0

        # Validate capability outputs
        assert "validation.result" in contract.capability_outputs

        # Validate execution constraints - compute can run in parallel
        assert contract.execution_constraints is not None
        assert contract.execution_constraints.can_run_parallel is True
        assert contract.execution_constraints.nondeterministic_effect is False

        # Validate lifecycle flags - pure compute typically doesn't need these
        assert contract.supports_lifecycle is False
        assert contract.supports_health_check is False
        assert contract.supports_provisioning is False

        # Validate tags
        assert "compute" in contract.tags
        assert "validation" in contract.tags

    def test_all_example_files_load_successfully(self, examples_dir: Path) -> None:
        """Ensure all YAML files in examples directory can be loaded."""
        yaml_files = list(examples_dir.glob("*.yaml"))
        assert len(yaml_files) >= 3, f"Expected at least 3 example files, found {len(yaml_files)}"

        for yaml_path in yaml_files:
            # Each file should load without raising an exception
            contract = load_and_validate_yaml_model(yaml_path, ModelHandlerContract)

            # Basic sanity checks for any handler contract
            assert contract.handler_id, f"handler_id missing in {yaml_path.name}"
            assert contract.name, f"name missing in {yaml_path.name}"
            assert contract.version, f"version missing in {yaml_path.name}"
            assert contract.descriptor, f"descriptor missing in {yaml_path.name}"
            assert contract.input_model, f"input_model missing in {yaml_path.name}"
            assert contract.output_model, f"output_model missing in {yaml_path.name}"

    @pytest.mark.parametrize(
        ("filename", "expected_kind"),
        [
            ("effect_handler.yaml", "effect"),
            ("reducer_handler.yaml", "reducer"),
            ("compute_handler.yaml", "compute"),
        ],
    )
    def test_handler_kind_matches_filename(
        self, examples_dir: Path, filename: str, expected_kind: str
    ) -> None:
        """Ensure handler_kind in descriptor matches the filename convention."""
        yaml_path = examples_dir / filename
        if not yaml_path.exists():
            pytest.skip(f"Example file not found: {filename}")

        contract = load_and_validate_yaml_model(yaml_path, ModelHandlerContract)
        assert contract.descriptor.handler_kind == expected_kind, (
            f"Expected handler_kind '{expected_kind}' in {filename}, "
            f"got '{contract.descriptor.handler_kind}'"
        )

    def test_handler_id_prefix_consistency(self, examples_dir: Path) -> None:
        """Ensure handler_id prefix is consistent with handler_kind."""
        yaml_files = list(examples_dir.glob("*.yaml"))

        for yaml_path in yaml_files:
            contract = load_and_validate_yaml_model(yaml_path, ModelHandlerContract)

            # Extract first segment of handler_id
            prefix = contract.handler_id.split(".")[0].lower()
            handler_kind = contract.descriptor.handler_kind

            # Typed prefixes should match handler_kind
            # Generic prefixes (node, handler) accept any kind
            typed_prefixes = {"compute", "effect", "reducer", "orchestrator"}
            if prefix in typed_prefixes:
                assert prefix == handler_kind, (
                    f"Handler ID prefix '{prefix}' doesn't match handler_kind "
                    f"'{handler_kind}' in {yaml_path.name}"
                )
