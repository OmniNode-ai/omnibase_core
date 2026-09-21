# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the typed LLM-reference generator input projection."""

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_llm_reference_codegen_inputs import (
    ModelLlmReferenceCodegenInputs,
)


@pytest.mark.unit
def test_codegen_projection_normalizes_semver_and_preserves_manifest_identifier() -> (
    None
):
    """The external registry's two differently shaped values stay distinct."""
    inputs = ModelLlmReferenceCodegenInputs.model_validate(
        {
            "model_registry_version": "1.3.0",
            "pricing_manifest_version": "2026-06-11-gemini-25-flash-lite",
        }
    )

    assert str(inputs.model_registry_version) == "1.3.0"
    assert inputs.pricing_manifest_version == "2026-06-11-gemini-25-flash-lite"


@pytest.mark.unit
def test_codegen_projection_rejects_malformed_registry_semver() -> None:
    """A non-SemVer registry version cannot enter the typed code generator."""
    with pytest.raises(ModelOnexError):
        ModelLlmReferenceCodegenInputs.model_validate({"model_registry_version": "v1"})
