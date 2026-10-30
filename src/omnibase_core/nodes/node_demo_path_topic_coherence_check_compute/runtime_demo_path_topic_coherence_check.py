# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Demo-path topic coherence CLI (OMN-12777).

`onex-demo-path-topic-gate <repo_root> [<repo_root> ...]`
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.demo_path_topic_coherence_check.model_demo_path_topic_coherence_check_input import (
    ModelDemoPathTopicCoherenceCheckInput,
)
from omnibase_core.nodes.node_demo_path_topic_coherence_check_compute.handler import (
    NodeDemoPathTopicCoherenceCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_demo_path_topic_coherence import (
    ValidatorDemoPathTopicCoherence,
)

_NODE_DEMO_PATH_TOPIC_COHERENCE_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeDemoPathTopicCoherenceCheckCompute]",
    NodeDemoPathTopicCoherenceCheckCompute,
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
            _NODE_DEMO_PATH_TOPIC_COHERENCE_CHECK_COMPUTE_TOKEN,
            NodeDemoPathTopicCoherenceCheckCompute,
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


def main(*, container: ModelONEXContainer | None = None) -> None:
    """Run the CLI with container-resolved services."""
    owned = container is None
    if container is None:
        container = build_container()
    try:
        return _run(container)
    finally:
        if owned:
            container.close()


def _run(container: ModelONEXContainer) -> None:
    """CLI entry point.

    Usage:
        onex-demo-path-topic-gate <repo_root> [<repo_root> ...]
        python -m omnibase_core.nodes.node_demo_path_topic_coherence_check_compute.runtime_demo_path_topic_coherence_check <roots...>
    """
    args = sys.argv[1:]
    if not args:
        sys.stderr.write(
            "Usage: onex-demo-path-topic-gate <repo_root> [<repo_root> ...]\n"
        )
        sys.exit(2)

    repo_roots = [Path(a).resolve() for a in args]
    missing = [str(r) for r in repo_roots if not r.is_dir()]
    if missing:
        sys.stderr.write(f"Error: directories not found: {missing}\n")
        sys.exit(2)

    result = container.get_service(
        _NODE_DEMO_PATH_TOPIC_COHERENCE_CHECK_COMPUTE_TOKEN
    ).handle(ModelDemoPathTopicCoherenceCheckInput(repo_roots=tuple(repo_roots)))

    sys.stdout.write(f"{result.summary}\n")
    if result.issues:
        sys.stdout.write("\n")
        for issue in result.issues:
            location = ""
            if issue.file_path:
                location = str(issue.file_path)
                if issue.line_number:
                    location += f":{issue.line_number}"
                location += ": "
            sys.stdout.write(f"  [ERROR] {location}{issue.message}\n")

    sys.exit(ValidatorDemoPathTopicCoherence.get_exit_code(result))


if __name__ == "__main__":
    main()
