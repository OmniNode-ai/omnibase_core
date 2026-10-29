# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Demo-path topic coherence CLI (OMN-12777).

`onex-demo-path-topic-gate <repo_root> [<repo_root> ...]`
"""

from __future__ import annotations

import sys
from pathlib import Path

from omnibase_core.models.nodes.demo_path_topic_coherence_check.model_demo_path_topic_coherence_check_input import (
    ModelDemoPathTopicCoherenceCheckInput,
)
from omnibase_core.nodes.node_demo_path_topic_coherence_check_compute.handler import (
    NodeDemoPathTopicCoherenceCheckCompute,
)
from omnibase_core.validation.validator_demo_path_topic_coherence import (
    ValidatorDemoPathTopicCoherence,
)


def main() -> None:
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

    result = NodeDemoPathTopicCoherenceCheckCompute().handle(
        ModelDemoPathTopicCoherenceCheckInput(repo_roots=tuple(repo_roots))
    )

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
