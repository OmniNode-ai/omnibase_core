# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for the Support Assistant Demo Handler Contract.

Validates that the support_assistant.yaml handler contract:
1. Loads successfully without parse errors
2. Deserializes into ModelHandlerContract correctly
3. Has consistent handler_id prefix matching handler_kind
4. Defines the required LLM capability dependency
5. Specifies input and output model references
6. Is properly configured as an effect handler (side_effecting purity)

See: OMN-1201 - Demo Support Assistant Handler
"""

from pathlib import Path

import pytest

from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model


@pytest.mark.unit
class TestHandlerContract:
    """Tests for the Support Assistant Demo Handler Contract."""

    @pytest.fixture
    def contract_path(self) -> Path:
        """Return the path to the support_assistant.yaml contract file."""
        # Navigate from tests/unit/examples/demo/handlers/support_assistant/
        # to examples/demo/handlers/support_assistant/
        return (
            Path(__file__).parents[6]
            / "examples"
            / "demo"
            / "handlers"
            / "support_assistant"
            / "support_assistant.yaml"
        )

    @pytest.fixture
    def contract(self, contract_path: Path) -> ModelHandlerContract:
        """Load and return the contract for tests that need it."""
        return load_and_validate_yaml_model(contract_path, ModelHandlerContract)

    def test_handler_contract_loads(self, contract_path: Path) -> None:
        """Contract YAML loads without errors."""
        assert contract_path.exists(), f"Contract file not found: {contract_path}"

        # Should not raise any exception
        contract = load_and_validate_yaml_model(contract_path, ModelHandlerContract)

        # Verify essential fields are present
        assert contract.handler_id is not None
        assert contract.name is not None
        assert contract.version is not None
        assert contract.descriptor is not None

    def test_handler_id_matches_kind(self, contract: ModelHandlerContract) -> None:
        """Handler ID prefix matches handler_kind."""
        # Extract first segment of handler_id
        prefix = contract.handler_id.split(".")[0].lower()
        handler_kind = contract.descriptor.handler_kind

        # For typed prefixes (effect, compute, reducer, orchestrator),
        # the prefix must match the handler_kind
        assert prefix == handler_kind, (
            f"Handler ID prefix '{prefix}' does not match handler_kind '{handler_kind}'"
        )

        # Verify it's an effect handler
        assert handler_kind == "effect"
        assert contract.handler_id == "effect.demo.support_assistant"

    def test_capability_inputs_defined(self, contract: ModelHandlerContract) -> None:
        """LLM capability is defined."""
        # Should have at least one capability input (the LLM)
        assert len(contract.capability_inputs) >= 1, (
            "Expected at least one capability input (llm)"
        )

        # Find the LLM capability
        llm_cap = None
        for cap in contract.capability_inputs:
            if cap.alias == "llm":
                llm_cap = cap
                break

        assert llm_cap is not None, "LLM capability with alias 'llm' not found"
        assert llm_cap.capability == "ai.llm.chat"
        assert llm_cap.strict is True, "LLM capability should be strict (required)"

        # Verify requirements
        assert llm_cap.requirements is not None
        assert llm_cap.requirements.must is not None
        assert llm_cap.requirements.must.get("supports_structured_output") is True

    def test_input_output_models_specified(
        self, contract: ModelHandlerContract
    ) -> None:
        """Input and output model references are valid."""
        # Input model should be specified
        assert contract.input_model is not None
        assert len(contract.input_model) > 0
        assert (
            contract.input_model
            == "examples.demo.handlers.support_assistant.SupportRequest"
        )

        # Output model should be specified
        assert contract.output_model is not None
        assert len(contract.output_model) > 0
        assert (
            contract.output_model
            == "examples.demo.handlers.support_assistant.SupportResponse"
        )

    def test_effect_handler_is_side_effecting(
        self, contract: ModelHandlerContract
    ) -> None:
        """Effect handler has purity=side_effecting."""
        assert contract.descriptor.purity == "side_effecting", (
            f"Effect handler should have purity='side_effecting', "
            f"got '{contract.descriptor.purity}'"
        )

        # LLM handlers are NOT idempotent - same input can produce different outputs
        # Retries are still useful for transient failures, but outputs may vary
        assert contract.descriptor.idempotent is False, (
            "LLM handlers cannot guarantee idempotency - same prompt may produce different responses"
        )

    def test_retry_policy_configured(self, contract: ModelHandlerContract) -> None:
        """Retry policy is properly configured for transient failures."""
        assert contract.descriptor.retry_policy is not None
        assert contract.descriptor.retry_policy.enabled is True
        assert contract.descriptor.retry_policy.max_retries >= 1
        assert contract.descriptor.retry_policy.backoff_strategy == "exponential"

    def test_circuit_breaker_configured(self, contract: ModelHandlerContract) -> None:
        """Circuit breaker is configured for fault tolerance."""
        assert contract.descriptor.circuit_breaker is not None
        assert contract.descriptor.circuit_breaker.enabled is True
        assert contract.descriptor.circuit_breaker.failure_threshold >= 1
        assert contract.descriptor.circuit_breaker.timeout_ms >= 1000

    def test_timeout_configured(self, contract: ModelHandlerContract) -> None:
        """Timeout is configured for LLM calls."""
        # LLM calls can be slow, so timeout should be reasonable
        assert contract.descriptor.timeout_ms is not None
        assert contract.descriptor.timeout_ms >= 10000  # At least 10 seconds
        assert contract.descriptor.timeout_ms <= 120000  # No more than 2 minutes

    def test_capability_outputs_defined(self, contract: ModelHandlerContract) -> None:
        """Capability outputs are defined."""
        assert len(contract.capability_outputs) >= 1, (
            "Expected at least one capability output"
        )
        assert "support.response.generated" in contract.capability_outputs
        assert "support.escalation.flagged" in contract.capability_outputs

    def test_tags_include_required_categories(
        self, contract: ModelHandlerContract
    ) -> None:
        """Tags include required categories for discovery."""
        required_tags = ["demo", "support", "llm", "effect"]
        for tag in required_tags:
            assert tag in contract.tags, f"Missing required tag: {tag}"

    def test_metadata_includes_ticket(self, contract: ModelHandlerContract) -> None:
        """Metadata includes ticket reference."""
        assert contract.metadata is not None
        assert contract.metadata.get("ticket") == "OMN-1201"
        assert contract.metadata.get("owner") == "demo-team"

    def test_lifecycle_support(self, contract: ModelHandlerContract) -> None:
        """Handler supports lifecycle and health check."""
        assert contract.supports_lifecycle is True
        assert contract.supports_health_check is True

    def test_version_is_semver(self, contract: ModelHandlerContract) -> None:
        """Version follows semantic versioning."""
        # Version pattern is validated by the model, but verify format
        assert contract.version == "1.0.0"
        parts = contract.version.split(".")
        assert len(parts) >= 3
        # First three parts should be numeric
        for part in parts[:3]:
            assert part.isdigit()
