# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence-shape CLI — local pre-push fail-fast check (OMN-14682).

`uv run python -m omnibase_core.nodes.node_evidence_shape_check_compute.runtime_evidence_shape_check ...`

Validates only the SHAPE of a PR body's Evidence-Source block — that a real
stamp is a single, canonical, top-level line (not an example quoted inside a
fenced code block / blockquote), that it is a well-formed reference or a
recognized disclaimer, and that a valid reference is paired with a canonical
``Evidence-Ticket:`` line. It does NOT verify receipts, contracts, or OCC
ancestry (that needs the onex_change_control checkout and stays the CI
receipt-gate's job). The goal is to give authors fail-fast feedback locally
instead of discovering the mismatch at CI or via manual body normalization.

Body source (in order): ``--pr-body`` > ``--pr-body-file`` > ``--pr-body-file -``
(stdin). Exactly one non-empty source is required.

Exit codes:
    0  — shape is valid (or no Evidence-Source stamp is present at all)
    1  — shape violation (stamp only inside a code block/quote, multiple
         canonical stamps, malformed reference, or missing paired
         Evidence-Ticket)
    2  — usage error (no body source provided)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.evidence_shape_check.model_evidence_shape_check_input import (
    ModelEvidenceShapeCheckInput,
)
from omnibase_core.nodes.node_evidence_shape_check_compute.handler import (
    NodeEvidenceShapeCheckCompute,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync

_NODE_EVIDENCE_SHAPE_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeEvidenceShapeCheckCompute]", NodeEvidenceShapeCheckCompute
)


def _optional_string_argument(args: argparse.Namespace, name: str) -> str | None:
    """Read an optional parser argument without leaking ``Any`` past the CLI boundary."""
    value = getattr(args, name, None)
    if value is None or isinstance(value, str):
        return value
    raise TypeError(  # error-ok: argparse namespace type validation at CLI boundary
        f"parser argument {name!r} must be a string or None"
    )


def _resolve_pr_body(args: argparse.Namespace) -> str | None:
    """Return the PR body from the highest-precedence provided source, else None."""
    pr_body = _optional_string_argument(args, "pr_body")
    if pr_body is not None:
        return pr_body
    pr_body_file = _optional_string_argument(args, "pr_body_file")
    if pr_body_file is not None:
        if pr_body_file == "-":
            return sys.stdin.read()
        return Path(pr_body_file).read_text(encoding="utf-8")
    return None


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (_NODE_EVIDENCE_SHAPE_CHECK_COMPUTE_TOKEN, NodeEvidenceShapeCheckCompute),
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
    parser = argparse.ArgumentParser(
        description=(
            "Evidence-shape pre-push check: validate the Evidence-Source block "
            "shape of a PR body before push (OMN-14682)."
        )
    )
    parser.add_argument(
        "--pr-body",
        default=None,
        help="Full PR description text (highest precedence).",
    )
    parser.add_argument(
        "--pr-body-file",
        default=None,
        help="Path to a file containing the PR body, or '-' to read stdin.",
    )
    args = parser.parse_args(argv)

    body = _resolve_pr_body(args)
    if body is None:
        parser.error("provide --pr-body, --pr-body-file <path>, or --pr-body-file -")

    result = container.get_service(_NODE_EVIDENCE_SHAPE_CHECK_COMPUTE_TOKEN).handle(
        ModelEvidenceShapeCheckInput(pr_body=body)
    )
    if result.passed:
        sys.stdout.write(f"::notice::{result.message}\n")
        return 0
    sys.stdout.write(f"::error::{result.message}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
