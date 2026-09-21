# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fail-closed error coverage for typed YAML contract projections."""

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_demo_path_yaml_contract import (
    ModelDemoPathYamlContract,
)
from omnibase_core.models.validation.model_fsm_binding_contract_document import (
    ModelFsmBindingContractDocument,
)
from omnibase_core.models.validation.model_occ_append_only_contract import (
    ModelOccAppendOnlyContract,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("projection", "content"),
    [
        (ModelDemoPathYamlContract, "metadata:\n  demo_path: true\n"),
        (ModelOccAppendOnlyContract, "dod_evidence: []\n"),
        (ModelFsmBindingContractDocument, "fsm_handler_binding: {}\n"),
    ],
)
def test_yaml_contract_projections_accept_canonical_mapping_input(
    projection: type[
        ModelDemoPathYamlContract
        | ModelOccAppendOnlyContract
        | ModelFsmBindingContractDocument
    ],
    content: str,
) -> None:
    """Each projection accepts the mapping shape it consumes."""
    assert projection.from_yaml(content)


@pytest.mark.unit
@pytest.mark.parametrize(
    "projection",
    [
        ModelDemoPathYamlContract,
        ModelOccAppendOnlyContract,
        ModelFsmBindingContractDocument,
    ],
)
def test_yaml_contract_projections_raise_canonical_error_for_non_mapping_input(
    projection: type[
        ModelDemoPathYamlContract
        | ModelOccAppendOnlyContract
        | ModelFsmBindingContractDocument
    ],
) -> None:
    """Malformed roots preserve the typed, fail-closed error contract."""
    with pytest.raises(ModelOnexError):
        projection.from_yaml("[]\n")
