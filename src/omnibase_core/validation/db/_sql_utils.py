"""Shared SQL utility functions for database repository validators.

This module provides common SQL processing utilities used across multiple
database validators. These functions handle SQL normalization and string
literal removal to enable accurate pattern matching in SQL validation.

Functions:
    normalize_sql: Remove comments and collapse whitespace from SQL.
    strip_sql_strings: Remove string literals to prevent false positives.

Example:
    >>> from omnibase_core.validation.db._sql_utils import normalize_sql, strip_sql_strings
    >>> sql = "SELECT * FROM users -- get all users"
    >>> normalized = normalize_sql(sql)
    >>> "SELECT * FROM users"
    >>> clean = strip_sql_strings("SELECT * FROM t WHERE name = 'DROP TABLE'")
    >>> # Returns: "SELECT * FROM t WHERE name = "
"""

import re

__all__ = ["normalize_sql", "strip_sql_strings"]


def normalize_sql(sql: str) -> str:
    """Normalize SQL by stripping comments and collapsing whitespace.

    This function prepares raw SQL for pattern matching by removing
    elements that could interfere with validation logic:

    - Single-line comments (-- comment to end of line)
    - Multi-line comments (/* comment block */)
    - Excess whitespace (collapsed to single spaces)

    Args:
        sql: Raw SQL string to normalize.

    Returns:
        Normalized SQL with comments removed and whitespace collapsed.

    Example:
        >>> normalize_sql('''
        ...     SELECT * FROM users -- get all
        ...     /* multi-line
        ...        comment */
        ...     WHERE active = true
        ... ''')
        'SELECT * FROM users WHERE active = true'
    """
    # Remove single-line comments (-- to end of line)
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    # Remove multi-line comments (/* ... */)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    # Collapse all whitespace to single spaces
    sql = " ".join(sql.split())
    return sql.strip()


def strip_sql_strings(sql: str) -> str:
    """Remove string literals from SQL to avoid false positives in pattern matching.

    This function strips both single-quoted string literals and double-quoted
    identifiers to prevent content within strings from triggering validation
    errors. For example, the string 'DROP TABLE users' should not be detected
    as a DDL statement.

    Handles PostgreSQL/SQL standard escaping conventions:
    - Backslash escapes: 'It\\'s a test' (escaped single quote)
    - Doubled quotes: 'It''s a test' (SQL-standard escaped quote)
    - Both conventions for double-quoted identifiers

    Args:
        sql: SQL string to process (ideally normalized first).

    Returns:
        SQL with all string literals replaced by empty strings.

    Example:
        >>> strip_sql_strings("SELECT * FROM t WHERE name = 'O''Brien'")
        'SELECT * FROM t WHERE name = '
        >>> strip_sql_strings("SELECT * FROM t WHERE msg = 'DROP TABLE'")
        'SELECT * FROM t WHERE msg = '
    """
    # Remove single-quoted strings
    # Pattern handles:
    #   [^'\\]  - any char except single quote or backslash
    #   \\.     - any escaped character (backslash + any char)
    #   ''      - doubled single quote (SQL-standard escape)
    sql = re.sub(r"'(?:[^'\\]|\\.|'')*'", "", sql)

    # Remove double-quoted identifiers/strings
    # Pattern handles:
    #   [^"\\]  - any char except double quote or backslash
    #   \\.     - any escaped character (backslash + any char)
    #   ""      - doubled double quote (SQL-standard escape)
    sql = re.sub(r'"(?:[^"\\]|\\.|"")*"', "", sql)

    return sql
