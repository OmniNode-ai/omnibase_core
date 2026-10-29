# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the check-no-dict-any hook (OMN-21501).

Usage::

    python -m omnibase_core.handlers.handler_dict_any_cli src/pkg/a.py
    python -m omnibase_core.handlers.handler_dict_any_cli --dir src \\
        --baseline .onex/baselines/check-no-dict-any.yaml [--write-baseline]

The detection is ``HandlerDictAny``; the baseline is the shared
``HandlerFindingBaseline`` (see ``handler_finding_baseline_cli``).
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from functools import cache
from importlib import resources
from typing import Final

from omnibase_core.handlers.handler_dict_any import HandlerDictAny
from omnibase_core.handlers.handler_finding_baseline_cli import run_baselined_hook
from omnibase_core.models.dict_any.model_dict_any_check_input import (
    ModelDictAnyCheckInput,
)
from omnibase_core.models.dict_any.model_dict_any_rules import ModelDictAnyRules
from omnibase_core.models.finding_baseline.model_finding_detect_result import (
    ModelFindingDetectResult,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["HOOK_ID", "load_rules", "main"]

HOOK_ID: Final[str] = "check-no-dict-any"
_RULES_RESOURCE: Final[str] = "dict_any_rules.yaml"
_REMEDIATION: Final[str] = (
    "Replace dict[str, Any] with a typed model, a TypedDict or a union of concrete "
    "value types; as a last resort decorate the function or class with "
    "@allow_dict_any and a justification."
)


@cache
def load_rules() -> ModelDictAnyRules:
    """The rule data shipped inside the package."""
    raw = resources.files("omnibase_core.contracts").joinpath(_RULES_RESOURCE)
    return load_yaml_content_as_model(raw.read_text("utf-8"), ModelDictAnyRules)


def _detect(files: tuple[ModelSourceFile, ...]) -> ModelFindingDetectResult:
    return HandlerDictAny().handle(
        ModelDictAnyCheckInput(files=files, rules=load_rules())
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry. Return 0 within the baseline, 1 on any other finding."""
    return run_baselined_hook(
        argv,
        hook_id=HOOK_ID,
        description="Reject dict[str, Any] annotations; optional shrink-only baseline.",
        detect=_detect,
        remediation=_REMEDIATION,
        default_dirs=("src",),
    )


if __name__ == "__main__":
    sys.exit(main())
