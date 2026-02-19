# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for DB repository contract validators.

This module tests all five DB repository validators:
- validate_db_structural: Required fields, valid identifiers
- validate_db_sql_safety: read->SELECT, forbid DDL, multi-statement, safety policy
- validate_db_table_access: Tables in SQL <= declared tables
- validate_db_deterministic: many=True -> ORDER BY required
- validate_db_params: Named params validation

Each validator has:
1. A golden contract test showing it passes
2. One or more failure cases showing it correctly rejects invalid contracts
"""

import pytest

from omnibase_core.enums.enum_database_engine import EnumDatabaseEngine
from omnibase_core.enums.enum_parameter_type import EnumParameterType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_db_operation import ModelDbOperation
from omnibase_core.models.contracts.model_db_param import ModelDbParam
from omnibase_core.models.contracts.model_db_repository_contract import (
    ModelDbRepositoryContract,
)
from omnibase_core.models.contracts.model_db_return import ModelDbReturn
from omnibase_core.models.contracts.model_db_safety_policy import ModelDbSafetyPolicy
from omnibase_core.validation.db import (
    validate_db_deterministic,
    validate_db_params,
    validate_db_projection,
    validate_db_sql_safety,
    validate_db_structural,
    validate_db_table_access,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def golden_contract() -> ModelDbRepositoryContract:
    """A contract that passes ALL validators - the reference implementation.

    This contract demonstrates:
    - Valid table and operation names (SQL identifiers)
    - Single-statement SQL (no semicolons)
    - Read mode uses SELECT, write mode uses INSERT
    - No DDL keywords
    - Only accesses declared tables
    - many=True queries have ORDER BY
    - LIMIT queries have ORDER BY
    - Only named parameters (:param)
    - All SQL params declared, all declared params used
    """
    return ModelDbRepositoryContract(
        name="learned_patterns_repository",
        engine=EnumDatabaseEngine.POSTGRES,
        database_ref="omninode_bridge",
        tables=["learned_patterns"],
        models={"PatternRow": "omnibase_spi.models:ModelCompiledPattern"},
        ops={
            "list_validated_patterns": ModelDbOperation(
                mode="read",
                sql="""
                    SELECT pattern_id, domain, compiled_snippet, quality_score
                    FROM learned_patterns
                    WHERE status = 'validated'
                    ORDER BY quality_score DESC, pattern_id ASC
                    LIMIT :limit
                """,
                params={
                    "limit": ModelDbParam(
                        name="limit",
                        param_type=EnumParameterType.INTEGER,
                        required=False,
                        default=ModelSchemaValue.create_number(200),
                        ge=1,
                        le=5000,
                        description="Maximum number of patterns to return",
                    ),
                },
                returns=ModelDbReturn(model_ref="PatternRow", many=True),
            ),
            "insert_pattern": ModelDbOperation(
                mode="write",
                sql="""
                    INSERT INTO learned_patterns (pattern_id, domain, compiled_snippet, status)
                    VALUES (:pattern_id, :domain, :snippet, :status)
                """,
                params={
                    "pattern_id": ModelDbParam(
                        name="pattern_id", param_type=EnumParameterType.STRING
                    ),
                    "domain": ModelDbParam(
                        name="domain", param_type=EnumParameterType.STRING
                    ),
                    "snippet": ModelDbParam(
                        name="snippet", param_type=EnumParameterType.STRING
                    ),
                    "status": ModelDbParam(
                        name="status", param_type=EnumParameterType.STRING
                    ),
                },
                returns=ModelDbReturn(model_ref="PatternRow", many=False),
            ),
        },
    )


# ============================================================================
# Golden Contract - All Validators Pass
# ============================================================================


@pytest.mark.unit
class TestGoldenContract:
    """Test that the golden contract passes all validators."""

    def test_structural_passes(
        self, golden_contract: ModelDbRepositoryContract
    ) -> None:
        """Golden contract passes structural validation."""
        result = validate_db_structural(golden_contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_sql_safety_passes(
        self, golden_contract: ModelDbRepositoryContract
    ) -> None:
        """Golden contract passes SQL safety validation."""
        result = validate_db_sql_safety(golden_contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_table_access_passes(
        self, golden_contract: ModelDbRepositoryContract
    ) -> None:
        """Golden contract passes table access validation."""
        result = validate_db_table_access(golden_contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_deterministic_passes(
        self, golden_contract: ModelDbRepositoryContract
    ) -> None:
        """Golden contract passes deterministic ordering validation."""
        result = validate_db_deterministic(golden_contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_params_passes(self, golden_contract: ModelDbRepositoryContract) -> None:
        """Golden contract passes parameter validation."""
        result = validate_db_params(golden_contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"


# ============================================================================
# Validator-Specific Failure Cases
# ============================================================================


@pytest.mark.unit
class TestValidatorDbStructural:
    """Test structural validator failure cases."""

    def test_invalid_table_name_starts_with_number(self) -> None:
        """Table names must be valid SQL identifiers (start with letter)."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["123invalid"],  # Invalid: starts with number
            models={},
            ops={
                "op1": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_structural(contract)
        assert not result.is_valid
        assert any("123invalid" in str(e) for e in result.errors)

    def test_invalid_table_name_special_chars(self) -> None:
        """Table names cannot contain special characters."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["my-table"],  # Invalid: contains hyphen
            models={},
            ops={
                "op1": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_structural(contract)
        assert not result.is_valid
        assert any("my-table" in str(e) for e in result.errors)

    def test_invalid_operation_name(self) -> None:
        """Operation names must be valid identifiers."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "123bad_op": ModelDbOperation(  # Invalid: starts with number
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_structural(contract)
        assert not result.is_valid
        assert any("123bad_op" in str(e) for e in result.errors)

    def test_schema_qualified_table_names_valid(self) -> None:
        """Schema-qualified table names (e.g., public.users) are valid."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["public.users", "schema_name.table_name", "simple_table"],
            models={},
            ops={
                "op1": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM public.users ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_structural(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_invalid_table_name_starts_with_dot(self) -> None:
        """Table names starting with dot are invalid."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=[".users"],  # Invalid: starts with dot
            models={},
            ops={
                "op1": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_structural(contract)
        assert not result.is_valid
        assert any(".users" in str(e) for e in result.errors)

    def test_invalid_table_name_ends_with_dot(self) -> None:
        """Table names ending with dot are invalid."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users."],  # Invalid: ends with dot
            models={},
            ops={
                "op1": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_structural(contract)
        assert not result.is_valid
        assert any("users." in str(e) for e in result.errors)

    def test_invalid_table_name_multiple_dots(self) -> None:
        """Table names with more than one dot are invalid."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["a.b.c"],  # Invalid: more than one dot
            models={},
            ops={
                "op1": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_structural(contract)
        assert not result.is_valid
        assert any("a.b.c" in str(e) for e in result.errors)


@pytest.mark.unit
class TestValidatorDbSqlSafety:
    """Test SQL safety validator failure cases."""

    def test_read_mode_with_insert(self) -> None:
        """Read mode must use SELECT."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "bad_read": ModelDbOperation(
                    mode="read",
                    sql="INSERT INTO test VALUES (1)",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any("read mode requires SELECT" in str(e) for e in result.errors)

    def test_write_mode_with_select(self) -> None:
        """Write mode must use INSERT/UPDATE/DELETE."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "bad_write": ModelDbOperation(
                    mode="write",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any(
            "write mode requires INSERT" in str(e)
            or "UPDATE" in str(e)
            or "DELETE" in str(e)
            for e in result.errors
        )

    def test_ddl_keyword_drop_blocked(self) -> None:
        """DROP keyword is forbidden."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "dangerous": ModelDbOperation(
                    mode="write",
                    sql="DROP TABLE test",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any("DROP" in str(e) for e in result.errors)

    def test_ddl_keyword_alter_blocked(self) -> None:
        """ALTER keyword is forbidden."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "dangerous": ModelDbOperation(
                    mode="write",
                    sql="ALTER TABLE test ADD COLUMN foo TEXT",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any("ALTER" in str(e) for e in result.errors)

    def test_ddl_keyword_truncate_blocked(self) -> None:
        """TRUNCATE keyword is forbidden."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "dangerous": ModelDbOperation(
                    mode="write",
                    sql="TRUNCATE TABLE test",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any("TRUNCATE" in str(e) for e in result.errors)

    def test_delete_without_where(self) -> None:
        """DELETE without WHERE requires opt-in."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "delete_all": ModelDbOperation(
                    mode="write",
                    sql="DELETE FROM test",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any("DELETE without WHERE" in str(e) for e in result.errors)

    def test_delete_without_where_with_policy_passes(self) -> None:
        """DELETE without WHERE passes with safety policy opt-in."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "delete_all": ModelDbOperation(
                    mode="write",
                    sql="DELETE FROM test",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                    safety_policy=ModelDbSafetyPolicy(allow_delete_without_where=True),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert result.is_valid, f"Expected valid with policy, got: {result.errors}"

    def test_update_without_where(self) -> None:
        """UPDATE without WHERE requires opt-in."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "update_all": ModelDbOperation(
                    mode="write",
                    sql="UPDATE test SET status = 'archived'",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any("UPDATE without WHERE" in str(e) for e in result.errors)

    def test_update_without_where_with_policy_passes(self) -> None:
        """UPDATE without WHERE passes with safety policy opt-in."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "update_all": ModelDbOperation(
                    mode="write",
                    sql="UPDATE test SET status = 'archived'",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                    safety_policy=ModelDbSafetyPolicy(allow_update_without_where=True),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert result.is_valid, f"Expected valid with policy, got: {result.errors}"

    def test_multi_statement_without_policy(self) -> None:
        """Multi-statement SQL requires safety policy opt-in."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "op1": ModelDbOperation(
                    mode="write",
                    sql="INSERT INTO test VALUES (1); DELETE FROM test WHERE id = 1",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any("multiple statements" in str(e).lower() for e in result.errors)

    def test_multi_statement_with_policy_passes(self) -> None:
        """Multi-statement SQL passes with safety policy opt-in."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "op1": ModelDbOperation(
                    mode="write",
                    sql="INSERT INTO test VALUES (1); DELETE FROM test WHERE id = 1",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                    safety_policy=ModelDbSafetyPolicy(allow_multi_statement=True),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert result.is_valid, f"Expected valid with policy, got: {result.errors}"

    def test_single_statement_with_trailing_semicolon_passes(self) -> None:
        """Single statement with trailing semicolon should pass validation.

        A trailing semicolon is valid SQL syntax and should not be flagged
        as multi-statement. Only semicolons BETWEEN statements indicate
        multiple statements.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "select_with_semicolon": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id;",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_insert_with_trailing_semicolon_passes(self) -> None:
        """INSERT with trailing semicolon should pass validation."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "insert_with_semicolon": ModelDbOperation(
                    mode="write",
                    sql="INSERT INTO test VALUES (1);",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_trailing_semicolon_with_whitespace_passes(self) -> None:
        """Trailing semicolon followed by whitespace should pass."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "select_semicolon_whitespace": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id;   \n",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_actual_multi_statement_still_fails(self) -> None:
        """Actual multi-statement SQL (semicolon between statements) still fails."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "multi_stmt": ModelDbOperation(
                    mode="read",
                    sql="SELECT 1; SELECT 2",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any("multiple statements" in str(e).lower() for e in result.errors)


@pytest.mark.unit
class TestValidatorDbTableAccess:
    """Test table access validator failure cases."""

    def test_undeclared_table(self) -> None:
        """SQL can only access declared tables."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["allowed_table"],
            models={},
            ops={
                "sneaky": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM secret_table ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert not result.is_valid
        assert any("secret_table" in str(e) for e in result.errors)

    def test_undeclared_table_in_join(self) -> None:
        """Join targets must also be declared tables."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],  # users declared, but not orders
            models={},
            ops={
                "join_query": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT u.name, o.total
                        FROM users u
                        JOIN orders o ON u.id = o.user_id
                        ORDER BY u.name
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert not result.is_valid
        assert any("orders" in str(e).lower() for e in result.errors)

    def test_cte_with_valid_tables_passes(self) -> None:
        """CTEs with valid tables pass validation when parser is available.

        In v2 (OMN-1791), CTEs are supported via sqlglot parser. The CTE body
        tables are validated against the allowed list.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "with_cte": ModelDbOperation(
                    mode="read",
                    sql="WITH cte AS (SELECT * FROM test) SELECT * FROM cte ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # With parser available (dev dependency), this passes
        # 'cte' is filtered as CTE alias, 'test' is in allowed list
        assert result.is_valid, f"CTE with valid table should pass: {result.errors}"

    def test_subquery_with_valid_tables_passes(self) -> None:
        """Subqueries with valid tables pass validation when parser is available.

        In v2 (OMN-1791), subqueries are supported via sqlglot parser. The
        subquery body tables are validated against the allowed list.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "with_subquery": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM (SELECT * FROM test) sub ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # With parser available (dev dependency), this passes
        # 'sub' is filtered as subquery alias, 'test' is in allowed list
        assert result.is_valid, (
            f"Subquery with valid table should pass: {result.errors}"
        )

    def test_multiple_declared_tables_pass(self) -> None:
        """Multiple tables can be declared and accessed."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users", "orders"],  # Both declared
            models={},
            ops={
                "join_query": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT u.name, o.total
                        FROM users u
                        JOIN orders o ON u.id = o.user_id
                        ORDER BY u.name
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    # ============================================================================
    # Schema-qualified table tests (Issue: schema bypass prevention)
    # ============================================================================

    def test_schema_qualified_allowlist_requires_exact_match(self) -> None:
        """Schema-qualified allowlist entry requires exact schema match.

        If tables: ["public.users"] is declared, only "public.users" should be allowed,
        not "other_schema.users" or just "users".
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["public.users"],  # Schema-qualified allowlist entry
            models={},
            ops={
                "wrong_schema": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM other_schema.users ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert not result.is_valid
        assert any("other_schema.users" in str(e) for e in result.errors)

    def test_schema_qualified_allowlist_exact_match_passes(self) -> None:
        """Schema-qualified allowlist entry with exact match passes."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["public.users"],  # Schema-qualified allowlist entry
            models={},
            ops={
                "correct_schema": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM public.users ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_simple_allowlist_accepts_any_schema(self) -> None:
        """Simple allowlist entry accepts any schema prefix.

        If tables: ["users"] is declared, then "public.users", "myschema.users",
        and "users" should all be allowed.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],  # Simple allowlist entry
            models={},
            ops={
                "public_schema": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM public.users ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
                "custom_schema": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM myschema.users ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
                "no_schema": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM users ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_schema_bypass_blocked(self) -> None:
        """Schema-qualified access to undeclared table is blocked.

        Prevents bypass where "public.secret_table" might evade check for "secret_table".
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["allowed_table"],
            models={},
            ops={
                "schema_bypass_attempt": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM public.secret_table ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert not result.is_valid
        assert any("public.secret_table" in str(e) for e in result.errors)

    # ============================================================================
    # Quoted identifier tests (Issue: quoted identifier evasion)
    # ============================================================================

    def test_quoted_table_extracted(self) -> None:
        """Quoted table identifiers are extracted and validated.

        SQL allows quoted identifiers like FROM "TableName" for case-sensitive names.
        These must be validated, not stripped and ignored.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["allowed_table"],
            models={},
            ops={
                "quoted_table": ModelDbOperation(
                    mode="read",
                    sql='SELECT * FROM "secret_table" ORDER BY id',
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert not result.is_valid
        assert any("secret_table" in str(e) for e in result.errors)

    def test_quoted_table_allowed_passes(self) -> None:
        """Quoted table that matches allowlist passes validation."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["MyTable"],  # Case-sensitive name
            models={},
            ops={
                "quoted_allowed": ModelDbOperation(
                    mode="read",
                    sql='SELECT * FROM "MyTable" ORDER BY id',
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_quoted_schema_qualified_table(self) -> None:
        """Quoted schema-qualified tables are extracted correctly."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["public.MyTable"],  # Schema-qualified
            models={},
            ops={
                "quoted_schema_table": ModelDbOperation(
                    mode="read",
                    sql='SELECT * FROM "public"."MyTable" ORDER BY id',
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_quoted_identifier_in_join(self) -> None:
        """Quoted identifiers in JOIN clauses are validated."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],  # Only users declared
            models={},
            ops={
                "quoted_join": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT u.name
                        FROM users u
                        JOIN "SecretOrders" o ON u.id = o.user_id
                        ORDER BY u.name
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert not result.is_valid
        assert any("SecretOrders" in str(e) for e in result.errors)

    def test_mixed_quoted_and_unquoted_tables(self) -> None:
        """Both quoted and unquoted tables in same query are validated."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users", "Orders"],  # Both declared
            models={},
            ops={
                "mixed_query": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT u.name, o.total
                        FROM users u
                        JOIN "Orders" o ON u.id = o.user_id
                        ORDER BY u.name
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_self_join_same_table_twice(self) -> None:
        """Self-join (same table with different aliases) should pass validation."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],
            models={},
            ops={
                "get_with_manager": ModelDbOperation(
                    mode="read",
                    sql="SELECT a.id, b.name FROM users a JOIN users b ON a.manager_id = b.id ORDER BY a.id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Self-join should pass. Errors: {result.errors}"

    def test_table_alias_not_flagged_as_table(self) -> None:
        """Table aliases should not be flagged as undeclared tables.

        SQL table aliases (e.g., `FROM patterns p`) should be correctly ignored
        by the table extraction logic. Only the actual table name should be
        extracted, not the alias that follows it.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["patterns"],
            models={},
            ops={
                "list_patterns": ModelDbOperation(
                    mode="read",
                    sql="SELECT p.id, p.name FROM patterns p WHERE p.active = true ORDER BY p.id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, (
            f"Alias 'p' should not be flagged. Errors: {result.errors}"
        )


@pytest.mark.unit
class TestValidatorDbDeterministic:
    """Test deterministic ordering validator failure cases."""

    def test_many_without_order_by(self) -> None:
        """many=True requires ORDER BY."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "non_deterministic": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        assert not result.is_valid
        assert any("ORDER BY" in str(e) for e in result.errors)

    def test_limit_without_order_by(self) -> None:
        """LIMIT requires ORDER BY."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "paginated": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test LIMIT 10",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        assert not result.is_valid
        assert any("LIMIT" in str(e) or "ORDER BY" in str(e) for e in result.errors)

    def test_offset_without_order_by(self) -> None:
        """OFFSET requires ORDER BY."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "paginated": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test LIMIT 10 OFFSET 20",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        assert not result.is_valid
        assert any("ORDER BY" in str(e) for e in result.errors)

    def test_many_false_without_order_by_passes(self) -> None:
        """many=False without ORDER BY passes (single row expected)."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "single_row": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = :id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                    },
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_write_operation_skipped(self) -> None:
        """Write operations (INSERT/UPDATE/DELETE) are not checked for ORDER BY."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "insert_op": ModelDbOperation(
                    mode="write",
                    sql="INSERT INTO test (name) VALUES (:name)",
                    params={
                        "name": ModelDbParam(
                            name="name", param_type=EnumParameterType.STRING
                        ),
                    },
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        assert result.is_valid, f"Expected valid for write op, got: {result.errors}"

    def test_order_by_in_string_literal_ignored(self) -> None:
        """ORDER BY inside string literal should be ignored; real ORDER BY detected.

        This test covers the PR #463 review feedback: escaped quotes in string
        literals should not cause false ORDER BY detection.

        The SQL has 'ORDER BY' in a string AND a real ORDER BY clause.
        Only the real ORDER BY should be detected.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "with_keyword_in_string": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE name = 'ORDER BY' ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        # Should pass because real ORDER BY exists outside the string
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_limit_in_string_real_limit_requires_order_by(self) -> None:
        """LIMIT inside string should be ignored; real LIMIT needs ORDER BY.

        Only the real LIMIT should be detected, and it requires ORDER BY.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "limit_in_string": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE msg = 'LIMIT 10' LIMIT 10",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        # Should fail: real LIMIT exists but no ORDER BY
        assert not result.is_valid
        assert any("LIMIT" in str(e) or "ORDER BY" in str(e) for e in result.errors)

    def test_order_by_in_backslash_escaped_string_ignored(self) -> None:
        """ORDER BY in backslash-escaped string should be ignored.

        Tests that backslash escape convention (It's -> It\\'s) doesn't break
        string stripping and cause false ORDER BY detection.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "escaped_string": ModelDbOperation(
                    mode="read",
                    sql=r"SELECT * FROM test WHERE name = 'It\'s ORDER BY test' ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        # Should pass: real ORDER BY exists after the escaped string
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_order_by_in_doubled_quote_string_ignored(self) -> None:
        """ORDER BY in SQL-standard doubled-quote string should be ignored.

        Tests that doubled quote escape convention (It's -> It''s) doesn't break
        string stripping and cause false ORDER BY detection.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "doubled_quote_string": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE name = 'It''s ORDER BY test' ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        # Should pass: real ORDER BY exists after the doubled-quote string
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_only_order_by_in_string_fails(self) -> None:
        """If ORDER BY only exists inside string literal, validation should fail.

        The query has ORDER BY in a string but no real ORDER BY clause.
        With many=True, this should fail validation.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "fake_order_by": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE msg = 'ORDER BY id'",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        # Should fail: no real ORDER BY, only one inside string
        assert not result.is_valid
        assert any("ORDER BY" in str(e) for e in result.errors)


@pytest.mark.unit
class TestValidatorDbParams:
    """Test parameter validator failure cases."""

    def test_positional_params_rejected_without_param_order(self) -> None:
        """Positional parameters ($1, $2) without param_order are rejected with helpful hint."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "positional": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = $1 ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                    },
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        # Error should mention param_order as a solution
        assert any("param_order" in str(e) for e in result.errors)
        assert any("$1" in str(e) for e in result.errors)

    def test_undefined_param(self) -> None:
        """All :params in SQL must be declared."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "missing_param": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = :id AND name = :name ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        # 'name' param is missing!
                    },
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        assert any("name" in str(e) or "Undefined" in str(e) for e in result.errors)

    def test_unused_param(self) -> None:
        """All declared params must be used in SQL."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "extra_param": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = :id ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        "unused": ModelDbParam(
                            name="unused", param_type=EnumParameterType.STRING
                        ),
                    },
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        assert any("unused" in str(e).lower() for e in result.errors)

    def test_multiple_positional_params_without_param_order(self) -> None:
        """Multiple positional params without param_order are rejected."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "multi_positional": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = $1 AND name = $2 ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        "name": ModelDbParam(
                            name="name", param_type=EnumParameterType.STRING
                        ),
                    },
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        # Should mention both $1 and $2 and suggest param_order
        assert any("$1" in str(e) for e in result.errors)
        assert any("$2" in str(e) for e in result.errors)
        assert any("param_order" in str(e) for e in result.errors)

    def test_empty_params_with_no_placeholders_passes(self) -> None:
        """No params required if SQL has no placeholders."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "no_params": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_type_cast_not_treated_as_param(self) -> None:
        """PostgreSQL type casts (::type) should not be detected as parameters."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "with_cast": ModelDbOperation(
                    mode="read",
                    sql="SELECT id::text, value::integer FROM test WHERE id = :id ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                    },
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        # Should pass - ::text and ::integer are type casts, not parameters
        # Only :id should be detected as a parameter
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"


# ============================================================================
# Positional Parameters with param_order
# ============================================================================


@pytest.mark.unit
class TestPositionalParamsWithParamOrder:
    """Test positional parameter support with param_order field."""

    def test_valid_positional_params_with_param_order(self) -> None:
        """Positional parameters with valid param_order should pass validation."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "positional_valid": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = $1 AND name = $2 ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        "name": ModelDbParam(
                            name="name", param_type=EnumParameterType.STRING
                        ),
                    },
                    param_order=("id", "name"),
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_single_positional_param_with_param_order(self) -> None:
        """Single positional parameter with param_order should pass."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "single_positional": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = $1 ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                    },
                    param_order=("id",),
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_index_gap_rejected(self) -> None:
        """Positional indices must be contiguous (no gaps)."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "gap_indices": ModelDbOperation(
                    mode="read",
                    # Missing $2
                    sql="SELECT * FROM test WHERE id = $1 AND active = $3 ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        "skipped": ModelDbParam(
                            name="skipped", param_type=EnumParameterType.STRING
                        ),
                        "active": ModelDbParam(
                            name="active", param_type=EnumParameterType.BOOLEAN
                        ),
                    },
                    param_order=("id", "skipped", "active"),
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        assert any("gap" in str(e).lower() or "$2" in str(e) for e in result.errors)

    def test_param_order_length_mismatch(self) -> None:
        """param_order length must match max positional index."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "length_mismatch": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = $1 AND name = $2 ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        "name": ModelDbParam(
                            name="name", param_type=EnumParameterType.STRING
                        ),
                        "extra": ModelDbParam(
                            name="extra", param_type=EnumParameterType.STRING
                        ),
                    },
                    # Only 2 positional params but 3 in param_order
                    param_order=("id", "name", "extra"),
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        assert any(
            "3 entries" in str(e) or "length" in str(e).lower() for e in result.errors
        )

    def test_param_order_too_short(self) -> None:
        """param_order too short for SQL positional indices should fail."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "too_short": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = $1 AND name = $2 AND email = $3 ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        "name": ModelDbParam(
                            name="name", param_type=EnumParameterType.STRING
                        ),
                        "email": ModelDbParam(
                            name="email", param_type=EnumParameterType.STRING
                        ),
                    },
                    # Only 2 in param_order but SQL uses $3
                    param_order=("id", "name"),
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        assert any("2 entries" in str(e) and "$3" in str(e) for e in result.errors)

    def test_mixing_positional_and_named_rejected(self) -> None:
        """Cannot mix positional ($N) and named (:param) in same SQL."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "mixed_params": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = $1 AND name = :name ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        "name": ModelDbParam(
                            name="name", param_type=EnumParameterType.STRING
                        ),
                    },
                    param_order=("id",),
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        assert any("mix" in str(e).lower() for e in result.errors)

    def test_param_order_invalid_reference_rejected_at_model_level(self) -> None:
        """param_order referencing non-existent param fails at model validation."""
        with pytest.raises(ValueError, match="not found in params"):
            ModelDbOperation(
                mode="read",
                sql="SELECT * FROM test WHERE id = $1 ORDER BY id",
                params={
                    "id": ModelDbParam(name="id", param_type=EnumParameterType.INTEGER),
                },
                # References 'nonexistent' which doesn't exist in params
                param_order=("id", "nonexistent"),
                returns=ModelDbReturn(model_ref="test:Model", many=True),
            )

    def test_param_order_with_named_params_rejected(self) -> None:
        """param_order should not be used with named parameters."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "named_with_order": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = :id ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                    },
                    param_order=("id",),
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        assert any(
            "param_order" in str(e) and "named" in str(e).lower() for e in result.errors
        )

    def test_positional_index_not_starting_at_one(self) -> None:
        """Positional indices must start at $1."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "wrong_start": ModelDbOperation(
                    mode="read",
                    # Starts at $2 instead of $1
                    sql="SELECT * FROM test WHERE id = $2 ORDER BY id",
                    params={
                        "placeholder": ModelDbParam(
                            name="placeholder", param_type=EnumParameterType.STRING
                        ),
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                    },
                    param_order=("placeholder", "id"),
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        # Should mention starting at $1
        assert any("$1" in str(e) or "start" in str(e).lower() for e in result.errors)

    def test_unused_param_with_positional(self) -> None:
        """Params declared but not in param_order should be flagged as unused."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "unused_with_positional": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test WHERE id = $1 ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        "unused_param": ModelDbParam(
                            name="unused_param", param_type=EnumParameterType.STRING
                        ),
                    },
                    param_order=("id",),
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert not result.is_valid
        assert any("unused" in str(e).lower() for e in result.errors)

    def test_duplicate_param_in_param_order_allowed(self) -> None:
        """Same param can be used multiple times in SQL via param_order."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "duplicate_usage": ModelDbOperation(
                    mode="read",
                    # Uses id twice via $1 and $2
                    sql="SELECT * FROM test WHERE id = $1 OR parent_id = $2 ORDER BY id",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                    },
                    param_order=("id", "id"),  # Same param mapped twice
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_params(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_keywords_in_string_literals_ignored(self) -> None:
        """SQL keywords inside string literals should not trigger validation errors."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["logs"],
            models={},
            ops={
                "log_message": ModelDbOperation(
                    mode="write",
                    # The word DROP is in a string literal - should not trigger DDL check
                    sql="INSERT INTO logs (message) VALUES ('User performed DROP action')",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_sql_safety(contract)
        # This should pass because DROP is inside a string literal
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_semicolon_in_string_literal_ignored(self) -> None:
        """Semicolons inside string literals should not trigger multi-statement check."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["logs"],
            models={},
            ops={
                "log_message": ModelDbOperation(
                    mode="write",
                    sql="INSERT INTO logs (message) VALUES ('End; Start')",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        # Multi-statement checking is in validate_db_sql_safety, not structural
        result = validate_db_sql_safety(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_param_in_string_literal_ignored(self) -> None:
        """Parameter-like patterns inside string literals should be ignored."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["logs"],
            models={},
            ops={
                "log_message": ModelDbOperation(
                    mode="write",
                    sql="INSERT INTO logs (message) VALUES ('Use :param syntax for params')",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        result = validate_db_params(contract)
        # The :param inside the string should not be counted as a real parameter
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_sql_with_comments_handled(self) -> None:
        """SQL comments should be stripped before validation."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "commented": ModelDbOperation(
                    mode="read",
                    sql="""
                        -- This is a comment with ORDER BY in it
                        SELECT * FROM test
                        /* Another comment: LIMIT 100 */
                        ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        # Real ORDER BY should be detected despite comments containing ORDER BY
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_case_insensitive_keywords(self) -> None:
        """SQL keywords should be detected case-insensitively."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "lowercase": ModelDbOperation(
                    mode="read",
                    sql="select * from test order by id",  # lowercase
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_deterministic(contract)
        assert result.is_valid, (
            f"Expected valid (case insensitive), got: {result.errors}"
        )

    def test_schema_qualified_table_name(self) -> None:
        """Schema-qualified table names should work."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],  # Table name without schema
            models={},
            ops={
                "schema_query": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM public.users ORDER BY id",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # public.users should match 'users' in tables list
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_doubled_quote_escape_in_string(self) -> None:
        """PostgreSQL-style doubled quotes inside strings should be handled."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["logs"],
            models={},
            ops={
                "log_message": ModelDbOperation(
                    mode="write",
                    sql="INSERT INTO logs (message) VALUES ('it''s working')",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        # Test all validators pass - the doubled quote shouldn't break anything
        assert validate_db_structural(contract).is_valid
        assert validate_db_sql_safety(contract).is_valid
        assert validate_db_table_access(contract).is_valid
        assert validate_db_params(contract).is_valid

    def test_backslash_escape_in_string(self) -> None:
        """Backslash-escaped quotes inside strings should be handled."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["logs"],
            models={},
            ops={
                "log_message": ModelDbOperation(
                    mode="write",
                    sql=r"INSERT INTO logs (message) VALUES ('foo\'bar')",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        # Test all validators pass
        assert validate_db_structural(contract).is_valid
        assert validate_db_sql_safety(contract).is_valid
        assert validate_db_table_access(contract).is_valid
        assert validate_db_params(contract).is_valid

    def test_ddl_keyword_after_escaped_quote(self) -> None:
        """DDL keywords should still be detected after escaped quote strings."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "dangerous": ModelDbOperation(
                    mode="write",
                    sql="INSERT INTO test VALUES ('safe''string'); DROP TABLE test",
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=False),
                ),
            },
        )
        # Should fail due to DDL keyword DROP outside string
        result = validate_db_sql_safety(contract)
        assert not result.is_valid
        assert any("DROP" in str(e) for e in result.errors)

    def test_column_names_with_sql_keywords_and_underscores(self) -> None:
        """Column names containing SQL keywords with underscores should not confuse parser.

        This tests that word boundary detection includes underscores.
        For example: col_FROM, created_from, FROM_date should NOT be
        mistaken for the FROM keyword.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "underscore_columns": ModelDbOperation(
                    mode="read",
                    sql="SELECT col_FROM, created_from, FROM_date FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["col_from", "created_from", "from_date"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, (
            f"Expected valid with underscore columns, got: {result.errors}"
        )


# ============================================================================
# CTE Table Extraction Tests (OMN-1791)
# ============================================================================


@pytest.mark.unit
class TestValidatorDbTableAccessCTE:
    """Test CTE table extraction with parser.

    These tests verify that CTEs are properly handled when the sqlglot
    parser is available. Tables inside CTE bodies are validated, while
    CTE alias names are correctly filtered out.
    """

    def test_simple_cte_tables_validated(self) -> None:
        """CTE tables are validated when parser available."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],
            models={},
            ops={
                "cte_query": ModelDbOperation(
                    mode="read",
                    sql="""
                        WITH active_users AS (
                            SELECT * FROM users WHERE active = true
                        )
                        SELECT * FROM active_users ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # Should pass because 'users' is in allowed list
        # and 'active_users' is a CTE name (not a table)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_cte_hidden_table_rejected(self) -> None:
        """CTE accessing undeclared table is rejected."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],  # 'secret_table' not declared
            models={},
            ops={
                "cte_query": ModelDbOperation(
                    mode="read",
                    sql="""
                        WITH data AS (
                            SELECT * FROM secret_table WHERE active = true
                        )
                        SELECT * FROM data ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # Should fail because 'secret_table' is not in allowed list
        assert not result.is_valid
        assert any("secret_table" in str(e) for e in result.errors)

    def test_cte_name_not_validated_as_table(self) -> None:
        """CTE alias names are not treated as tables.

        The CTE alias 'temp_data' should not trigger a validation error
        even though it's used in FROM clause - it's a CTE reference, not a table.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["real_table"],
            models={},
            ops={
                "cte_query": ModelDbOperation(
                    mode="read",
                    sql="""
                        WITH temp_data AS (
                            SELECT * FROM real_table
                        )
                        SELECT * FROM temp_data ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # Should pass - 'temp_data' is CTE alias, 'real_table' is declared
        assert result.is_valid, (
            f"CTE alias should not be validated as table: {result.errors}"
        )

    def test_multiple_ctes_validated(self) -> None:
        """Multiple CTEs in single query are all validated."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users", "orders"],
            models={},
            ops={
                "multi_cte": ModelDbOperation(
                    mode="read",
                    sql="""
                        WITH
                            active_users AS (SELECT * FROM users WHERE active = true),
                            recent_orders AS (SELECT * FROM orders WHERE date > '2024-01-01')
                        SELECT u.name, o.total
                        FROM active_users u
                        JOIN recent_orders o ON u.id = o.user_id
                        ORDER BY u.name
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Multiple CTEs should validate: {result.errors}"

    def test_recursive_cte_fails_closed(self) -> None:
        """WITH RECURSIVE always fails closed."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["employees"],
            models={},
            ops={
                "recursive_cte": ModelDbOperation(
                    mode="read",
                    sql="""
                        WITH RECURSIVE employee_tree AS (
                            SELECT id, name, manager_id FROM employees WHERE manager_id IS NULL
                            UNION ALL
                            SELECT e.id, e.name, e.manager_id
                            FROM employees e
                            JOIN employee_tree et ON e.manager_id = et.id
                        )
                        SELECT * FROM employee_tree ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # Should fail closed on WITH RECURSIVE
        assert not result.is_valid
        assert any("RECURSIVE" in str(e) for e in result.errors)


# ============================================================================
# Subquery Table Extraction Tests (OMN-1791)
# ============================================================================


@pytest.mark.unit
class TestValidatorDbTableAccessSubquery:
    """Test subquery table extraction with parser.

    These tests verify that tables inside subqueries are properly
    validated when the sqlglot parser is available.
    """

    def test_simple_subquery_tables_validated(self) -> None:
        """Subquery tables are validated when parser available."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],
            models={},
            ops={
                "subquery": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT * FROM (
                            SELECT id, name FROM users WHERE active = true
                        ) sub
                        ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # Should pass because 'users' is in allowed list
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_subquery_hidden_table_rejected(self) -> None:
        """Subquery accessing undeclared table is rejected."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],  # 'secret_table' not declared
            models={},
            ops={
                "subquery": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT * FROM (
                            SELECT * FROM secret_table
                        ) sub
                        ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # Should fail because 'secret_table' is not in allowed list
        assert not result.is_valid
        assert any("secret_table" in str(e) for e in result.errors)

    def test_subquery_alias_not_validated_as_table(self) -> None:
        """Subquery aliases should not be validated as tables.

        The subquery alias 'sub' should not trigger validation error.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["real_table"],
            models={},
            ops={
                "subquery": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT sub.id FROM (
                            SELECT * FROM real_table
                        ) sub
                        ORDER BY sub.id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, (
            f"Subquery alias should not be validated: {result.errors}"
        )

    def test_multiple_subqueries_validated(self) -> None:
        """Multiple subqueries in single query are all validated."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users", "orders"],
            models={},
            ops={
                "multi_subquery": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT u.name, o.total
                        FROM (SELECT * FROM users WHERE active = true) u
                        JOIN (SELECT * FROM orders WHERE status = 'completed') o
                        ON u.id = o.user_id
                        ORDER BY u.name
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Multiple subqueries should validate: {result.errors}"

    def test_in_clause_subquery_validated(self) -> None:
        """Tables in IN clause subqueries are validated."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users", "active_user_ids"],
            models={},
            ops={
                "in_subquery": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT * FROM users
                        WHERE id IN (SELECT user_id FROM active_user_ids)
                        ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert result.is_valid, f"IN clause subquery should validate: {result.errors}"

    def test_in_clause_hidden_table_rejected(self) -> None:
        """Hidden table in IN clause subquery is rejected."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],  # 'secret_ids' not declared
            models={},
            ops={
                "in_subquery": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT * FROM users
                        WHERE id IN (SELECT user_id FROM secret_ids)
                        ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        assert not result.is_valid
        assert any("secret_ids" in str(e) for e in result.errors)


# ============================================================================
# Parser Fallback Tests (OMN-1791)
# ============================================================================


@pytest.mark.unit
class TestValidatorDbTableAccessParserIntegration:
    """Test parser integration and fallback behavior.

    These tests verify that simple SQL uses the fast regex path,
    and that the validator provides helpful error messages when
    complex SQL requires the parser.
    """

    def test_simple_sql_works_without_parser(self) -> None:
        """Simple SQL (no CTE/subquery) works without parser."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users", "orders"],
            models={},
            ops={
                "simple_join": ModelDbOperation(
                    mode="read",
                    sql="""
                        SELECT u.name, o.total
                        FROM users u
                        JOIN orders o ON u.id = o.user_id
                        ORDER BY u.name
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        # This should always work - uses regex fast path
        result = validate_db_table_access(contract)
        assert result.is_valid, f"Simple SQL should not need parser: {result.errors}"

    def test_cte_with_parser_available(self) -> None:
        """CTE validation succeeds when parser is available.

        This test will pass when sqlglot is installed (dev dependencies).
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users"],
            models={},
            ops={
                "cte_query": ModelDbOperation(
                    mode="read",
                    sql="""
                        WITH active AS (SELECT * FROM users WHERE active = true)
                        SELECT * FROM active ORDER BY id
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # In dev environment with sqlglot installed, this should pass
        # In production without sqlglot, this should fail with helpful message
        if not result.is_valid:
            # Verify the error message is helpful
            assert any("sql-parser" in str(e) for e in result.errors)

    def test_nested_cte_and_subquery(self) -> None:
        """Complex SQL with both CTE and subquery validates correctly."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["users", "orders"],
            models={},
            ops={
                "complex_query": ModelDbOperation(
                    mode="read",
                    sql="""
                        WITH recent_users AS (
                            SELECT * FROM users WHERE created_at > '2024-01-01'
                        )
                        SELECT u.name, (SELECT COUNT(*) FROM orders WHERE user_id = u.id) as order_count
                        FROM recent_users u
                        ORDER BY u.name
                    """,
                    params={},
                    returns=ModelDbReturn(model_ref="test:Model", many=True),
                ),
            },
        )
        result = validate_db_table_access(contract)
        # With parser, should pass (users and orders are declared)
        # Without parser, should fail with helpful message
        if not result.is_valid:
            assert any("sql-parser" in str(e) or "CTE" in str(e) for e in result.errors)


# Field Projection Validator (OMN-1790)
# ============================================================================


@pytest.mark.unit
class TestValidatorDbProjection:
    """Test field projection validator.

    Validates that SQL SELECT projections match declared fields when
    strict mode is enabled (default when fields are declared).
    """

    # === PASS CASES ===

    def test_simple_match_passes(self) -> None:
        """Simple column match passes validation."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql="SELECT id, name FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, f"Expected valid, got: {result.errors}"

    def test_alias_match_passes(self) -> None:
        """Alias in SELECT matches declared field."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql="SELECT user_id AS id FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, f"Expected valid, got: {result.errors}"

    def test_table_prefix_stripped(self) -> None:
        """Table prefix is stripped from columns."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql="SELECT t.id, t.name FROM test t ORDER BY t.id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, f"Expected valid, got: {result.errors}"

    def test_no_fields_skips_validation(self) -> None:
        """No fields declared skips validation entirely."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_all": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        # fields=None (default) - no projection validation
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, f"Expected valid (skipped), got: {result.errors}"

    def test_case_insensitive_match(self) -> None:
        """Field matching is case-insensitive."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql="SELECT ID, Name FROM test ORDER BY ID",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, (
            f"Expected valid (case-insensitive), got: {result.errors}"
        )

    def test_case_insensitive_duplicate_fields_rejected(self) -> None:
        """Fields with case-insensitive duplicates are rejected at model level.

        Since SQL column names are case-insensitive, ['id', 'ID'] would collapse
        to the same effective field during projection validation. We catch this
        early at model instantiation to prevent configuration errors.
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ModelDbReturn(
                model_ref="test:Model",
                many=True,
                fields=["id", "ID"],  # Case-insensitive duplicates
            )
        assert "case-insensitive" in str(exc_info.value).lower()

    # === STRICT MODE FAILURES ===

    def test_select_star_strict_fails(self) -> None:
        """SELECT * in strict mode fails."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_all": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],  # Strict mode enabled by default
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert not result.is_valid
        assert any("SELECT *" in str(e) for e in result.errors)

    def test_table_star_strict_fails(self) -> None:
        """SELECT table.* in strict mode fails."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_all": ModelDbOperation(
                    mode="read",
                    sql="SELECT t.* FROM test t ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],  # Strict mode enabled
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert not result.is_valid
        assert any(
            "SELECT *" in str(e) or "strict mode" in str(e) for e in result.errors
        )

    def test_missing_field_strict_fails(self) -> None:
        """Missing declared field in SQL fails in strict mode."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql="SELECT id FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],  # 'name' is missing in SQL
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert not result.is_valid
        assert any("name" in str(e).lower() for e in result.errors)

    def test_extra_field_strict_fails(self) -> None:
        """Extra field in SQL not declared fails in strict mode."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql="SELECT id, name, age FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],  # 'age' is extra in SQL
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert not result.is_valid
        assert any("age" in str(e).lower() for e in result.errors)

    def test_complex_expression_strict_fails(self) -> None:
        """Complex expression (function) in strict mode fails."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_count": ModelDbOperation(
                    mode="read",
                    sql="SELECT COUNT(*), id FROM test GROUP BY id ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["count", "id"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert not result.is_valid
        assert any("complex" in str(e).lower() for e in result.errors)

    def test_case_expression_strict_fails(self) -> None:
        """CASE expression in strict mode fails."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_status": ModelDbOperation(
                    mode="read",
                    sql="SELECT CASE WHEN x > 0 THEN 'yes' ELSE 'no' END AS status FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["status"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert not result.is_valid
        assert any("complex" in str(e).lower() for e in result.errors)

    # === LENIENT MODE (strict=False) ===

    def test_select_star_lenient_warns(self) -> None:
        """SELECT * in lenient mode warns but passes."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_all": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],
                        strict=False,  # Lenient mode
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, f"Expected valid in lenient mode, got: {result.errors}"
        assert len(result.warnings) > 0
        assert any("SELECT *" in str(w) for w in result.warnings)

    def test_field_mismatch_lenient_warns(self) -> None:
        """Field mismatch in lenient mode warns but passes."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql="SELECT id FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],  # 'name' is missing
                        strict=False,  # Lenient mode
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, f"Expected valid in lenient mode, got: {result.errors}"
        assert len(result.warnings) > 0
        assert any("mismatch" in str(w).lower() for w in result.warnings)

    # === ESCAPE HATCH ===

    def test_select_star_allowed_warns(self) -> None:
        """SELECT * with allow_select_star=True warns but passes."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_all": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],
                        allow_select_star=True,  # Escape hatch
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, (
            f"Expected valid with escape hatch, got: {result.errors}"
        )
        assert len(result.warnings) > 0
        assert any("allow_select_star" in str(w) for w in result.warnings)

    # === EDGE CASES ===

    def test_strict_true_no_fields_warns(self) -> None:
        """strict=True with no fields declared emits warning."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_all": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        # fields=None (not declared)
                        strict=True,  # Explicit strict but no fields
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, f"Expected valid (skipped), got: {result.errors}"
        assert len(result.warnings) > 0
        assert any(
            "strict=True" in str(w) and "no fields" in str(w).lower()
            for w in result.warnings
        )

    def test_write_operation_skipped(self) -> None:
        """Write operations (INSERT/UPDATE/DELETE) are not validated."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "insert_user": ModelDbOperation(
                    mode="write",
                    sql="INSERT INTO test (id, name) VALUES (:id, :name)",
                    params={
                        "id": ModelDbParam(
                            name="id", param_type=EnumParameterType.INTEGER
                        ),
                        "name": ModelDbParam(
                            name="name", param_type=EnumParameterType.STRING
                        ),
                    },
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=False,
                        fields=["id", "name"],  # Declared but ignored for write
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, f"Expected valid for write op, got: {result.errors}"

    def test_multiple_operations_mixed(self) -> None:
        """Multiple operations with mixed results are validated together."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "good_op": ModelDbOperation(
                    mode="read",
                    sql="SELECT id, name FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],
                    ),
                ),
                "bad_op": ModelDbOperation(
                    mode="read",
                    sql="SELECT * FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id"],  # SELECT * with fields = error
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert not result.is_valid
        assert any("bad_op" in str(e) for e in result.errors)

    def test_quoted_alias_case_preserved_in_extraction(self) -> None:
        """Quoted aliases preserve case in SQL extraction.

        Note: The validator lowercases declared fields for comparison, so
        quoted aliases with non-lowercase names will only match if the
        declared field is also specified with matching case.

        Since the validator uses case-insensitive comparison (lowercases declared
        fields), quoted aliases are effectively case-insensitive for matching.
        """
        # With lowercase declared field, it should match the lowercase version
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql='SELECT user_id AS "userid" FROM test ORDER BY user_id',
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["userid"],  # Lowercase to match
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, (
            f"Expected valid with quoted alias, got: {result.errors}"
        )

    def test_mixed_case_quoted_alias_matches(self) -> None:
        """Mixed-case quoted aliases match case-insensitively.

        SQL quoted identifiers preserve case (e.g., "UserId" stays as "UserId"),
        but field comparison should be case-insensitive since SQL columns are
        case-insensitive in most databases.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql='SELECT user_id AS "UserId" FROM test ORDER BY user_id',
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["userid"],  # Lowercase field matches "UserId" alias
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, (
            f"Expected valid with mixed-case quoted alias, got: {result.errors}"
        )

    def test_implicit_alias_match(self) -> None:
        """Implicit alias (without AS keyword) is recognized."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_user": ModelDbOperation(
                    mode="read",
                    sql="SELECT user_id uid FROM test ORDER BY uid",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["uid"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, (
            f"Expected valid with implicit alias, got: {result.errors}"
        )

    def test_distinct_keyword_handled(self) -> None:
        """SELECT DISTINCT is handled correctly."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_unique": ModelDbOperation(
                    mode="read",
                    sql="SELECT DISTINCT id, name FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["id", "name"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        assert result.is_valid, f"Expected valid with DISTINCT, got: {result.errors}"

    def test_escaped_quote_in_string_handled(self) -> None:
        """SQL-standard doubled quotes inside strings are handled correctly.

        The string 'It''s FROM here' contains doubled quotes (SQL escape) and
        the word FROM. Without proper handling, the FROM inside the string could
        be detected as the FROM clause boundary, breaking column extraction.
        """
        contract = ModelDbRepositoryContract(
            name="test",
            engine=EnumDatabaseEngine.POSTGRES,
            database_ref="db",
            tables=["test"],
            models={},
            ops={
                "get_msg": ModelDbOperation(
                    mode="read",
                    sql="SELECT 'It''s FROM here' AS msg, id FROM test ORDER BY id",
                    params={},
                    returns=ModelDbReturn(
                        model_ref="test:Model",
                        many=True,
                        fields=["msg", "id"],
                    ),
                ),
            },
        )
        result = validate_db_projection(contract)
        # String literals with explicit AS aliases are handled correctly.
        # The alias 'msg' is extracted, so this passes validation.
        # (String literals WITHOUT aliases would be marked as complex.)
        assert result.is_valid, (
            f"Expected valid (string literal with alias extracted), got: {result.errors}"
        )
