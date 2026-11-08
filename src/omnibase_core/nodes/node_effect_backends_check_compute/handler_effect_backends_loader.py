# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Effect boundary of the effect-backends validator: read node contracts from a directory."""

from __future__ import annotations

from pathlib import Path

import yaml

from omnibase_core.models.validation.model_effect_backends_load_request import (
    ModelEffectBackendsLoadRequest,
)
from omnibase_core.models.validation.model_effect_contract_document import (
    ModelEffectContractDocument,
)
from omnibase_core.models.validation.model_loaded_contracts import ModelLoadedContracts
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

CONTRACT_FILE_NAME = "contract.yaml"
KEPT_FIELDS = frozenset({"node_name", "name", "node_type", "backends"})


class HandlerEffectBackendsLoader:
    """Effect boundary: read the contracts of one directory."""

    def handle(self, request: ModelEffectBackendsLoadRequest) -> ModelLoadedContracts:
        """Parse every ``*/contract.yaml`` under ``root``; a file that does not parse is reported."""
        root = Path(request.root)
        documents: list[ModelEffectContractDocument] = []
        unreadable: list[str] = []
        for path in sorted(root.glob(f"*/{CONTRACT_FILE_NAME}")):
            try:
                parsed = load_yaml_mapping_no_duplicates(
                    path.read_text(encoding="utf-8"), source=str(path)
                )
            except (OSError, ValueError, yaml.YAMLError):
                unreadable.append(str(path))
                continue
            kept: dict[str, object] = {
                key: value
                for key, value in parsed.items()
                if isinstance(key, str) and key in KEPT_FIELDS
            }
            documents.append(ModelEffectContractDocument(path=str(path), document=kept))
        return ModelLoadedContracts(
            documents=tuple(documents), unreadable=tuple(unreadable)
        )
