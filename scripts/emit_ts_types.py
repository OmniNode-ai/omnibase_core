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

Note: ``ModelDashboardHint`` is planned (Part 1 of the dashboard local-integration
plan) but not yet in the tree. It will be added to ``MODELS`` once that lands.
See docs/plans/2026-04-17-dashboard-local-integration.md in omni_home.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_core.models.notifications import ModelStateTransitionNotification
from omnibase_core.models.projectors import (
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
    "ModelStateTransitionNotification": ModelStateTransitionNotification,
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: emit_ts_types.py <output_json_path>", file=sys.stderr)
        return 1
    output = Path(sys.argv[1])
    combined = {
        "$id": "https://omninode.ai/schemas/omnidash-v2.json",
        "$defs": {name: model.model_json_schema() for name, model in MODELS.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(combined, indent=2))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
