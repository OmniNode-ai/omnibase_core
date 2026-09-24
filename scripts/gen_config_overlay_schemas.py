# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Write the JSON Schema exports of the config overlay models (OMN-19391).

Stdlib readers (omniclaude hooks, for one) validate overlay documents against
these files instead of importing pydantic. The committed files must equal
``model_json_schema()``; ``tests/unit/models/config_overlay`` enforces that.

    uv run python scripts/gen_config_overlay_schemas.py          # write
    uv run python scripts/gen_config_overlay_schemas.py --check  # exit 1 on drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_core.models.config_overlay import (
    ModelConfigOverlayDocument,
    ModelConfigOverlayScope,
    ModelEmbeddingEndpointOverlay,
    ModelLlmCatalogOverlay,
    ModelLlmPricingOverlay,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

SCHEMA_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "omnibase_core"
    / "schemas"
    / "config_overlay"
)

SCHEMA_EXPORTS: dict[str, type[BaseModel]] = {
    "config_overlay_document.schema.json": ModelConfigOverlayDocument,
    "config_overlay_scope.schema.json": ModelConfigOverlayScope,
    "embedding_endpoint.schema.json": ModelEmbeddingEndpointOverlay,
    "llm_catalog.schema.json": ModelLlmCatalogOverlay,
    "llm_pricing.schema.json": ModelLlmPricingOverlay,
}


def render(model: type[BaseModel]) -> str:
    """The committed text of ``model``'s JSON Schema."""
    return json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on drift")
    args = parser.parse_args(argv)
    drifted: list[str] = []
    for name, model in SCHEMA_EXPORTS.items():
        path = SCHEMA_DIR / name
        text = render(model)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                drifted.append(name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if drifted:
        sys.stderr.write(
            "config overlay schema exports drifted: "
            + ", ".join(drifted)
            + "\nRun: uv run python scripts/gen_config_overlay_schemas.py\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
