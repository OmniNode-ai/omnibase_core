# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One targeted-column UPSERT plan, rendered into each driver's placeholder style.

WHY THIS LIVES IN CORE (OMN-18159)

Four implementations of the same statement exist across this workspace: the
delegation projection runner's asyncpg ``_dynamic_upsert`` (``$N``), and
``omnimarket``'s psycopg2 (``%(name)s``), SQLite (``:name``) and in-memory sync
adapters -- plus the runtime kernel's own projection database operations in
``omnibase_infra``. They already agreed on the easy half (conflict-key
splitting, the missing-key refusal, ``DO NOTHING`` when no column is updatable)
and had drifted apart on the half that matters: only the asyncpg one grew the
write-attestation features that the staging green bar's writer-principal clause
reads.

``omnimarket`` and ``omnibase_infra`` both depend on ``omnibase_core`` and
``omnibase_core`` depends on neither, so under the compat -> core -> spi ->
infra layering this is the only place both can share one copy. Putting it here
rather than duplicating it into the second consumer is the whole point: a
decision made in one place cannot diverge between write paths; a decision
copied into four cannot help but.

This module holds NO I/O. It owns the DECISIONS -- which column goes on which
arm, which expression is admissible, which identifier is safe -- and leaves
each adapter owning only its driver's parameter binding.

WHAT A "TARGETED-COLUMN" UPSERT MEANS, since every adapter must agree on it:
``EXCLUDED`` overwrite for the columns present in ``row`` ONLY. A column absent
from ``row`` is left untouched on an existing row and takes its database
default on INSERT. That is the contract every caller of a sync projection
database adapter already relies on, and it is what makes sticky-evidence merge
paths safe.

THE THREE FEATURES BEYOND A PLAIN UPSERT, and why each is not a nicety:

``sql_expression_columns``
    A column whose value is a SQL EXPRESSION that Postgres evaluates per row,
    on BOTH arms -- never a bound parameter. ``writer_identity = CURRENT_USER``
    is the whole reason a projection row can answer "which database principal
    wrote this": a bound parameter would let the writing process choose the
    answer, and a column recording whatever the application asserts attests to
    nothing. The expression is restated on the ``DO UPDATE`` arm because a
    column DEFAULT is consulted only on INSERT, so an existing row would
    otherwise wear its first writer's stamp for the rest of its life. Because
    these strings reach the composed statement UNCAST and unparameterised, the
    admissible set is CLOSED (:data:`ALLOWED_WRITE_ATTESTATION_SQL`) and
    checked here, never interpolated from a caller's string.

``insert_only_columns``
    Named on the INSERT arm, withheld from ``DO UPDATE SET``: "attribute the
    row I create, never re-attribute one that already exists". Both halves are
    load-bearing under row-level security, and the INSERT half is the
    non-obvious one. Postgres evaluates the policy's ``WITH CHECK`` against the
    PROPOSED insert row BEFORE the conflict is resolved, so a targeted-column
    upsert that omits ``tenant_id`` proposes a row carrying the column default
    and is refused outright whenever ``app.tenant_id`` is anything else -- even
    when the statement was only ever going to take the update arm.

``returning``
    The row the database actually stored. A writer cannot know what it wrote
    for a column the database stamped, so a republish built from the writer's
    own row dict would serve an attestation nothing attested to.

WHY THESE RAISE ``ValueError``/``KeyError`` AND NOT ``OnexError``

Every refusal here rejects a CALLER-SUPPLIED ARGUMENT before any statement is
composed -- a malformed identifier, an inadmissible expression, a row missing
its own conflict key. That is the standard-Python function-boundary case this
repo's error-handling guidance assigns to ``ValueError``, not an ONEX runtime
condition that needs an error code, a correlation id or a serialized envelope.

There is also a hard compatibility constraint. All four adapters that will
adopt this builder already raise exactly these types for exactly these inputs,
and their callers and test suites match on them. The builder exists to make
those four paths byte-identical; changing the exception type at the same moment
would make the migration observable to every caller and would break the
parity tests that are the only proof the migration was behaviour-preserving.
The ``KeyError`` for a missing conflict key is the same: it is what all four
raise today, and the message format is matched on.

ORDERING IS PART OF THE CONTRACT, not an accident of iteration. Bound columns
keep their ``row`` order and come first; expression columns follow in their
mapping order. Two write paths that ordered them differently would produce
statements that are semantically equal and textually different, and a
differential test that proves they agree would have nothing to compare.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

__all__ = [
    "ALLOWED_WRITE_ATTESTATION_SQL",
    "SQL_EXPRESSION_SENTINEL_PREFIX",
    "WRITE_ATTESTATION_COLUMNS",
    "ModelUpsertPlan",
    "build_upsert_plan",
]

#: Trusted-internal-literal identifier guard. Every table and column name that
#: reaches a plan comes from a hand-written constant or a typed row key, never
#: from user or network input -- validating anyway keeps the composed SQL
#: provably injection-free rather than provably-injection-free-by-convention.
_IDENTIFIER_RE: Final = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

#: The closed set of SQL expressions a write-attestation column may be stamped
#: with. Both members are evaluated by Postgres per row: ``CURRENT_USER`` is
#: the connection's effective principal at the instant of the write, and
#: ``NOW()`` is the writing transaction's timestamp. The set is closed because
#: these strings are composed into the statement uncast.
ALLOWED_WRITE_ATTESTATION_SQL: Final[frozenset[str]] = frozenset(
    {"CURRENT_USER", "NOW()"}
)

#: The two columns migration 0038 added to ``delegation_events`` and the
#: expressions that stamp them, on both arms.
WRITE_ATTESTATION_COLUMNS: Final[Mapping[str, str]] = MappingProxyType(
    {"writer_identity": "CURRENT_USER", "written_at": "NOW()"}
)

#: How the double records a column it cannot evaluate. Unmistakable on a
#: failure, and deliberately NOT a plausible principal name: a double that
#: invented ``"postgres"`` would make every attestation assertion written
#: against it pass while the production statement bound a literal string.
SQL_EXPRESSION_SENTINEL_PREFIX: Final = "<sql:"

Dialect = Literal["pyformat", "qmark_named", "numeric"]


@dataclass(frozen=True, slots=True)
class ModelUpsertPlan:
    """The resolved column layout of one targeted-column UPSERT.

    ``bound_columns`` are the columns a driver must bind a parameter for, in
    bind order. ``insert_columns`` is the INSERT column list -- bound columns
    followed by expression columns. ``update_assignments`` pairs each column on
    the ``DO UPDATE SET`` arm with either ``None`` (assign from ``EXCLUDED``)
    or the SQL expression to re-evaluate.
    """

    table: str
    conflict_keys: list[str]
    bound_columns: list[str]
    expression_columns: Mapping[str, str]
    update_assignments: list[tuple[str, str | None]]
    returning: list[str]

    @property
    def insert_columns(self) -> list[str]:
        return [*self.bound_columns, *self.expression_columns]

    @property
    def is_do_nothing(self) -> bool:
        """True when no column is updatable, so the conflict arm does nothing.

        This is a real outcome, not a degenerate one: a row of nothing but
        conflict keys, or one whose every other column is insert-only, has
        nothing to say about a row that already exists.
        """
        return not self.update_assignments

    def render(
        self,
        *,
        dialect: Dialect,
        jsonb_columns: frozenset[str] = frozenset(),
    ) -> str:
        """Compose the statement for one driver's placeholder style.

        ``jsonb_columns`` applies to the ``numeric`` dialect only, where
        asyncpg does not auto-adapt Python containers the way psycopg2's
        ``Json`` wrapper does, so the placeholder itself carries the cast. The
        other two dialects adapt the VALUE in the adapter and leave the
        placeholder plain, which is why passing the set to them is a caller
        error rather than a silent no-op.
        """
        if jsonb_columns and dialect != "numeric":
            # The four adapters this builder replaces already raise this exact
            # type for this exact input and their callers match on it.
            # error-ok: caller-argument validation at a function boundary
            raise ValueError(
                f"jsonb_columns is meaningful only for the 'numeric' dialect; "
                f"the {dialect!r} dialect adapts the value, not the placeholder"
            )
        placeholders = self._placeholders(dialect, jsonb_columns)
        excluded = "excluded" if dialect == "qmark_named" else "EXCLUDED"
        set_pairs = [
            f"{column} = {excluded}.{column}"
            if expression is None
            else f"{column} = {expression}"
            for column, expression in self.update_assignments
        ]
        action = f"DO UPDATE SET {', '.join(set_pairs)}" if set_pairs else "DO NOTHING"
        # sqlite writes `ON CONFLICT(a, b)`; postgres writes `ON CONFLICT (a, b)`.
        # Preserved per dialect so a rendered statement is byte-identical to what
        # each adapter composed before this module existed.
        conflict = ", ".join(self.conflict_keys)
        conflict_clause = (
            f"ON CONFLICT({conflict})"
            if dialect == "qmark_named"
            else f"ON CONFLICT ({conflict})"
        )
        returning_clause = (
            f" RETURNING {', '.join(self.returning)}" if self.returning else ""
        )
        return (
            f"INSERT INTO {self.table} ({', '.join(self.insert_columns)}) "
            f"VALUES ({', '.join([*placeholders, *self.expression_columns.values()])}) "
            f"{conflict_clause} {action}{returning_clause}"
        )

    def _placeholders(
        self, dialect: Dialect, jsonb_columns: frozenset[str]
    ) -> list[str]:
        if dialect == "pyformat":
            return [f"%({column})s" for column in self.bound_columns]
        if dialect == "qmark_named":
            return [f":{column}" for column in self.bound_columns]
        return [
            f"${index}::jsonb" if column in jsonb_columns else f"${index}"
            for index, column in enumerate(self.bound_columns, start=1)
        ]


def _validate(names: Iterable[str], *, kind: str) -> None:
    for name in names:
        if not _IDENTIFIER_RE.match(name):
            # The four adapters this builder replaces already raise this exact
            # type for this exact input and their callers match on it.
            # error-ok: caller-argument validation at a function boundary
            raise ValueError(f"invalid {kind} identifier: {name!r}")


def build_upsert_plan(
    *,
    table: str,
    conflict_key: str,
    row: Mapping[str, object],
    insert_only_columns: frozenset[str] = frozenset(),
    sql_expression_columns: Mapping[str, str] = MappingProxyType({}),
    returning: Sequence[str] = (),
) -> ModelUpsertPlan:
    """Resolve one targeted-column UPSERT into a :class:`ModelUpsertPlan`.

    Every refusal here is loud and happens before any connection is opened, so
    a rejected write cannot leave a partially applied statement behind.
    """
    conflict_keys = [key.strip() for key in conflict_key.split(",") if key.strip()]
    if not conflict_keys:
        # The four adapters this builder replaces already raise this exact
        # type for this exact input and their callers match on it.
        # error-ok: caller-argument validation at a function boundary
        raise ValueError("conflict_key must contain at least one key")
    missing = [key for key in conflict_keys if key not in row]
    if missing:
        # The four adapters this builder replaces already raise this exact
        # type for this exact input and their callers match on it.
        # error-ok: caller-argument validation at a function boundary
        raise KeyError(f"row missing conflict key(s): {missing}")

    # An attestation column may not also be a bound value. If a caller put one
    # on the row dict it would win the placeholder slot and the expression
    # would never be evaluated -- the column would silently go back to
    # recording whatever the writing process said.
    overlapping = sorted(set(sql_expression_columns) & set(row))
    if overlapping:
        # The four adapters this builder replaces already raise this exact
        # type for this exact input and their callers match on it.
        # error-ok: caller-argument validation at a function boundary
        raise ValueError(
            f"columns {overlapping!r} are declared as SQL expressions and must "
            "not also be supplied as row values: a bound parameter would "
            "override the expression and the column would attest to the caller "
            "rather than to the database"
        )
    for column, expression in sql_expression_columns.items():
        if expression not in ALLOWED_WRITE_ATTESTATION_SQL:
            # The four adapters this builder replaces already raise this exact
            # type for this exact input and their callers match on it.
            # error-ok: caller-argument validation at a function boundary
            raise ValueError(
                f"SQL expression {expression!r} for column {column!r} is not in "
                "the allowed write-attestation set "
                f"{sorted(ALLOWED_WRITE_ATTESTATION_SQL)!r}"
            )

    # The KIND is carried into the message on purpose. "invalid identifier
    # 'timestamp '" does not say whether the caller mistyped a row key, a
    # conflict key or a RETURNING column, and those are three different bugs
    # in three different call sites.
    bound_columns = list(row)
    _validate((table,), kind="table")
    _validate(bound_columns, kind="column")
    _validate(conflict_keys, kind="conflict-key")
    _validate(sql_expression_columns, kind="expression-column")
    _validate(returning, kind="returning-column")

    update_assignments: list[tuple[str, str | None]] = [
        (column, None)
        for column in bound_columns
        if column not in conflict_keys and column not in insert_only_columns
    ]
    update_assignments.extend(sql_expression_columns.items())

    return ModelUpsertPlan(
        table=table,
        conflict_keys=conflict_keys,
        bound_columns=bound_columns,
        expression_columns=MappingProxyType(dict(sql_expression_columns)),
        update_assignments=update_assignments,
        returning=list(returning),
    )
