#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Generate typed LogicalModelKey and EndpointRef constants (OMN-11932).

Reads:
  $OMNI_HOME/omnibase_infra/contracts/llm_endpoints.yaml
  $OMNI_HOME/omnimarket/src/omnimarket/data/model_registry/model_registry_v1.yaml

Writes:
  src/omnibase_core/constants/constants_llm_refs.py

Run:
  uv run python scripts/generate_llm_refs.py          # generate + write
  uv run python scripts/generate_llm_refs.py --check  # drift detection (CI mode)

Exit codes:
  0 - Success / no drift
  1 - Drift detected (--check mode) or generation error
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

OMNI_HOME = Path(os.environ["OMNI_HOME"])

ENDPOINTS_YAML = OMNI_HOME / "omnibase_infra" / "contracts" / "llm_endpoints.yaml"
REGISTRY_YAML = (
    OMNI_HOME
    / "omnimarket"
    / "src"
    / "omnimarket"
    / "data"
    / "model_registry"
    / "model_registry_v1.yaml"
)

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = (
    REPO_ROOT / "src" / "omnibase_core" / "constants" / "constants_llm_refs.py"
)

def _to_enum_name(value: str) -> str:
    upper = value.upper()
    # Replace runs of non-alphanumeric chars with _
    name = re.sub(r"[^A-Z0-9]+", "_", upper)
    # Strip leading/trailing underscores
    name = name.strip("_")
    return name


def _load_yaml(path: Path) -> dict:  # type: ignore[type-arg]
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at top level of {path}")
    return data


def _generate(endpoints_yaml: Path, registry_yaml: Path) -> str:
    endpoints_data = _load_yaml(endpoints_yaml)
    registry_data = _load_yaml(registry_yaml)

    endpoints = endpoints_data.get("endpoints", [])
    models = registry_data.get("models", {})

    model_entries: list[tuple[str, str]] = []
    for model_id in models:
        model_entries.append((_to_enum_name(model_id), model_id))

    endpoint_entries: list[tuple[str, str]] = []
    for slot in endpoints:
        slot_id = slot["slot_id"]
        endpoint_entries.append((_to_enum_name(slot_id), slot_id))

    model_lines = "\n".join(f'    {name} = "{value}"' for name, value in model_entries)
    endpoint_lines = "\n".join(
        f'    {name} = "{value}"' for name, value in endpoint_entries
    )

    return f"""\
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# ============================================================
# AUTO-GENERATED — do not edit by hand.
# Source:
#   omnibase_infra/contracts/llm_endpoints.yaml
#   omnimarket/src/omnimarket/data/model_registry/model_registry_v1.yaml
# Generator: scripts/generate_llm_refs.py (OMN-11932)
# Regenerate: uv run python scripts/generate_llm_refs.py
# ============================================================

\"\"\"
Typed compile-time constants for LLM model keys and endpoint slot references.

Use these instead of bare string literals so that typos become import errors
and IDEs can autocomplete slot/model identifiers.

LogicalModelKey — canonical model identifiers from model_registry_v1.yaml.
EndpointRef     — canonical slot IDs from llm_endpoints.yaml (all statuses).
\"\"\"

from __future__ import annotations

from enum import StrEnum


class LogicalModelKey(StrEnum):
    \"\"\"Canonical model identifiers from model_registry_v1.yaml.\"\"\"

{model_lines}


class EndpointRef(StrEnum):
    \"\"\"Canonical slot IDs from llm_endpoints.yaml (all statuses included).\"\"\"

{endpoint_lines}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Drift-detection mode: fail if generated output differs from on-disk file.",
    )
    args = parser.parse_args()

    generated = _generate(ENDPOINTS_YAML, REGISTRY_YAML)

    if args.check:
        if not OUTPUT_PATH.exists():
            print(
                f"DRIFT: {OUTPUT_PATH} does not exist. Run generate_llm_refs.py to create it."
            )
            sys.exit(1)
        on_disk = OUTPUT_PATH.read_text()
        if generated != on_disk:
            print(
                f"DRIFT: {OUTPUT_PATH} is out of date.\n"
                "Run: uv run python scripts/generate_llm_refs.py"
            )
            sys.exit(1)
        print("OK: constants_llm_refs.py matches source YAMLs.")
    else:
        OUTPUT_PATH.write_text(generated)
        print(f"Written: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
