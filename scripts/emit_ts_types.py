# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Emit combined JSON Schema for Pydantic models consumed by omnidash-v2.

Usage:
    uv run python scripts/emit_ts_types.py <output_json_path>

The output is a JSON object of the form:
    {
        "$id": "https://omninode.ai/schemas/omnidash-v2.json",
        "$defs": {
            "ModelProjectorContract": { ... Pydantic JSON schema ... },
            "ModelProjectorSchema": { ... },
            ...
        }
    }

Downstream consumer: omnidash-v2 pipes this through json-schema-to-typescript
to emit src/shared/types/generated/onex-models.ts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_core.models.dashboard import (
    ModelActionContract,
    ModelComponentContract,
    ModelDataBindingContract,
    ModelEvidenceRequirementContract,
    ModelOmniStudioEvidenceBundle,
    ModelPermissionContract,
    ModelRendererCapabilityContract,
    ModelRendererThemeContract,
    ModelReviewPacket,
    ModelThemeActivation,
    ModelThemeCatalog,
    ModelThemeCatalogEntry,
    ModelThemeInstance,
    ModelWidgetEnvelope,
    ModelWidgetProvenance,
)
from omnibase_core.models.notifications import ModelStateTransitionNotification
from omnibase_core.models.projectors import (
    ModelDashboardHint,
    ModelProjectorBehavior,
    ModelProjectorColumn,
    ModelProjectorContract,
    ModelProjectorIndex,
    ModelProjectorSchema,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

MODELS: dict[str, type[BaseModel]] = {
    "ModelProjectorContract": ModelProjectorContract,
    "ModelProjectorSchema": ModelProjectorSchema,
    "ModelProjectorColumn": ModelProjectorColumn,
    "ModelProjectorBehavior": ModelProjectorBehavior,
    "ModelProjectorIndex": ModelProjectorIndex,
    "ModelDashboardHint": ModelDashboardHint,
    "ModelStateTransitionNotification": ModelStateTransitionNotification,
    # UI contract primitives (OMN-13130 — Phase 0)
    "ModelComponentContract": ModelComponentContract,
    "ModelActionContract": ModelActionContract,
    "ModelDataBindingContract": ModelDataBindingContract,
    "ModelPermissionContract": ModelPermissionContract,
    "ModelEvidenceRequirementContract": ModelEvidenceRequirementContract,
    "ModelRendererCapabilityContract": ModelRendererCapabilityContract,
    # Versioned design-token contract (OMN-13389) + the instance/catalog
    # layer that gives a token VALUE somewhere to live (OMN-16882, Phase C1)
    "ModelRendererThemeContract": ModelRendererThemeContract,
    "ModelThemeInstance": ModelThemeInstance,
    "ModelThemeCatalogEntry": ModelThemeCatalogEntry,
    "ModelThemeCatalog": ModelThemeCatalog,
    "ModelThemeActivation": ModelThemeActivation,
    # One versioned widget envelope — the unit Plane 1 distributes; carries the
    # config half ModelComponentContract never had (OMN-16883, Phase C2)
    "ModelWidgetEnvelope": ModelWidgetEnvelope,
    "ModelWidgetProvenance": ModelWidgetProvenance,
    # Review Packet + OmniStudio Evidence Bundle (OMN-13387)
    "ModelReviewPacket": ModelReviewPacket,
    "ModelOmniStudioEvidenceBundle": ModelOmniStudioEvidenceBundle,
}


def _combined_defs() -> dict[str, object]:
    """Build root-level definitions so nested ``#/$defs/...`` refs resolve."""
    defs: dict[str, object] = {}
    for name, model in MODELS.items():
        schema = model.model_json_schema()
        nested_defs = schema.pop("$defs", {})
        if not isinstance(nested_defs, dict):
            raise TypeError(f"{name} emitted non-object $defs")
        for nested_name, nested_schema in nested_defs.items():
            existing = defs.get(nested_name)
            if existing is not None and existing != nested_schema:
                raise ValueError(f"conflicting nested schema for {nested_name}")
            defs[nested_name] = nested_schema
        existing = defs.get(name)
        if existing is not None and existing != schema:
            raise ValueError(f"conflicting schema for {name}")
        defs[name] = schema
    return defs


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: emit_ts_types.py <output_json_path>", file=sys.stderr)
        return 1
    output = Path(sys.argv[1])
    combined = {
        "$id": "https://omninode.ai/schemas/omnidash-v2.json",
        "$defs": _combined_defs(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(combined, indent=2))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
