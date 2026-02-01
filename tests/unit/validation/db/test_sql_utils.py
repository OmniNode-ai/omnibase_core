"""Unit tests for SQL utility functions.

Tests for normalize_sql and strip_sql_strings functions in sql_utils.py.
These functions handle SQL preprocessing for pattern matching validation.
"""

import pytest

from omnibase_core.validation.db.sql_utils import normalize_sql, strip_sql_strings


@pytest.mark.unit
class TestNormalizeSql:
    """Tests for normalize_sql function."""

    def test_strips_single_line_comment(self) -> None:
        """Single-line comments (-- to end of line) are removed."""
        sql = "SELECT * FROM users -- get all users"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users"

    def test_strips_multi_line_comment(self) -> None:
        """Multi-line comments (/* ... */) are removed."""
        sql = "SELECT * FROM users /* this is a comment */ WHERE active = true"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users WHERE active = true"

    def test_strips_multi_line_comment_spanning_lines(self) -> None:
        """Multi-line comments spanning multiple lines are removed."""
        sql = """SELECT * FROM users
        /* this is
           a multi-line
           comment */
        WHERE active = true"""
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users WHERE active = true"

    def test_collapses_whitespace(self) -> None:
        """Excess whitespace is collapsed to single spaces."""
        sql = "SELECT   *   FROM    users"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users"

    def test_collapses_newlines(self) -> None:
        """Newlines are collapsed to single spaces."""
        sql = """SELECT *
        FROM users
        WHERE active = true"""
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users WHERE active = true"

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Leading and trailing whitespace is stripped."""
        sql = "   SELECT * FROM users   "
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users"

    def test_preserves_comment_like_pattern_in_single_quoted_string(self) -> None:
        """Comment-like patterns (--) inside single-quoted strings are preserved."""
        sql = "SELECT * FROM t WHERE msg = 'value -- not a comment'"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM t WHERE msg = 'value -- not a comment'"

    def test_preserves_comment_like_pattern_in_double_quoted_string(self) -> None:
        """Comment-like patterns (--) inside double-quoted strings are preserved."""
        sql = 'SELECT * FROM t WHERE msg = "value -- not a comment"'
        result = normalize_sql(sql)
        assert result == 'SELECT * FROM t WHERE msg = "value -- not a comment"'

    def test_preserves_multiline_comment_pattern_in_string(self) -> None:
        """Multi-line comment patterns (/* */) inside strings are preserved."""
        sql = "SELECT * FROM t WHERE msg = 'value /* not a comment */'"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM t WHERE msg = 'value /* not a comment */'"

    def test_strips_real_comment_after_string_with_comment_pattern(self) -> None:
        """Real comments after strings containing comment patterns are stripped."""
        sql = "SELECT * FROM t WHERE msg = 'value -- in string' -- real comment"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM t WHERE msg = 'value -- in string'"

    def test_preserves_escaped_quote_in_string(self) -> None:
        """Escaped quotes (doubled) inside strings are handled correctly."""
        sql = "SELECT * FROM t WHERE msg = 'it''s -- not a comment'"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM t WHERE msg = 'it''s -- not a comment'"

    def test_preserves_backslash_escaped_quote_in_string(self) -> None:
        r"""Backslash-escaped quotes inside strings are handled correctly."""
        sql = r"SELECT * FROM t WHERE msg = 'foo\'bar -- not a comment'"
        result = normalize_sql(sql)
        assert result == r"SELECT * FROM t WHERE msg = 'foo\'bar -- not a comment'"

    def test_multiple_strings_with_comments(self) -> None:
        """Multiple strings containing comment patterns are all preserved."""
        sql = (
            "SELECT * FROM t WHERE a = 'val -- 1' AND b = 'val /* 2 */' -- real comment"
        )
        result = normalize_sql(sql)
        assert result == "SELECT * FROM t WHERE a = 'val -- 1' AND b = 'val /* 2 */'"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert normalize_sql("") == ""

    def test_only_whitespace(self) -> None:
        """String with only whitespace returns empty string."""
        assert normalize_sql("   \n\t   ") == ""

    def test_only_comment(self) -> None:
        """String with only comment returns empty string."""
        assert normalize_sql("-- just a comment") == ""

    def test_combined_normalization(self) -> None:
        """Full normalization test with comments, whitespace, and strings."""
        sql = """
            -- Header comment
            SELECT *   FROM   users
            /* block comment */
            WHERE msg = 'test -- value'
            -- trailing comment
        """
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users WHERE msg = 'test -- value'"


@pytest.mark.unit
class TestStripSqlStrings:
    """Tests for strip_sql_strings function."""

    def test_strips_single_quoted_string(self) -> None:
        """Single-quoted strings are removed."""
        sql = "SELECT * FROM t WHERE name = 'John'"
        result = strip_sql_strings(sql)
        assert result == "SELECT * FROM t WHERE name = "

    def test_strips_double_quoted_string(self) -> None:
        """Double-quoted strings are removed."""
        sql = 'SELECT * FROM t WHERE name = "John"'
        result = strip_sql_strings(sql)
        assert result == "SELECT * FROM t WHERE name = "

    def test_strips_multiple_strings(self) -> None:
        """Multiple string literals are all removed."""
        sql = "SELECT * FROM t WHERE a = 'x' AND b = 'y'"
        result = strip_sql_strings(sql)
        assert result == "SELECT * FROM t WHERE a =  AND b = "

    def test_handles_doubled_quote_escape(self) -> None:
        """Doubled quotes (SQL-standard escape) are handled correctly."""
        sql = "SELECT * FROM t WHERE name = 'O''Brien'"
        result = strip_sql_strings(sql)
        assert result == "SELECT * FROM t WHERE name = "

    def test_handles_backslash_escape(self) -> None:
        r"""Backslash-escaped quotes are handled correctly."""
        sql = r"SELECT * FROM t WHERE name = 'foo\'bar'"
        result = strip_sql_strings(sql)
        assert result == "SELECT * FROM t WHERE name = "

    def test_ddl_keyword_in_string_removed(self) -> None:
        """DDL keywords inside strings are removed with the string."""
        sql = "SELECT * FROM t WHERE msg = 'DROP TABLE'"
        result = strip_sql_strings(sql)
        assert "DROP" not in result
        assert result == "SELECT * FROM t WHERE msg = "

    def test_empty_string_literal(self) -> None:
        """Empty string literals are removed."""
        sql = "SELECT * FROM t WHERE name = ''"
        result = strip_sql_strings(sql)
        assert result == "SELECT * FROM t WHERE name = "

    def test_no_strings(self) -> None:
        """SQL without strings is unchanged."""
        sql = "SELECT * FROM users WHERE id = 123"
        result = strip_sql_strings(sql)
        assert result == sql


@pytest.mark.unit
class TestIntegration:
    """Integration tests combining normalize_sql and strip_sql_strings."""

    def test_normalize_then_strip(self) -> None:
        """Typical usage: normalize first, then strip strings."""
        sql = """
            SELECT * FROM logs
            -- This comment should be removed
            WHERE message = 'DROP TABLE users'
        """
        normalized = normalize_sql(sql)
        stripped = strip_sql_strings(normalized)

        # DROP should not appear in final result (it was in a string)
        assert "DROP" not in stripped
        assert "SELECT * FROM logs WHERE message =" in stripped

    def test_comment_in_string_preserved_then_stripped(self) -> None:
        """Comment-like pattern in string is preserved through normalization."""
        sql = "SELECT * FROM t WHERE msg = 'val -- comment' -- real comment"
        normalized = normalize_sql(sql)

        # String content is preserved, real comment is stripped
        assert normalized == "SELECT * FROM t WHERE msg = 'val -- comment'"

        # Now strip strings
        stripped = strip_sql_strings(normalized)
        assert stripped == "SELECT * FROM t WHERE msg = "
