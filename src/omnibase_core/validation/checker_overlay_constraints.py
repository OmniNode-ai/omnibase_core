# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure overlay-constraints checker: a declaration and overlay values in, issues out (OMN-22185).

A contract declares derived names (sums of overlay keys or numbers) and relations between
overlay keys. A relation whose key is absent or not a number, whose syntax is not two sums
joined by one comparison operator, or whose comparison does not hold, is refused with a
diagnostic naming the relation. Operators, term syntax and diagnostics are parameters of
``overlay_constraints.validation.yaml``; this module holds no rule data, no overlay key and
no repository name.
"""

from __future__ import annotations

import ast
import re

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.overlay_constraints.model_overlay_constraints_check_input import (
    ModelOverlayConstraintsCheckInput,
)
from omnibase_core.models.overlay_constraints.model_overlay_constraints_check_result import (
    ModelOverlayConstraintsCheckResult,
)
from omnibase_core.models.overlay_constraints.model_overlay_constraints_rules import (
    ModelOverlayConstraintsRules,
)

__all__ = ["check_overlay_constraints"]


class _Malformed(ValueError):
    """A relation or derived name whose text is not a sum or a comparison."""


def _fill(template: str, **fields: str) -> str:
    """Fill a contract template; a template naming an unknown field is a contract error."""
    try:
        return template.format(**fields)
    except (KeyError, IndexError, ValueError) as exc:
        raise ModelOnexError(
            message=f"rule template {template!r} cannot be filled: {exc!r}",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        ) from exc


def _holds(operator_text: str, left: float, right: float) -> bool:
    """Apply a comparison operator written as Python writes it."""
    try:
        op = ast.parse(f"0 {operator_text} 0", mode="eval").body
    except SyntaxError as exc:
        raise ModelOnexError(
            message=f"operator {operator_text!r} is not a comparison operator",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        ) from exc
    if not isinstance(op, ast.Compare) or len(op.ops) != 1:
        raise ModelOnexError(
            message=f"operator {operator_text!r} is not one comparison operator",
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )
    match op.ops[0]:
        case ast.Lt():
            return left < right
        case ast.LtE():
            return left <= right
        case ast.Gt():
            return left > right
        case ast.GtE():
            return left >= right
        case ast.Eq():
            return left == right
        case ast.NotEq():
            return left != right
        case _:
            raise ModelOnexError(
                message=f"operator {operator_text!r} is not an ordering or equality",
                error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
            )


def check_overlay_constraints(
    request: ModelOverlayConstraintsCheckInput,
) -> ModelOverlayConstraintsCheckResult:
    """Judge every declared relation against the overlay values."""
    rules = ModelOverlayConstraintsRules.from_contract(request.contract)
    syntax = rules.row("relation_malformed")
    identifier = syntax.pattern("identifier_pattern")
    number = syntax.pattern("number_pattern")
    separator = syntax.texts["sum_separator"]
    splitter = re.compile(
        "("
        + "|".join(
            re.escape(o)
            for o in sorted(syntax.lists["operators"], key=len, reverse=True)
        )
        + ")"
    )
    found: list[ModelValidationIssue] = []
    judged = 0

    def add(code: str, relation_name: str, expression: str, **fields: str) -> None:
        row = rules.row(code)
        if not row.enabled or not row.judges(request.source_name):
            return
        context = {
            "source": request.source_name,
            "relation": relation_name,
            "expression": expression,
            **fields,
        }
        found.append(
            ModelValidationIssue(
                severity=row.severity,
                message=_fill(row.message, **context),
                code=code,
                rule_name=code,
                context=context,
            )
        )

    def terms(text: str, derived_ok: bool) -> list[str | float]:
        """A sum's terms as key names (str) and numbers (float)."""
        out: list[str | float] = []
        for raw in text.split(separator):
            term = raw.strip()
            if number.match(term):
                out.append(float(term))
            elif identifier.match(term):
                if term in request.declaration.derived:
                    if not derived_ok:
                        raise _Malformed(
                            f"derived name {term} is defined by another derived name"
                        )
                    out.extend(terms(request.declaration.derived[term], False))
                else:
                    out.append(term)
            else:
                raise _Malformed(f"{term!r} is neither an overlay key nor a number")
        return out

    for relation in request.declaration.relations:
        pieces = splitter.split(relation.expression)
        if len(pieces) != 3:
            add(
                "relation_malformed",
                relation.relation_name,
                relation.expression,
                reason="it needs exactly one comparison operator",
            )
            continue
        try:
            sides = (terms(pieces[0], True), terms(pieces[2], True))
        except _Malformed as exc:
            add(
                "relation_malformed",
                relation.relation_name,
                relation.expression,
                reason=str(exc),
            )
            continue
        total: list[float] = []
        refused = False
        for side in sides:
            subtotal = 0.0
            for term in side:
                if not isinstance(term, str):
                    subtotal += term
                    continue
                if term not in request.values:
                    add(
                        "key_absent",
                        relation.relation_name,
                        relation.expression,
                        key=term,
                    )
                    refused = True
                    continue
                value = request.values[term]
                if isinstance(value, bool) or not isinstance(value, int | float):
                    add(
                        "value_not_numeric",
                        relation.relation_name,
                        relation.expression,
                        key=term,
                    )
                    refused = True
                    continue
                subtotal += value
            total.append(subtotal)
        if refused:
            continue
        judged += 1
        if not _holds(pieces[1], total[0], total[1]):
            add(
                "relation_violated",
                relation.relation_name,
                relation.expression,
                left=f"{total[0]:g}",
                operator=pieces[1],
                right=f"{total[1]:g}",
            )

    return ModelOverlayConstraintsCheckResult(
        issues=tuple(found),
        exit_code=1 if any(i.severity.is_error_or_above() for i in found) else 0,
        relations_checked=judged,
    )
