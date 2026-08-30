# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Prove — or refuse to prove — that an ``enums/`` diff is purely ADDITIVE.

OMN-16321. ``enums`` is a ``shared_modules`` entry, so step 3 of
``detect_test_paths.compute_selection`` escalates ANY diff touching it to the
40-shard full suite on a bare path-prefix match. Measured cost: a two-member
addition plus ten tests (OMN-16998, external contributor) selected all 44,495
tests, ~10h on the contributor's hardware.

The escalation is a proxy for a real hazard: an enum member that is RENAMED,
REMOVED, or has its VALUE changed can break any consumer — persisted rows,
wire payloads, ``match`` arms, dict lookups keyed by value — arbitrarily far
from the import graph. That hazard is real and this module does not narrow it.

But a diff that only APPENDS members is a different fact. A new member cannot
change the meaning of an existing one; it can only break code that enumerates
the type exhaustively. Exhaustive consumers must reference the enum to
enumerate it, so they are reachable through the reverse-import closure — and
the dynamically-discovering ones (schema/registry/contract sweeps) live under
the always-run ``unnarrowable_test_paths`` roots, which
``_with_unnarrowable`` unions into every narrowed selection unconditionally.

So this module answers exactly one question, structurally rather than
textually: *is every enums/ hunk in this diff a pure addition?* It is a
governed safety classifier and narrows ONLY on positive proof:

* AST-parsed both revisions. A ``SyntaxError`` on either side → NOT provable.
* Every pre-existing ``(class, member, value-literal)`` triple must survive
  byte-identical. A rename, a removal, or a value edit → NOT provable.
* Everything in the module that is NOT an enum member assignment — imports,
  decorators, base classes, methods, module-level statements, docstrings — is
  fingerprinted and must be UNCHANGED. A new method, an edited ``__str__``, a
  changed base class → NOT provable.
* A deleted file, an unreadable base revision, a non-UTF-8 blob → NOT provable.

There is deliberately NO override env var, and no way to assert additivity from
outside: the only input is the two revisions of the file.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

__all__ = [
    "ModelEnumModuleShape",
    "classify_enum_diff_additive",
    "enum_module_shape",
]

# Assignment values that are member DEFINITIONS rather than machinery. An enum
# member is a plain class-body assignment; everything else in the body (methods,
# nested classes, dunder config like `_ignore_`) is captured as structure.
_MEMBER_EXCLUDED_PREFIX = "_"


@dataclass(frozen=True)
class ModelEnumModuleShape:
    """The structural fingerprint of one Python module, split two ways.

    ``members`` maps ``"ClassName.MEMBER"`` to the unparsed source of its value
    expression, so a value edit is visible even when it is a call or an f-string.
    ``structure`` is the unparsed AST of the SAME module with every member
    assignment stripped out — so any non-member edit changes it.
    """

    members: dict[str, str]
    structure: str


def _member_assignment(node: ast.stmt) -> tuple[str, ast.expr] | None:
    """Return ``(member_name, value_expr)`` when ``node`` defines an enum member.

    A member is a plain class-body assignment — ``NAME = <expr>`` or
    ``NAME: ann = <expr>`` — with a single ``Name`` target that does not start
    with an underscore. Everything else (tuple targets, ``_ignore_``/``_order_``
    machinery, augmented assignment, methods, nested classes) is STRUCTURE, and
    is fingerprinted rather than treated as an addable member.
    """
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            return None
        target: ast.expr = node.targets[0]
        value: ast.expr | None = node.value
    elif isinstance(node, ast.AnnAssign):
        target = node.target
        value = node.value
    else:
        return None
    if value is None:
        return None
    if not isinstance(target, ast.Name):
        return None
    if target.id.startswith(_MEMBER_EXCLUDED_PREFIX):
        return None
    return target.id, value


def enum_module_shape(source: str) -> ModelEnumModuleShape | None:
    """Fingerprint ``source``, or ``None`` when it cannot be parsed.

    ``None`` is the fail-closed signal: an unparseable revision is never
    classified additive.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None

    members: dict[str, str] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        surviving: list[ast.stmt] = []
        for stmt in node.body:
            member = _member_assignment(stmt)
            if member is None:
                surviving.append(stmt)
            else:
                name, value = member
                members[f"{node.name}.{name}"] = ast.unparse(value)
        # A class body cannot be empty; keep it syntactically valid so the
        # stripped tree still unparses.
        node.body = surviving or [ast.Pass()]

    try:
        structure = ast.unparse(tree)
    except (AttributeError, ValueError):  # pragma: no cover - defensive
        return None
    return ModelEnumModuleShape(members=members, structure=structure)


def classify_enum_diff_additive(
    old_source: str | None,
    new_source: str | None,
) -> bool:
    """True ONLY when ``new_source`` provably just ADDS members to ``old_source``.

    ``old_source is None`` means the file did not exist at the base revision —
    a brand-new enum module, which adds members and removes none, so it is
    additive. ``new_source is None`` means the file was DELETED (or is
    unreadable) at head, which removes members and is never additive.
    """
    if new_source is None:
        return False
    new_shape = enum_module_shape(new_source)
    if new_shape is None:
        return False
    if old_source is None:
        # New file: nothing pre-existing can have been renamed or removed.
        return True
    old_shape = enum_module_shape(old_source)
    if old_shape is None:
        return False

    # Any non-member edit anywhere in the module disqualifies the diff.
    if old_shape.structure != new_shape.structure:
        return False

    # Every pre-existing member must survive with an identical value literal.
    for key, old_value in old_shape.members.items():
        if new_shape.members.get(key) != old_value:
            return False
    return True
