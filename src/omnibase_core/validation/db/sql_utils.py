"""Shared SQL utilities for database repository validators.

Provides normalize_sql (removes comments, collapses whitespace) and
strip_sql_strings (removes string literals to prevent false positives).
"""

import re

__all__ = ["normalize_sql", "strip_sql_strings"]

# Pattern for matching SQL string literals (single and double quoted)
# Handles:
#   [^'\\]  - any char except single quote or backslash
#   \\.     - any escaped character (backslash + any char)
#   ''      - doubled single quote (SQL-standard escape)
_SINGLE_QUOTE_STRING_PATTERN = re.compile(r"'(?:[^'\\]|\\.|'')*'")
_DOUBLE_QUOTE_STRING_PATTERN = re.compile(r'"(?:[^"\\]|\\.|"")*"')


def _extract_strings_with_placeholders(
    sql: str,
) -> tuple[str, list[tuple[str, str]]]:
    """Extract string literals and replace with placeholders.

    This function finds all single-quoted and double-quoted strings in SQL,
    replaces them with unique placeholders, and returns both the modified
    SQL and a mapping to restore them later.

    Args:
        sql: SQL string that may contain quoted strings.

    Returns:
        A tuple of (modified_sql, replacements) where replacements is a list
        of (placeholder, original_string) tuples.
    """
    replacements: list[tuple[str, str]] = []
    counter = 0

    def make_placeholder(match: re.Match[str]) -> str:
        nonlocal counter
        placeholder = f"__SQL_STRING_{counter}__"
        replacements.append((placeholder, match.group(0)))
        counter += 1
        return placeholder

    # Replace single-quoted strings first, then double-quoted
    sql = _SINGLE_QUOTE_STRING_PATTERN.sub(make_placeholder, sql)
    sql = _DOUBLE_QUOTE_STRING_PATTERN.sub(make_placeholder, sql)

    return sql, replacements


def _restore_strings(sql: str, replacements: list[tuple[str, str]]) -> str:
    """Restore string literals from placeholders.

    Args:
        sql: SQL with placeholders.
        replacements: List of (placeholder, original_string) tuples.

    Returns:
        SQL with original string literals restored.
    """
    for placeholder, original in replacements:
        sql = sql.replace(placeholder, original)
    return sql


def normalize_sql(sql: str) -> str:
    """Normalize SQL by stripping comments and collapsing whitespace.

    This function prepares raw SQL for pattern matching by removing
    elements that could interfere with validation logic:

    - Single-line comments (-- comment to end of line)
    - Multi-line comments (/* comment block */)
    - Excess whitespace (collapsed to single spaces)

    String literals are preserved - comment-like patterns inside quoted
    strings (e.g., 'value -- not a comment') are not stripped.

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

        >>> normalize_sql("SELECT * FROM t WHERE msg = 'value -- not a comment'")
        "SELECT * FROM t WHERE msg = 'value -- not a comment'"
    """
    # Step 1: Extract string literals and replace with placeholders
    # This protects comment-like patterns inside strings
    sql, replacements = _extract_strings_with_placeholders(sql)

    # Step 2: Remove single-line comments (-- to end of line)
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)

    # Step 3: Remove multi-line comments (/* ... */)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)

    # Step 4: Restore string literals
    sql = _restore_strings(sql, replacements)

    # Step 5: Collapse all whitespace to single spaces
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
