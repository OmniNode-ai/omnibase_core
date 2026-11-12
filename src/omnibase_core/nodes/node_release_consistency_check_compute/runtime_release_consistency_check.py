# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Release-consistency CLI for the release job (OMN-23845, report only).

The container is the composition root: it holds the gather EFFECT, which does
every read, and the COMPUTE node, which judges. Every input arrives as an
argument, the summary path included, so nothing is read from the environment.
Exit codes: 0 AGREE, 1 MISMATCH, 2 UNKNOWN. The release job turns 1 and 2 into
warnings and ends green: in the pilot the report never fails or blocks a
release.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.release_consistency_check.model_release_consistency_gather_input import (
    ModelReleaseConsistencyGatherInput,
)
from omnibase_core.models.nodes.release_consistency_check.model_release_consistency_report import (
    ModelReleaseConsistencyReport,
)
from omnibase_core.nodes.node_release_consistency_check_compute.handler import (
    NodeReleaseConsistencyCheckCompute,
)
from omnibase_core.nodes.node_release_consistency_gather_effect.handler import (
    NodeReleaseConsistencyGatherEffect,
)

_DESCRIPTION = (
    "Report whether a release's tag, its wheel metadata and the files PyPI "
    "serves agree (OMN-23845, report only)."
)


def create_container() -> ModelONEXContainer:
    """Compose the gather EFFECT and the COMPUTE node."""
    container = ModelONEXContainer(enable_service_registry=True)
    registry = container.service_registry

    async def register() -> None:
        await registry.register_instance(
            interface=NodeReleaseConsistencyGatherEffect,
            instance=NodeReleaseConsistencyGatherEffect(),
        )
        await registry.register_instance(
            interface=NodeReleaseConsistencyCheckCompute,
            instance=NodeReleaseConsistencyCheckCompute(),
        )

    asyncio.run(register())
    return container


def render_summary(report: ModelReleaseConsistencyReport) -> str:
    """Markdown for the run summary: the tag, the verdict and every line."""
    rows = "\n".join(f"- {line}" for line in report.lines)
    return f"### Release consistency for {report.tag}: {report.verdict}\n\n{rows}\n"


def main(argv: list[str] | None = None) -> int:
    """Gather, judge, print each line and the verdict, append the summary."""
    parser = argparse.ArgumentParser(description=_DESCRIPTION)
    parser.add_argument("--tag", required=True, help="The release tag, vX.Y.Z.")
    parser.add_argument(
        "--dist", required=True, help="The built dist directory with SHA256SUMS.txt."
    )
    parser.add_argument(
        "--pypi-json",
        default=None,
        help="The saved PyPI JSON for the tag's version; absent means unread.",
    )
    parser.add_argument(
        "--summary-path",
        default=None,
        help="A Markdown file the summary is appended to (the run's step summary).",
    )
    args = parser.parse_args(argv)
    container = create_container()
    gather = container.get_service(NodeReleaseConsistencyGatherEffect)
    check = container.get_service(NodeReleaseConsistencyCheckCompute)
    facts = gather.handle(
        ModelReleaseConsistencyGatherInput(
            tag=args.tag, dist_dir=args.dist, pypi_json_path=args.pypi_json
        )
    )
    report = check.handle(facts)
    for line in report.lines:
        sys.stdout.write(line + "\n")
    sys.stdout.write(f"VERDICT {report.verdict}\n")
    if args.summary_path:
        with Path(args.summary_path).open("a", encoding="utf-8") as handle:
            handle.write(render_summary(report))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
