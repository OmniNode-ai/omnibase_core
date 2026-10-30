# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Duplicate-config-ids CLI (OMN-14401).

`uv run python -m omnibase_core.nodes.node_duplicate_config_ids_check_compute.runtime_duplicate_config_ids_check`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.errors import OnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.duplicate_config_ids_check.model_duplicate_config_ids_check_input import (
    ModelDuplicateConfigIdsCheckInput,
)
from omnibase_core.nodes.node_duplicate_config_ids_check_compute.handler import (
    NodeDuplicateConfigIdsCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync

_NODE_DUPLICATE_CONFIG_IDS_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeDuplicateConfigIdsCheckCompute]", NodeDuplicateConfigIdsCheckCompute
)


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (
            _NODE_DUPLICATE_CONFIG_IDS_CHECK_COMPUTE_TOKEN,
            NodeDuplicateConfigIdsCheckCompute,
        ),
    ):
        run_coro_sync(
            registry.register_service(
                token,
                implementation,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    return container


def main(
    argv: list[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Run the CLI with container-resolved services."""
    owned = container is None
    if container is None:
        container = build_container()
    try:
        return _run(argv, container)
    finally:
        if owned:
            container.close()


def _run(argv: list[str] | None, container: ModelONEXContainer) -> int:
    """CLI entrypoint.

    Exit codes:
        0 — no violations (including: no manifest declared yet)
        1 — violations found, or the manifest itself is malformed
    """
    parser = argparse.ArgumentParser(
        prog="check-duplicate-registry-ids",
        description=(
            "Reject config/registry YAML files declaring duplicate ids over a "
            "key that is not guaranteed unique. Checked registries are declared "
            "config-as-data in a manifest file."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(".duplicate-id-registries.yaml"),
        help="Path to the manifest file (default: .duplicate-id-registries.yaml)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(),
        help="Root directory registry paths in the manifest are relative to (default: cwd)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Ignored — accepted for pre-commit pass_filenames compatibility",
    )
    parsed = parser.parse_args(argv)

    if not parsed.manifest.is_file():
        sys.stdout.write(
            f"No manifest at {parsed.manifest} — no registries opted in, nothing to check.\n"
        )
        return 0

    try:
        violations = (
            container.get_service(_NODE_DUPLICATE_CONFIG_IDS_CHECK_COMPUTE_TOKEN)
            .handle(
                ModelDuplicateConfigIdsCheckInput(
                    manifest_path=parsed.manifest, repo_root=parsed.repo_root
                )
            )
            .violations
        )
    except OnexError as exc:
        sys.stdout.write(f"FAIL: cannot load manifest {parsed.manifest}: {exc}\n")
        return 1

    for v in violations:
        label = f" [group={v.group_label}]" if v.group_label else ""
        sys.stdout.write(f"{v.registry_path}{label}: {v.detail}\n")

    if violations:
        sys.stdout.write(f"\n{len(violations)} duplicate-id registry violation(s).\n")
        return 1

    sys.stdout.write("No duplicate-id registry violations found.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
