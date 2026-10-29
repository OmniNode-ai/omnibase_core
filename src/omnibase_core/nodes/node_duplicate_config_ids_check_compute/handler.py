# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed duplicate-config-ids validation, delegating to the validation-layer checker."""

from __future__ import annotations

from omnibase_core.models.nodes.duplicate_config_ids_check.model_duplicate_config_ids_check_input import (
    ModelDuplicateConfigIdsCheckInput,
)
from omnibase_core.models.nodes.duplicate_config_ids_check.model_duplicate_config_ids_check_output import (
    ModelDuplicateConfigIdsCheckOutput,
)
from omnibase_core.validation.validator_duplicate_config_ids import (
    ValidatorDuplicateConfigIds,
)


class NodeDuplicateConfigIdsCheckCompute:
    """Check every registry declared in a duplicate-id manifest."""

    def handle(
        self, request: ModelDuplicateConfigIdsCheckInput
    ) -> ModelDuplicateConfigIdsCheckOutput:
        """Return the violations the validator finds for the manifest."""
        violations = ValidatorDuplicateConfigIds().check_manifest(
            request.manifest_path, request.repo_root
        )
        return ModelDuplicateConfigIdsCheckOutput(violations=tuple(violations))
