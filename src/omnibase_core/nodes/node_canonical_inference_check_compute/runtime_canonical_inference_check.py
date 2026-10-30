# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical-inference ratchet CLI — pre-commit hook + CI gate (OMN-13219).

`uv run python -m omnibase_core.nodes.node_canonical_inference_check_compute.runtime_canonical_inference_check`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.nodes.canonical_inference_check.model_canonical_inference_check_input import (
    ModelCanonicalInferenceCheckInput,
)
from omnibase_core.models.nodes.text_file_write.model_text_file_write_input import (
    ModelTextFileWriteInput,
)
from omnibase_core.nodes.node_canonical_inference_check_compute.handler import (
    NodeCanonicalInferenceCheckCompute,
)
from omnibase_core.nodes.node_text_file_write_effect.handler import (
    NodeTextFileWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_canonical_inference import (
    DEFAULT_BASELINE,
    SUPPRESS_ANNOTATION,
    assert_baseline_shrinks_only,
    load_baseline,
    scan_source,
    scan_tree,
)

_NODE_TEXT_FILE_WRITE_EFFECT_TOKEN = cast(
    "type[NodeTextFileWriteEffect]", NodeTextFileWriteEffect
)
_NODE_CANONICAL_INFERENCE_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeCanonicalInferenceCheckCompute]", NodeCanonicalInferenceCheckCompute
)


def _err(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def _out(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def _update_baseline(
    container: ModelONEXContainer,
    repo: str,
    repo_root: Path,
    baseline_path: Path,
    *,
    seed: bool,
) -> int:
    """Regenerate this repo's baseline subset (burn-down only)."""
    prior_entries: list[dict[str, str]] = []
    if baseline_path.exists():
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
        all_entries = data.get("violations", []) if isinstance(data, dict) else []
        prior_entries = [
            e for e in all_entries if isinstance(e, dict) and "fingerprint" in e
        ]
    repo_before = {e["fingerprint"] for e in prior_entries if e.get("repo") == repo}
    other_entries = [e for e in prior_entries if e.get("repo") != repo]

    fresh_violations = scan_tree(repo, repo_root)
    fresh: list[dict[str, str]] = [
        {
            "repo": v.repo,
            "path": v.path,
            "rule": v.rule,
            "fingerprint": v.fingerprint,
        }
        for v in fresh_violations
    ]
    repo_after = {e["fingerprint"] for e in fresh}

    if not seed:
        try:
            assert_baseline_shrinks_only(repo_before, repo_after)
        except ValueError as exc:
            _err(f"CANONICAL-INFERENCE BASELINE REJECTED: {exc}")
            return 1

    merged = sorted(
        [*other_entries, *fresh],
        key=lambda e: (e["repo"], e["path"], e["fingerprint"]),
    )
    container.get_service(_NODE_TEXT_FILE_WRITE_EFFECT_TOKEN).handle(
        ModelTextFileWriteInput(
            path=str(baseline_path),
            text=json.dumps(
                {"schema_version": "1.0.0", "count": len(merged), "violations": merged},
                indent=2,
            )
            + "\n",
        )
    )
    action = "seeded" if seed else f"burned down {len(repo_before) - len(repo_after)}"
    _out(
        f"CANONICAL-INFERENCE BASELINE updated for {repo}: {len(repo_after)} "
        f"violation(s) ({action}). Total across repos: {len(merged)}."
    )
    return 0


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (_NODE_TEXT_FILE_WRITE_EFFECT_TOKEN, NodeTextFileWriteEffect),
        (
            _NODE_CANONICAL_INFERENCE_CHECK_COMPUTE_TOKEN,
            NodeCanonicalInferenceCheckCompute,
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
    """CLI entry point.

    Staged-files mode (pre-commit): pass file paths as positional args.
    Full-repo mode (CI): pass ``--all --repo <name> --repo-root <path>``.
    Baseline update: pass ``--seed`` or ``--update-baseline``.

    Exit codes:
        0 — no new violations (or grandfathered-only)
        1 — new violation(s) found or baseline grew
    """
    parser = argparse.ArgumentParser(
        prog="check-canonical-inference",
        description="canonical-inference ratchet gate (OMN-13219).",
    )
    parser.add_argument(
        "paths", nargs="*", help="Explicit files to scan (staged set, pre-commit mode)."
    )
    parser.add_argument(
        "--repo", default="omnibase_core", help="Repo name for fingerprints."
    )
    parser.add_argument(
        "--repo-root", default=".", help="Repo root for repo-relative paths."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Full-repo scan (CI mode) instead of explicit staged files.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Regenerate this repo's baseline subset (burn-down only).",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="One-time initialization of this repo's baseline subset (no shrink check).",
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE),
        help="Path to the baseline JSON.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    baseline_path = Path(args.baseline)

    if args.update_baseline or args.seed:
        return _update_baseline(
            container, args.repo, repo_root, baseline_path, seed=args.seed
        )

    if args.all:
        violations = scan_tree(args.repo, repo_root)
    else:
        if not args.paths:
            _out("CANONICAL-INFERENCE GATE: no files to scan.")
            return 0
        violations = []
        for raw in args.paths:
            p = Path(raw)
            if not p.is_file() or p.suffix != ".py":
                continue
            try:
                source = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                rel = str(p.resolve().relative_to(repo_root.resolve()))
            except ValueError:
                rel = str(p)
            violations.extend(scan_source(args.repo, rel, source, source_path=p))

    verdict = container.get_service(
        _NODE_CANONICAL_INFERENCE_CHECK_COMPUTE_TOKEN
    ).handle(
        ModelCanonicalInferenceCheckInput(
            violations=tuple(violations),
            baseline_fingerprints=frozenset(load_baseline(baseline_path)),
        )
    )
    new = verdict.new
    grandfathered = verdict.grandfathered

    if new:
        _err(
            f"CANONICAL-INFERENCE GATE FAILED: {len(new)} NEW violation(s) — inference "
            "must go through the contract-driven routing authority (bus / "
            "inference-effect / Bifrost); model + provider resolve from the routing "
            "contract, never a shelled model CLI or env var.\n"
        )
        for v in new:
            _err(f"  [{v.rule}] {v.repo}/{v.path}:{v.line}")
            _err(f"    {v.snippet}")
            _err(
                "    -> route through the canonical inference path, or annotate "
                f"{SUPPRESS_ANNOTATION} <reason>"
            )
        return 1

    _out(
        f"CANONICAL-INFERENCE GATE PASSED: 0 new violations "
        f"({len(grandfathered)} grandfathered)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
