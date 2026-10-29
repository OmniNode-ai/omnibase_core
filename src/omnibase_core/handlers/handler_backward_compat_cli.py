# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the check-no-backward-compat hook (OMN-21501).

Usage::

    python -m omnibase_core.handlers.handler_backward_compat_cli src/pkg/a.py
    python -m omnibase_core.handlers.handler_backward_compat_cli --dir src \\
        --baseline .onex/baselines/check-no-backward-compat.yaml [--write-baseline]

The detection is ``HandlerBackwardCompat``; the baseline is the shared
``HandlerFindingBaseline`` (see ``handler_finding_baseline_cli``).
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from functools import cache
from importlib import resources
from typing import Final

from omnibase_core.handlers.handler_backward_compat import HandlerBackwardCompat
from omnibase_core.handlers.handler_finding_baseline_cli import run_baselined_hook
from omnibase_core.models.backward_compat.model_backward_compat_check_input import (
    ModelBackwardCompatCheckInput,
)
from omnibase_core.models.backward_compat.model_backward_compat_rules import (
    ModelBackwardCompatRules,
)
from omnibase_core.models.finding_baseline.model_finding_detect_result import (
    ModelFindingDetectResult,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["HOOK_ID", "load_rules", "main"]

HOOK_ID: Final[str] = "check-no-backward-compat"
_RULES_RESOURCE: Final[str] = "backward_compat_rules.yaml"


@cache
def load_rules() -> ModelBackwardCompatRules:
    """The rule data shipped inside the package."""
    raw = resources.files("omnibase_core.contracts").joinpath(_RULES_RESOURCE)
    return load_yaml_content_as_model(raw.read_text("utf-8"), ModelBackwardCompatRules)


def _detect(files: tuple[ModelSourceFile, ...]) -> ModelFindingDetectResult:
    return HandlerBackwardCompat().handle(
        ModelBackwardCompatCheckInput(files=files, rules=load_rules())
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry. Return 0 within the baseline, 1 on any other finding."""
    rules = load_rules()
    return run_baselined_hook(
        argv,
        hook_id=HOOK_ID,
        description="Reject backcompat anti-patterns; optional shrink-only baseline.",
        detect=_detect,
        remediation=rules.remediation,
        default_dirs=(),
        encodings=rules.encodings,
        max_bytes=rules.max_file_size_bytes,
        skip_dir_parts=frozenset(rules.skip_dir_parts),
    )


if __name__ == "__main__":
    sys.exit(main())
