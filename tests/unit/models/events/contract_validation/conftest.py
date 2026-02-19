# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared fixtures for contract validation event model tests."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_validation_mode import EnumValidationMode
from omnibase_core.models.events.contract_validation import (
    ModelContractRef,
    ModelContractValidationContext,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.fixture
def sample_contract_id() -> str:
    """Provide a sample contract ID for tests."""
    return "runtime-host-contract"


@pytest.fixture
def sample_run_id() -> UUID:
    """Provide a unique run ID for tests."""
    return uuid4()


@pytest.fixture
def sample_actor_id() -> UUID:
    """Provide a unique actor ID for tests."""
    return uuid4()


@pytest.fixture
def sample_correlation_id() -> UUID:
    """Provide a unique correlation ID for tests."""
    return uuid4()


@pytest.fixture
def sample_contract_ref(sample_contract_id: str) -> ModelContractRef:
    """Provide a sample ModelContractRef for tests."""
    return ModelContractRef(
        contract_id=sample_contract_id,
        path=Path("/contracts/runtime-host.yaml"),
        content_hash="sha256:abc123def456",
        schema_version=ModelSemVer(major=1, minor=0, patch=0),
    )


@pytest.fixture
def minimal_contract_ref() -> ModelContractRef:
    """Provide a minimal ModelContractRef with only required fields."""
    return ModelContractRef(contract_id="minimal-contract")


@pytest.fixture
def sample_validation_context_strict() -> ModelContractValidationContext:
    """Provide a strict validation context."""
    return ModelContractValidationContext(
        mode=EnumValidationMode.STRICT,
        flags={"validate_schema": True, "validate_references": True},
    )


@pytest.fixture
def sample_validation_context_permissive() -> ModelContractValidationContext:
    """Provide a permissive validation context."""
    return ModelContractValidationContext(
        mode=EnumValidationMode.PERMISSIVE,
        flags={"skip_optional_checks": True},
    )


@pytest.fixture
def default_validation_context() -> ModelContractValidationContext:
    """Provide a default validation context (STRICT mode, no flags)."""
    return ModelContractValidationContext()
