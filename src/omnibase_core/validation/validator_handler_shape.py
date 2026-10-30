# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorHandlerShape -- judge every handler class, bound or not (OMN-21536, K3).

The ``ValidatorBase`` entry of the handler-shape rules: it reads one Python module,
parses it into the facts of ``models/handler_shape`` and hands them with the
contract's rule rows to the pure ``checker_handler_shape.check_handler_shape``. The
scan set and every rule value live in ``contracts/handler_shape.validation.yaml``.
No contract binding is consulted, so a handler class that no contract names is judged
like any other.

Usage (pre-commit hook)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_handler_shape:ValidatorHandlerShape <python files...>
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.handler_shape.model_handler_shape_class import (
    ModelHandlerShapeClass,
)
from omnibase_core.models.handler_shape.model_handler_shape_function import (
    ModelHandlerShapeFunction,
)
from omnibase_core.models.handler_shape.model_handler_shape_method import (
    ModelHandlerShapeMethod,
)
from omnibase_core.models.handler_shape.model_handler_shape_module import (
    ModelHandlerShapeModule,
)
from omnibase_core.validation.checker_handler_shape import check_handler_shape
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorHandlerShape"]

_Function = ast.FunctionDef | ast.AsyncFunctionDef


def _rooted_at(node: ast.expr, receiver: str) -> bool:
    """Whether ``node`` is an attribute chain that starts at the receiver name."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return isinstance(node, ast.Name) and node.id == receiver


def _method_facts(function: _Function) -> ModelHandlerShapeMethod:
    decorators = {d.id for d in function.decorator_list if isinstance(d, ast.Name)}
    args = [*function.args.posonlyargs, *function.args.args]
    receiver = None if "staticmethod" in decorators or not args else args[0].arg
    positional = args if receiver is None else args[1:]
    assigns = False
    calls: list[str] = []
    for node in ast.walk(function):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        for target in targets:
            for leaf in ast.walk(target):
                if (
                    receiver is not None
                    and isinstance(leaf, ast.Attribute)
                    and _rooted_at(leaf, receiver)
                ):
                    assigns = True
        if (
            receiver is not None
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and _rooted_at(node.func.value, receiver)
        ):
            calls.append(node.func.attr)
    return ModelHandlerShapeMethod(
        name=function.name,
        line=function.lineno,
        positional_names=tuple(a.arg for a in positional),
        positional_annotations=tuple(
            ast.unparse(a.annotation) if a.annotation is not None else ""
            for a in positional
        ),
        has_kwargs=function.args.kwarg is not None,
        assigns_self_attribute=assigns,
        self_attribute_calls=tuple(calls),
    )


def module_facts(path: str, source: str) -> ModelHandlerShapeModule:
    """Parse ``source`` into the facts the pure checker judges."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.update({alias.name.rpartition(".")[2], alias.asname or ""})
    names.discard("")
    return ModelHandlerShapeModule(
        path=path,
        classes=tuple(
            ModelHandlerShapeClass(
                name=cls.name,
                line=cls.lineno,
                methods=tuple(
                    _method_facts(m)
                    for m in cls.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                ),
            )
            for cls in tree.body
            if isinstance(cls, ast.ClassDef)
        ),
        functions=tuple(
            ModelHandlerShapeFunction(name=f.name, line=f.lineno)
            for f in tree.body
            if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
        referenced_names=frozenset(names),
    )


class ValidatorHandlerShape(ValidatorBase):
    """Read one module and judge its handler classes against the contract rule rows."""

    validator_id: ClassVar[str] = "handler_shape"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            facts = module_facts(path.as_posix(), path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read module: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        return check_handler_shape(facts, contract.rules)
