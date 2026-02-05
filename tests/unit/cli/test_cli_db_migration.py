"""Unit tests for DB migration CLI commands."""

from pathlib import Path

import pytest

from omnibase_core.cli.cli_db_migration import (
    convert_positional_to_named,
    migrate_contract,
    migrate_operation,
)


@pytest.mark.unit
class TestConvertPositionalToNamed:
    """Tests for convert_positional_to_named function."""

    def test_single_param(self) -> None:
        """Convert single positional param."""
        sql = "SELECT * FROM users WHERE id = $1"
        result = convert_positional_to_named(sql, ["user_id"])
        assert result == "SELECT * FROM users WHERE id = :user_id"

    def test_multiple_params(self) -> None:
        """Convert multiple positional params."""
        sql = "SELECT * FROM users WHERE id = $1 AND name = $2"
        result = convert_positional_to_named(sql, ["user_id", "user_name"])
        assert result == "SELECT * FROM users WHERE id = :user_id AND name = :user_name"

    def test_params_in_insert(self) -> None:
        """Convert params in INSERT statement."""
        sql = "INSERT INTO users (id, name, email) VALUES ($1, $2, $3)"
        result = convert_positional_to_named(sql, ["id", "name", "email"])
        assert (
            result == "INSERT INTO users (id, name, email) VALUES (:id, :name, :email)"
        )

    def test_duplicate_param_usage(self) -> None:
        """Same param can be referenced multiple times."""
        sql = "SELECT * FROM users WHERE id = $1 OR parent_id = $1"
        result = convert_positional_to_named(sql, ["user_id"])
        assert (
            result == "SELECT * FROM users WHERE id = :user_id OR parent_id = :user_id"
        )

    def test_out_of_bounds_index_raises(self) -> None:
        """Out of bounds positional index raises ValueError."""
        sql = "SELECT * FROM users WHERE id = $3"
        with pytest.raises(ValueError, match="out of bounds"):
            convert_positional_to_named(sql, ["only_one"])

    def test_zero_index_raises(self) -> None:
        """$0 is out of bounds (1-based indexing)."""
        sql = "SELECT * FROM users WHERE id = $0"
        with pytest.raises(ValueError, match="out of bounds"):
            convert_positional_to_named(sql, ["some_param"])

    def test_no_params_unchanged(self) -> None:
        """SQL without positional params is unchanged."""
        sql = "SELECT * FROM users WHERE active = true"
        result = convert_positional_to_named(sql, [])
        assert result == sql

    def test_preserves_other_dollar_signs(self) -> None:
        """Dollar signs not followed by digits are preserved."""
        sql = "SELECT price FROM items WHERE cost = $1 AND currency = '$$USD$$'"
        result = convert_positional_to_named(sql, ["cost_value"])
        assert (
            result
            == "SELECT price FROM items WHERE cost = :cost_value AND currency = '$$USD$$'"
        )


@pytest.mark.unit
class TestMigrateOperation:
    """Tests for migrate_operation function."""

    def test_migrate_operation_with_positional(self) -> None:
        """Operation with positional params is migrated."""
        op_data = {
            "mode": "read",
            "sql": "SELECT * FROM users WHERE id = $1",
            "params": {"user_id": {"name": "user_id", "param_type": "integer"}},
            "param_order": ["user_id"],
            "returns": {"model_ref": "test:User", "many": False},
        }
        result = migrate_operation(op_data)

        assert result["sql"] == "SELECT * FROM users WHERE id = :user_id"
        assert "param_order" not in result
        assert result["params"] == op_data["params"]
        assert result["returns"] == op_data["returns"]

    def test_migrate_operation_without_positional(self) -> None:
        """Operation without positional params is unchanged."""
        op_data = {
            "mode": "read",
            "sql": "SELECT * FROM users WHERE id = :user_id",
            "params": {"user_id": {"name": "user_id", "param_type": "integer"}},
            "returns": {"model_ref": "test:User", "many": False},
        }
        result = migrate_operation(op_data)

        assert result["sql"] == op_data["sql"]
        assert "param_order" not in result

    def test_migrate_operation_removes_unused_param_order(self) -> None:
        """param_order is removed even if SQL has no positional params."""
        op_data = {
            "mode": "read",
            "sql": "SELECT * FROM users WHERE id = :user_id",
            "params": {"user_id": {"name": "user_id", "param_type": "integer"}},
            "param_order": ["user_id"],  # Shouldn't be here but we clean it up
            "returns": {"model_ref": "test:User", "many": False},
        }
        result = migrate_operation(op_data)

        assert "param_order" not in result

    def test_migrate_operation_missing_param_order_raises(self) -> None:
        """Positional params without param_order raises error."""
        op_data = {
            "mode": "read",
            "sql": "SELECT * FROM users WHERE id = $1",
            "params": {"user_id": {"name": "user_id", "param_type": "integer"}},
            # Missing param_order!
            "returns": {"model_ref": "test:User", "many": False},
        }
        with pytest.raises(ValueError, match="no param_order"):
            migrate_operation(op_data)


@pytest.mark.unit
class TestMigrateContract:
    """Tests for migrate_contract function."""

    def test_migrate_full_contract(self) -> None:
        """Full contract with multiple operations is migrated."""
        contract_data = {
            "name": "test_repo",
            "engine": "postgres",
            "database_ref": "test_db",
            "tables": ["users", "orders"],
            "models": {},
            "ops": {
                "get_user": {
                    "mode": "read",
                    "sql": "SELECT * FROM users WHERE id = $1",
                    "params": {"user_id": {"name": "user_id", "param_type": "integer"}},
                    "param_order": ["user_id"],
                    "returns": {"model_ref": "test:User", "many": False},
                },
                "list_orders": {
                    "mode": "read",
                    "sql": "SELECT * FROM orders WHERE user_id = :user_id ORDER BY id",
                    "params": {"user_id": {"name": "user_id", "param_type": "integer"}},
                    "returns": {"model_ref": "test:Order", "many": True},
                },
            },
        }
        result = migrate_contract(contract_data)

        # get_user should be migrated
        assert (
            result["ops"]["get_user"]["sql"]
            == "SELECT * FROM users WHERE id = :user_id"
        )
        assert "param_order" not in result["ops"]["get_user"]

        # list_orders should be unchanged
        assert (
            result["ops"]["list_orders"]["sql"]
            == contract_data["ops"]["list_orders"]["sql"]
        )

        # Non-ops fields should be preserved
        assert result["name"] == "test_repo"
        assert result["tables"] == ["users", "orders"]

    def test_migrate_empty_ops(self) -> None:
        """Contract with empty ops is handled."""
        contract_data = {
            "name": "empty_repo",
            "engine": "postgres",
            "database_ref": "test_db",
            "tables": [],
            "models": {},
            "ops": {},
        }
        result = migrate_contract(contract_data)

        assert result["ops"] == {}
        assert result["name"] == "empty_repo"

    def test_migrate_non_dict_ops_unchanged(self) -> None:
        """Contract with non-dict ops is returned unchanged."""
        contract_data = {
            "name": "invalid_repo",
            "engine": "postgres",
            "ops": [
                "not",
                "a",
                "dict",
            ],  # Invalid but migrate_contract handles gracefully
        }
        result = migrate_contract(contract_data)

        # Should return unchanged since ops isn't a dict
        assert result["ops"] == ["not", "a", "dict"]


@pytest.mark.unit
class TestMigrateParamsCLI:
    """Tests for the migrate-params CLI command."""

    def test_dry_run_shows_preview(self, tmp_path: Path) -> None:
        """Dry run shows what would be changed without modifying files."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_db_migration import db

        # Create test contract file
        contract_file = tmp_path / "contract.yaml"
        contract_content = """
name: test_repo
engine: postgres
database_ref: test_db
tables: [users]
models: {}
ops:
  get_user:
    mode: read
    sql: SELECT * FROM users WHERE id = $1
    params:
      user_id:
        name: user_id
        param_type: integer
    param_order: [user_id]
    returns:
      model_ref: "test:User"
      many: false
"""
        contract_file.write_text(contract_content)

        runner = CliRunner()
        result = runner.invoke(db, ["migrate-params", str(contract_file), "--dry-run"])

        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "get_user" in result.output
        # Original file should be unchanged
        assert "$1" in contract_file.read_text()

    def test_output_to_file(self, tmp_path: Path) -> None:
        """Output to specified file preserves original."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_db_migration import db

        contract_file = tmp_path / "contract.yaml"
        output_file = tmp_path / "migrated.yaml"
        contract_content = """
name: test_repo
engine: postgres
database_ref: test_db
tables: [users]
models: {}
ops:
  get_user:
    mode: read
    sql: SELECT * FROM users WHERE id = $1
    params:
      user_id:
        name: user_id
        param_type: integer
    param_order: [user_id]
    returns:
      model_ref: "test:User"
      many: false
"""
        contract_file.write_text(contract_content)

        runner = CliRunner()
        result = runner.invoke(
            db, ["migrate-params", str(contract_file), "-o", str(output_file)]
        )

        assert result.exit_code == 0
        # Original unchanged
        assert "$1" in contract_file.read_text()
        # Output has migrated SQL
        output_content = output_file.read_text()
        assert ":user_id" in output_content
        assert "$1" not in output_content

    def test_in_place_modifies_file(self, tmp_path: Path) -> None:
        """In-place mode modifies the original file."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_db_migration import db

        contract_file = tmp_path / "contract.yaml"
        contract_content = """
name: test_repo
engine: postgres
database_ref: test_db
tables: [users]
models: {}
ops:
  get_user:
    mode: read
    sql: SELECT * FROM users WHERE id = $1
    params:
      user_id:
        name: user_id
        param_type: integer
    param_order: [user_id]
    returns:
      model_ref: "test:User"
      many: false
"""
        contract_file.write_text(contract_content)

        runner = CliRunner()
        result = runner.invoke(db, ["migrate-params", str(contract_file), "--in-place"])

        assert result.exit_code == 0
        # File should be modified
        modified_content = contract_file.read_text()
        assert ":user_id" in modified_content
        assert "$1" not in modified_content

    def test_in_place_and_output_conflict(self, tmp_path: Path) -> None:
        """Cannot use both --in-place and --output."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_db_migration import db

        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text("name: test\nops: {}")

        runner = CliRunner()
        result = runner.invoke(
            db,
            [
                "migrate-params",
                str(contract_file),
                "--in-place",
                "-o",
                str(tmp_path / "out.yaml"),
            ],
        )

        assert result.exit_code != 0
        assert "Cannot use both" in result.output

    def test_no_migration_needed(self, tmp_path: Path) -> None:
        """Reports when no positional params found."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_db_migration import db

        contract_file = tmp_path / "contract.yaml"
        contract_content = """
name: test_repo
engine: postgres
database_ref: test_db
ops:
  get_user:
    mode: read
    sql: SELECT * FROM users WHERE id = :user_id
    params:
      user_id:
        name: user_id
        param_type: integer
"""
        contract_file.write_text(contract_content)

        runner = CliRunner()
        result = runner.invoke(db, ["migrate-params", str(contract_file)])

        assert result.exit_code == 0
        assert "No positional parameters found" in result.output

    def test_invalid_ops_structure_error(self, tmp_path: Path) -> None:
        """Reports error when ops is not a dict."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_db_migration import db

        contract_file = tmp_path / "contract.yaml"
        contract_content = """
name: test_repo
engine: postgres
ops:
  - not
  - a
  - dict
"""
        contract_file.write_text(contract_content)

        runner = CliRunner()
        result = runner.invoke(db, ["migrate-params", str(contract_file)])

        assert result.exit_code != 0
        assert "Invalid 'ops' structure" in result.output

    def test_invalid_yaml_error(self, tmp_path: Path) -> None:
        """Reports error for invalid YAML."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_db_migration import db

        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text("invalid: yaml: content: [")

        runner = CliRunner()
        result = runner.invoke(db, ["migrate-params", str(contract_file)])

        assert result.exit_code != 0
        assert "YAML parsing error" in result.output

    def test_missing_param_order_error(self, tmp_path: Path) -> None:
        """Reports error when positional params lack param_order."""
        from click.testing import CliRunner

        from omnibase_core.cli.cli_db_migration import db

        contract_file = tmp_path / "contract.yaml"
        contract_content = """
name: test_repo
engine: postgres
ops:
  get_user:
    mode: read
    sql: SELECT * FROM users WHERE id = $1
    params:
      user_id:
        name: user_id
        param_type: integer
    # Missing param_order!
"""
        contract_file.write_text(contract_content)

        runner = CliRunner()
        result = runner.invoke(db, ["migrate-params", str(contract_file)])

        assert result.exit_code != 0
        assert "no param_order" in result.output or "Validation errors" in result.output
