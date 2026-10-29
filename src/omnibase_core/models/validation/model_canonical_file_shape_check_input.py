# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalFileShapeCheckInput -- input of the canonical-file-shape COMPUTE node (OMN-21515)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_canonical_file_shape_facts import (
    ModelCanonicalFileShapeFacts,
)
from omnibase_core.models.validation.model_node_home_ratchet_request import (
    ModelNodeHomeRatchetRequest,
)


class ModelCanonicalFileShapeCheckInput(BaseModel):
    """The gathered facts and the validator contract whose rule rows apply.

    ``facts`` is None when only the node-home rule runs, ``node_home`` None when
    only the file-shape rules run.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    facts: ModelCanonicalFileShapeFacts | None = None
    node_home: ModelNodeHomeRatchetRequest | None = None
    contract: ModelValidatorSubcontract
