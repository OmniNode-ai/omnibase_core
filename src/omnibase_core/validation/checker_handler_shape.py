# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure handler-shape checker: facts in, ``ModelValidationIssue`` out (OMN-21536, K3).

Judges every handler class of a parsed module, bound by a contract or not, against
the rule rows of ``contracts/handler_shape.validation.yaml``. Every pattern, name
list, threshold and remediation text is a ``parameters`` entry of a rule row; nothing
here names a handler, a parameter or a type. The module performs no I/O: no file
read, no clock, no environment.

Rule row kinds (the ``kind`` parameter):

* ``handle_signature`` -- a handler class whose ``handle`` takes parameters the
  shared runtime adapter cannot pass a typed request into.
* ``functions_only_module`` -- a handler module (by file pattern) that holds public
  module-level functions and no class.
* ``forbidden_reference`` -- a handler module that references a forbidden type name.
* ``self_mutation`` -- a public method of a handler class, other than ``handle``,
  that assigns to the receiver or calls a mutating method on one of its attributes.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.handler_shape.model_handler_shape_class import (
    ModelHandlerShapeClass,
)
from omnibase_core.models.handler_shape.model_handler_shape_method import (
    ModelHandlerShapeMethod,
)
from omnibase_core.models.handler_shape.model_handler_shape_module import (
    ModelHandlerShapeModule,
)
from omnibase_core.validation.checker_rule_parameters import (
    rule_int,
    rule_string,
    rule_strings,
)

__all__ = ["check_handler_shape"]


def _pattern(rule: ModelValidatorRule, key: str) -> re.Pattern[str]:
    try:
        return re.compile(rule_string(rule, key))
    except re.error as exc:
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r}: parameters.{key} is not a regular expression: {exc}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        ) from exc


def _issue(
    rule: ModelValidatorRule,
    module: ModelHandlerShapeModule,
    line: int | None,
    detail: str,
) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=rule.severity,
        message=f"{detail} -- {rule_string(rule, 'remediation')}",
        code=rule.rule_id,
        file_path=Path(module.path),
        line_number=line,
        rule_name=rule.rule_id,
    )


def _handler_classes(
    rule: ModelValidatorRule, module: ModelHandlerShapeModule
) -> list[ModelHandlerShapeClass]:
    prefixes = rule_strings(rule, "handler_class_prefixes")
    handle = rule_string(rule, "handle_method_name")
    return [
        cls
        for cls in module.classes
        if cls.name.startswith(prefixes) or any(m.name == handle for m in cls.methods)
    ]


def _adaptable(rule: ModelValidatorRule, method: ModelHandlerShapeMethod) -> str | None:
    """None when the runtime adapter can pass a typed request in, else the reason."""
    if method.has_kwargs or not method.positional_names:
        return None
    if len(method.positional_names) > 1:
        return f"takes {len(method.positional_names)} positional parameters {list(method.positional_names)}"
    name = method.positional_names[0]
    annotation = (
        method.positional_annotations[0] if method.positional_annotations else ""
    )
    typed = (
        annotation
        and annotation not in rule_strings(rule, "non_model_annotations")
        and not any(s in annotation for s in rule_strings(rule, "non_model_substrings"))
        and (
            any(m in annotation for m in rule_strings(rule, "model_annotation_markers"))
            or annotation.endswith(
                tuple(rule_strings(rule, "model_annotation_suffixes"))
            )
        )
    )
    if name in rule_strings(rule, "magic_param_names") or typed:
        return None
    return f"takes one parameter {name!r} that is not a typed request ({annotation or 'untyped'})"


def _require(rule: ModelValidatorRule) -> None:
    """Read every parameter of the rule's kind, so a broken row fails to load."""
    kind = rule_string(rule, "kind")
    keys_by_kind: dict[str, tuple[str, ...]] = {
        "handle_signature": (
            "magic_param_names",
            "non_model_annotations",
            "non_model_substrings",
            "model_annotation_markers",
            "model_annotation_suffixes",
        ),
        "forbidden_reference": ("handler_class_prefixes", "forbidden_names"),
        "self_mutation": (
            "handler_class_prefixes",
            "exempt_method_names",
            "mutating_call_names",
        ),
    }
    for key in keys_by_kind.get(kind, ()):
        rule_strings(rule, key)
    if kind in {"handle_signature", "forbidden_reference", "self_mutation"}:
        rule_string(rule, "handle_method_name")
    if kind in {"functions_only_module", "forbidden_reference"}:
        _pattern(rule, "handler_file_pattern")
    if kind == "functions_only_module":
        rule_string(rule, "private_function_prefix")
        rule_int(rule, "min_public_functions")
    if kind == "self_mutation":
        rule_string(rule, "private_method_prefix")
    rule_string(rule, "remediation")


def _check_rule(
    rule: ModelValidatorRule, module: ModelHandlerShapeModule
) -> list[ModelValidationIssue]:
    _require(rule)
    kind = rule_string(rule, "kind")
    issues: list[ModelValidationIssue] = []
    if kind == "handle_signature":
        handle = rule_string(rule, "handle_method_name")
        for cls in module.classes:
            for method in cls.methods:
                reason = _adaptable(rule, method) if method.name == handle else None
                if reason is not None:
                    issues.append(
                        _issue(
                            rule, module, method.line, f"{cls.name}.{handle} {reason}"
                        )
                    )
    elif kind == "functions_only_module":
        pattern = _pattern(rule, "handler_file_pattern")
        skip = rule_string(rule, "private_function_prefix")
        floor = rule_int(rule, "min_public_functions")
        public = [f for f in module.functions if not f.name.startswith(skip)]
        if pattern.search(module.path) and not module.classes and len(public) >= floor:
            names = ", ".join(f.name for f in public)
            issues.append(
                _issue(
                    rule,
                    module,
                    public[0].line,
                    f"handler module holds module functions only ({names})",
                )
            )
    elif kind == "forbidden_reference":
        pattern = _pattern(rule, "handler_file_pattern")
        forbidden = rule_strings(rule, "forbidden_names")
        if pattern.search(module.path) or _handler_classes(rule, module):
            for name in forbidden:
                if name in module.referenced_names:
                    issues.append(
                        _issue(rule, module, None, f"handler module references {name}")
                    )
    elif kind == "self_mutation":
        handle = rule_string(rule, "handle_method_name")
        exempt = rule_strings(rule, "exempt_method_names")
        private = rule_string(rule, "private_method_prefix")
        mutating = rule_strings(rule, "mutating_call_names")
        for cls in _handler_classes(rule, module):
            for method in cls.methods:
                if (
                    method.name == handle
                    or method.name in exempt
                    or method.name.startswith(private)
                ):
                    continue
                calls = sorted(set(method.self_attribute_calls) & set(mutating))
                if method.assigns_self_attribute or calls:
                    how = (
                        "assigns to self"
                        if method.assigns_self_attribute
                        else f"calls {calls}"
                    )
                    issues.append(
                        _issue(
                            rule,
                            module,
                            method.line,
                            f"{cls.name}.{method.name} is a public method that mutates handler state ({how})",
                        )
                    )
    else:
        raise ModelOnexError(
            message=f"rule {rule.rule_id!r}: unknown kind {kind!r}",
            error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
        )
    return issues


def check_handler_shape(
    module: ModelHandlerShapeModule, rules: Sequence[ModelValidatorRule]
) -> tuple[ModelValidationIssue, ...]:
    """The issues of one module, in rule order then source order.

    Raises ``ModelOnexError`` when an enabled rule row carries an unreadable
    parameter, so an invalid contract fails to load instead of passing.
    """
    issues: list[ModelValidationIssue] = []
    for rule in rules:
        if rule.enabled:
            issues.extend(_check_rule(rule, module))
    return tuple(issues)
