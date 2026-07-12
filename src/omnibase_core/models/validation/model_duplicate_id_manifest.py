# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDuplicateIdManifest — the parsed .duplicate-id-registries.yaml
document declaring, config-as-data, which registries ValidatorDuplicateConfigIds
checks (OMN-14401)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import OnexError
from omnibase_core.models.validation.model_duplicate_id_check_spec import (
    ModelDuplicateIdCheckSpec,
)


class ModelDuplicateIdManifest(BaseModel):
    """Config-as-data manifest: which registries to check, and how."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    registries: tuple[ModelDuplicateIdCheckSpec, ...]

    @classmethod
    def from_yaml(cls, manifest_path: Path) -> ModelDuplicateIdManifest:
        """Load and validate the manifest file.

        Raises OnexError on malformed manifests (unparseable YAML, wrong
        top-level shape, or a registries entry that fails schema validation).
        """
        try:
            raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise OnexError(
                message=f"unparseable manifest YAML at {manifest_path}: {exc}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            ) from exc

        if not isinstance(raw, dict):
            raise OnexError(
                message=(
                    f"manifest {manifest_path} must be a mapping with a "
                    "top-level 'registries' key"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        try:
            return cls.model_validate(raw)
        except ValidationError as exc:
            raise OnexError(
                message=f"manifest {manifest_path} failed schema validation: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
