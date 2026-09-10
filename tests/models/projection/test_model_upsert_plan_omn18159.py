# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-18159: the shared targeted-column UPSERT plan.

This module is the single home of the decisions four write paths across this
workspace had already drifted on. The tests below therefore assert the
DECISIONS -- arm placement, the closed admissible-expression set, identifier
validation, bind ordering -- and the exact rendered text for each driver
dialect, because two adapters that render the same plan differently are the
drift this module exists to remove.

The rendered-statement assertions are deliberately byte-exact rather than
structural. A structural assertion ("the update arm mentions writer_identity")
passes for a statement that assigns it from ``EXCLUDED`` instead of
re-evaluating the expression, and those two differ only when a second writer
touches the row -- which is exactly the case the attestation exists to
distinguish.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from omnibase_core.models.projection import (
    ALLOWED_WRITE_ATTESTATION_SQL,
    WRITE_ATTESTATION_COLUMNS,
    build_upsert_plan,
)

pytestmark = pytest.mark.unit


class TestArmPlacement:
    def test_every_non_conflict_column_is_on_the_update_arm(self) -> None:
        plan = build_upsert_plan(
            table="delegation_events",
            conflict_key="correlation_id",
            row={"correlation_id": "c1", "task_type": "t", "delegated_to": "d"},
        )
        assert plan.conflict_keys == ["correlation_id"]
        assert plan.insert_columns == ["correlation_id", "task_type", "delegated_to"]
        assert plan.update_assignments == [("task_type", None), ("delegated_to", None)]
        assert plan.bound_columns == ["correlation_id", "task_type", "delegated_to"]

    def test_a_row_of_only_conflict_keys_takes_the_do_nothing_arm(self) -> None:
        plan = build_upsert_plan(
            table="t", conflict_key="correlation_id", row={"correlation_id": "c1"}
        )
        assert plan.update_assignments == []
        assert plan.is_do_nothing is True

    def test_composite_conflict_keys_split_and_strip(self) -> None:
        plan = build_upsert_plan(
            table="delegation_budget_state",
            conflict_key="tenant_id, cost_tier_name ,budget_period",
            row={
                "tenant_id": "x",
                "cost_tier_name": "y",
                "budget_period": "z",
                "delegation_count": 1,
            },
        )
        assert plan.conflict_keys == ["tenant_id", "cost_tier_name", "budget_period"]
        assert plan.update_assignments == [("delegation_count", None)]

    def test_insert_only_columns_are_on_insert_and_off_update(self) -> None:
        """Both halves are load-bearing under row-level security.

        The INSERT half is the non-obvious one: Postgres checks the policy
        against the PROPOSED row before resolving the conflict, so dropping
        ``tenant_id`` from the column list entirely is refused outright even
        for a statement that would only ever take the update arm.
        """
        plan = build_upsert_plan(
            table="delegation_events",
            conflict_key="correlation_id",
            row={
                "correlation_id": "c1",
                "tenant_id": "t",
                "timestamp": "ts",
                "quality_gate_passed": True,
            },
            insert_only_columns=frozenset({"tenant_id", "timestamp"}),
        )
        assert "tenant_id" in plan.insert_columns
        assert "timestamp" in plan.insert_columns
        assert plan.update_assignments == [("quality_gate_passed", None)]

    def test_a_row_whose_every_updatable_column_is_insert_only_does_nothing(
        self,
    ) -> None:
        plan = build_upsert_plan(
            table="delegation_events",
            conflict_key="correlation_id",
            row={"correlation_id": "c1", "tenant_id": "t"},
            insert_only_columns=frozenset({"tenant_id"}),
        )
        assert plan.is_do_nothing is True
        assert "tenant_id" in plan.insert_columns


class TestExpressionColumns:
    def test_expressions_are_on_both_arms_and_bind_nothing(self) -> None:
        plan = build_upsert_plan(
            table="delegation_events",
            conflict_key="correlation_id",
            row={"correlation_id": "c1", "task_type": "t"},
            sql_expression_columns=WRITE_ATTESTATION_COLUMNS,
        )
        assert plan.insert_columns == [
            "correlation_id",
            "task_type",
            "writer_identity",
            "written_at",
        ]
        assert plan.bound_columns == ["correlation_id", "task_type"]
        assert plan.update_assignments == [
            ("task_type", None),
            ("writer_identity", "CURRENT_USER"),
            ("written_at", "NOW()"),
        ]

    def test_a_column_bound_and_expressed_at_once_is_refused(self) -> None:
        """The refusal that makes the attestation mean anything.

        A bound value would win the placeholder slot and the expression would
        never be evaluated, so the column would silently go back to recording
        whatever the writing process said.
        """
        with pytest.raises(ValueError, match="must not also be supplied as row values"):
            build_upsert_plan(
                table="delegation_events",
                conflict_key="correlation_id",
                row={"correlation_id": "c1", "writer_identity": "i_said_so"},
                sql_expression_columns=WRITE_ATTESTATION_COLUMNS,
            )

    @pytest.mark.parametrize(
        "expression",
        ["(SELECT 1)", "version()", "current_user", "NOW ()", "CURRENT_USER;--"],
    )
    def test_an_expression_outside_the_closed_set_is_refused(
        self, expression: str
    ) -> None:
        """The set is closed because these strings reach the statement uncast.

        ``current_user`` lowercase and ``NOW ()`` with a space are included
        deliberately: they are semantically identical to admissible members,
        and admitting them by normalising would turn a closed set into a
        parser.
        """
        with pytest.raises(ValueError, match="not in the allowed write-attestation"):
            build_upsert_plan(
                table="delegation_events",
                conflict_key="correlation_id",
                row={"correlation_id": "c1"},
                sql_expression_columns=MappingProxyType(
                    {"writer_identity": expression}
                ),
            )

    def test_the_closed_set_holds_exactly_two_members(self) -> None:
        assert frozenset({"CURRENT_USER", "NOW()"}) == ALLOWED_WRITE_ATTESTATION_SQL
        assert dict(WRITE_ATTESTATION_COLUMNS) == {
            "writer_identity": "CURRENT_USER",
            "written_at": "NOW()",
        }


class TestIdentifierValidation:
    @pytest.mark.parametrize(
        "bad", ["delegation events", "drop;table", "1_leading_digit", "", "a-b", "a.b"]
    )
    def test_the_message_names_which_position_the_bad_identifier_came_from(
        self, bad: str
    ) -> None:
        """A mistyped row key, table and RETURNING column are three bugs.

        A single generic message forces the reader back to the call site to
        work out which of the three they have.
        """
        with pytest.raises(ValueError, match="invalid column identifier"):
            build_upsert_plan(
                table="delegation_events",
                conflict_key="correlation_id",
                row={"correlation_id": "c1", bad: "v"},
            )
        with pytest.raises(ValueError, match="invalid table identifier"):
            build_upsert_plan(
                table=bad, conflict_key="correlation_id", row={"correlation_id": "c1"}
            )
        with pytest.raises(ValueError, match="invalid returning-column identifier"):
            build_upsert_plan(
                table="delegation_events",
                conflict_key="correlation_id",
                row={"correlation_id": "c1"},
                returning=(bad,),
            )

    def test_an_empty_conflict_key_is_refused(self) -> None:
        with pytest.raises(ValueError, match="at least one key"):
            build_upsert_plan(table="t", conflict_key="  ,  ", row={"a": 1})

    def test_a_row_missing_a_conflict_key_is_refused(self) -> None:
        with pytest.raises(KeyError, match="missing conflict key"):
            build_upsert_plan(table="t", conflict_key="correlation_id", row={"a": 1})


class TestRendering:
    def test_pyformat_dialect(self) -> None:
        plan = build_upsert_plan(
            table="delegation_events",
            conflict_key="correlation_id",
            row={"correlation_id": "c1", "task_type": "t"},
            sql_expression_columns=WRITE_ATTESTATION_COLUMNS,
            returning=("correlation_id", "writer_identity"),
        )
        assert plan.render(dialect="pyformat") == (
            "INSERT INTO delegation_events "
            "(correlation_id, task_type, writer_identity, written_at) "
            "VALUES (%(correlation_id)s, %(task_type)s, CURRENT_USER, NOW()) "
            "ON CONFLICT (correlation_id) DO UPDATE SET "
            "task_type = EXCLUDED.task_type, "
            "writer_identity = CURRENT_USER, written_at = NOW() "
            "RETURNING correlation_id, writer_identity"
        )

    def test_qmark_named_dialect_uses_lowercase_excluded_and_tight_conflict(
        self,
    ) -> None:
        """SQLite spells both differently, and the difference is not cosmetic.

        Reproducing each driver's own spelling is what lets an adapter adopt
        this builder without changing a single byte of the statement it
        already issues, so the migration is provably behaviour-preserving.
        """
        plan = build_upsert_plan(
            table="delegation_events",
            conflict_key="correlation_id",
            row={"correlation_id": "c1", "task_type": "t"},
        )
        assert plan.render(dialect="qmark_named") == (
            "INSERT INTO delegation_events (correlation_id, task_type) "
            "VALUES (:correlation_id, :task_type) "
            "ON CONFLICT(correlation_id) DO UPDATE SET "
            "task_type = excluded.task_type"
        )

    def test_numeric_dialect_numbers_placeholders_in_bind_order(self) -> None:
        plan = build_upsert_plan(
            table="delegation_events",
            conflict_key="correlation_id",
            row={"correlation_id": "c1", "gates": ["a"], "task_type": "t"},
            sql_expression_columns=WRITE_ATTESTATION_COLUMNS,
        )
        assert plan.render(dialect="numeric", jsonb_columns=frozenset({"gates"})) == (
            "INSERT INTO delegation_events "
            "(correlation_id, gates, task_type, writer_identity, written_at) "
            "VALUES ($1, $2::jsonb, $3, CURRENT_USER, NOW()) "
            "ON CONFLICT (correlation_id) DO UPDATE SET "
            "gates = EXCLUDED.gates, task_type = EXCLUDED.task_type, "
            "writer_identity = CURRENT_USER, written_at = NOW()"
        )

    def test_do_nothing_renders_without_a_set_clause(self) -> None:
        plan = build_upsert_plan(
            table="t", conflict_key="correlation_id", row={"correlation_id": "c1"}
        )
        assert plan.render(dialect="pyformat").endswith(
            "ON CONFLICT (correlation_id) DO NOTHING"
        )

    def test_jsonb_columns_on_a_value_adapting_dialect_is_a_caller_error(self) -> None:
        """Silently ignoring it would hide a real mistake.

        Only the numeric dialect carries the cast on the placeholder; the
        other two adapt the VALUE inside the adapter. A caller passing the set
        to those has misunderstood which side does the work, and a no-op would
        let that misunderstanding ship.
        """
        plan = build_upsert_plan(
            table="t", conflict_key="k", row={"k": "1", "gates": ["a"]}
        )
        for dialect in ("pyformat", "qmark_named"):
            with pytest.raises(ValueError, match="only for the 'numeric' dialect"):
                plan.render(
                    dialect=dialect,  # type: ignore[arg-type]
                    jsonb_columns=frozenset({"gates"}),
                )

    def test_bind_order_follows_row_order_not_sorted_order(self) -> None:
        """Ordering is part of the contract, not an accident of iteration.

        Two write paths that ordered columns differently would render
        statements that are semantically equal and textually different, and a
        differential test proving they agree would have nothing to compare.
        """
        plan = build_upsert_plan(
            table="t",
            conflict_key="k",
            row={"k": "1", "zeta": 1, "alpha": 2},
        )
        assert plan.bound_columns == ["k", "zeta", "alpha"]
        assert plan.render(dialect="numeric").startswith(
            "INSERT INTO t (k, zeta, alpha) VALUES ($1, $2, $3)"
        )


class TestPlanIsInert:
    def test_the_plan_carries_no_values_only_column_names(self) -> None:
        """The plan is a statement shape, never a row of data.

        Keeping values out of it is what lets it be built, logged and compared
        without ever handling a tenant identifier or a secret.
        """
        plan = build_upsert_plan(
            table="t", conflict_key="k", row={"k": "sensitive", "v": "also-sensitive"}
        )
        rendered = repr(plan) + plan.render(dialect="pyformat")
        assert "sensitive" not in rendered
