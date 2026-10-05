# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolve core script rules at the runtime boundary, including its fallback."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_aislop_rule import ModelAislopRule
from omnibase_core.nodes.node_ai_slop_check_compute.matcher_ai_slop import compile_rules
from omnibase_core.validation.aislop_rule_loader import resolve_rules


def legacy_rules(*, docstrings: bool) -> list[ModelAislopRule]:
    """Carry the script's hardcoded fallback as typed rule data.

    Inline flag groups preserve its regex behavior under the normal bundled
    docstring compilation flags. In particular the fallback preserves spaces
    and matches reST markers case sensitively.
    """
    if not docstrings:
        return [
            ModelAislopRule(
                name="step_narration",
                pattern_type="regex_line",
                severity="WARNING",
                pattern=r"#\s*Step\s+\d+\s*[:\-]",
                file_globs=["*.md"],
                description="Markdown step narration",
            )
        ]
    patterns = [
        (
            "sycophancy",
            "ERROR",
            r"(?-x:^\s*(Excellent|Great|Sure|Certainly|Absolutely|Of course|Happy to|I would be|Gladly|Wonderful|Perfect|Fantastic|Awesome)[!,. ])",
        ),
        (
            "rest_docstring",
            "ERROR",
            r"(?-ix:^\s*:(param|type|returns?|rtype|raises?|var|ivar|cvar)\b)",
        ),
        (
            "boilerplate_docstring",
            "WARNING",
            r"(?-x:^\s*This\s+(module|class|function|method|file|script|node|handler|service)\s+(provides?|implements?|contains?|is responsible for|handles?|manages?|offers?))",
        ),
        ("md_separator", "WARNING", r"={4,}"),
    ]
    return [
        ModelAislopRule(
            name=name,
            severity="ERROR" if severity == "ERROR" else "WARNING",
            pattern_type="regex_ast_docstring",
            pattern=pattern,
            description=name,
        )
        for name, severity, pattern in patterns
    ]


def resolve_script_rules(root: Path, *, docstrings: bool) -> list[ModelAislopRule]:
    """Reproduce each independently resolved script rule family.

    The old script catches loader and regex failures per family and uses its
    hardcoded patterns. This fallback is required for malformed config parity.
    """
    try:
        rules = resolve_rules(root).rules
        compiled = compile_rules(rules, docstrings=docstrings)
        return [rule for _, rule in compiled.values()]
    except (
        OSError,
        ImportError,
        TypeError,
        ValueError,
        re.error,
        yaml.YAMLError,
        ModelOnexError,
    ):
        return legacy_rules(docstrings=docstrings)
