"""Unit tests for DB repository contract validators.

This module tests all five DB repository validators:
- validate_db_structural: Required fields, valid identifiers, single statements
- validate_db_sql_safety: read->SELECT, forbid DDL, safety policy
- validate_db_table_access: Tables in SQL <= declared tables
- validate_db_deterministic: many=True -> ORDER BY required
- validate_db_params: Named params validation

Each validator has:
1. A golden contract test showing it passes
2. One or more failure cases showing it correctly rejects invalid contracts
"""

import pytest

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
        engine="postgres",
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


class TestValidatorDbStructural:
    """Test structural validator failure cases."""

    def test_invalid_table_name_starts_with_number(self) -> None:
        """Table names must be valid SQL identifiers (start with letter)."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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


class TestValidatorDbSqlSafety:
    """Test SQL safety validator failure cases."""

    def test_read_mode_with_insert(self) -> None:
        """Read mode must use SELECT."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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


class TestValidatorDbTableAccess:
    """Test table access validator failure cases."""

    def test_undeclared_table(self) -> None:
        """SQL can only access declared tables."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
            engine="postgres",
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

    def test_cte_fails_closed(self) -> None:
        """CTEs are not supported and should fail closed."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
        assert not result.is_valid
        assert any("CTE" in str(e) for e in result.errors)

    def test_subquery_fails_closed(self) -> None:
        """Subqueries are not supported and should fail closed."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
        assert not result.is_valid
        assert any("subquery" in str(e).lower() for e in result.errors)

    def test_multiple_declared_tables_pass(self) -> None:
        """Multiple tables can be declared and accessed."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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


class TestValidatorDbDeterministic:
    """Test deterministic ordering validator failure cases."""

    def test_many_without_order_by(self) -> None:
        """many=True requires ORDER BY."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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


class TestValidatorDbParams:
    """Test parameter validator failure cases."""

    def test_positional_params_rejected(self) -> None:
        """Positional parameters ($1, $2) are not allowed."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
        assert any("Positional" in str(e) or "$1" in str(e) for e in result.errors)

    def test_undefined_param(self) -> None:
        """All :params in SQL must be declared."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
            engine="postgres",
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

    def test_multiple_positional_params(self) -> None:
        """Multiple positional params are all reported."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
        # Should mention both $1 and $2
        assert any("$1" in str(e) for e in result.errors)
        assert any("$2" in str(e) for e in result.errors)

    def test_empty_params_with_no_placeholders_passes(self) -> None:
        """No params required if SQL has no placeholders."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
            engine="postgres",
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
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_keywords_in_string_literals_ignored(self) -> None:
        """SQL keywords inside string literals should not trigger validation errors."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
            engine="postgres",
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
        result = validate_db_structural(contract)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"

    def test_param_in_string_literal_ignored(self) -> None:
        """Parameter-like patterns inside string literals should be ignored."""
        contract = ModelDbRepositoryContract(
            name="test",
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
            engine="postgres",
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
