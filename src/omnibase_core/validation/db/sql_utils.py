"""Shared SQL utilities for database repository validators.

Provides normalize_sql (removes comments, collapses whitespace) and
strip_sql_strings (removes string literals to prevent false positives).
"""

import re

__all__ = ["extract_select_columns", "normalize_sql", "strip_sql_strings"]

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


# SQL keywords that should not be treated as implicit aliases
_SQL_KEYWORDS = frozenset(
    {
        "ALL",
        "AND",
        "AS",
        "ASC",
        "BETWEEN",
        "BY",
        "CROSS",
        "DEFAULT",
        "DESC",
        "DISTINCT",
        "FROM",
        "GROUP",
        "HAVING",
        "IN",
        "INNER",
        "INTO",
        "IS",
        "JOIN",
        "LEFT",
        "LIKE",
        "LIMIT",
        "NATURAL",
        "NOT",
        "NULL",
        "OFFSET",
        "ON",
        "OR",
        "ORDER",
        "OUTER",
        "RIGHT",
        "SET",
        "TRUE",
        "FALSE",
        "UNION",
        "USING",
        "VALUES",
        "WHERE",
    }
)


def _split_select_columns(select_clause: str) -> list[str]:
    """Split SELECT columns by comma, respecting parentheses and quotes.

    Args:
        select_clause: The text between SELECT and FROM.

    Returns:
        List of column expressions, stripped of surrounding whitespace.
    """
    columns: list[str] = []
    current: list[str] = []
    depth = 0
    in_single_quote = False
    in_double_quote = False

    for char in select_clause:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current.append(char)
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(char)
        elif not in_single_quote and not in_double_quote:
            if char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                col = "".join(current).strip()
                if col:
                    columns.append(col)
                current = []
            else:
                current.append(char)
        else:
            current.append(char)

    # Add the last column
    col = "".join(current).strip()
    if col:
        columns.append(col)

    return columns


def _extract_column_name(expr: str) -> str | None:
    """Extract column name from a column expression.

    Handles:
        - col -> col (lowercase)
        - col AS alias -> alias (lowercase)
        - col alias -> alias (lowercase, if not a keyword)
        - table.col -> col (lowercase)
        - "Column" -> Column (preserve case for quoted identifiers)
        - table."Column" AS alias -> alias (alias takes precedence)

    Args:
        expr: A single column expression from the SELECT clause.

    Returns:
        Extracted column name, or None if cannot parse.
    """
    expr = expr.strip()

    # Check for explicit AS alias: ... AS alias or ... AS "alias"
    as_match = re.search(r"\bAS\s+\"([^\"]+)\"\s*$", expr, re.IGNORECASE)
    if as_match:
        return as_match.group(1)  # Preserve case for quoted alias

    as_match = re.search(r"\bAS\s+(\w+)\s*$", expr, re.IGNORECASE)
    if as_match:
        return as_match.group(1).lower()

    # Check for implicit alias (word at end after space, not a keyword)
    # Pattern: expr "alias" (quoted)
    implicit_quoted = re.search(r'\s+"([^"]+)"\s*$', expr)
    if implicit_quoted:
        return implicit_quoted.group(1)  # Preserve case

    # Pattern: expr alias (unquoted)
    implicit_unquoted = re.search(r"\s+(\w+)\s*$", expr)
    if implicit_unquoted:
        potential_alias = implicit_unquoted.group(1)
        if potential_alias.upper() not in _SQL_KEYWORDS:
            return potential_alias.lower()
        # Fall through to base column extraction if it's a keyword

    # Extract base column (possibly table-qualified)
    # Try quoted identifier at end: table."Column" or just "Column"
    quoted_match = re.search(r'(?:[\w"]+\.)?\"([^\"]+)\"\s*$', expr)
    if quoted_match:
        return quoted_match.group(1)  # Preserve case

    # Try unquoted: table.col or just col
    unquoted_match = re.search(r"(?:\w+\.)?(\w+)\s*$", expr)
    if unquoted_match:
        return unquoted_match.group(1).lower()

    return None


def _find_from_keyword(sql: str, start: int) -> int:
    """Find the position of the FROM keyword, respecting quotes and parentheses.

    Args:
        sql: SQL string to search.
        start: Position to start searching from.

    Returns:
        Position of FROM keyword, or -1 if not found.
    """
    i = start
    length = len(sql)
    depth = 0
    in_single_quote = False
    in_double_quote = False

    while i < length:
        char = sql[i]

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif not in_single_quote and not in_double_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif depth == 0:
                # Check for FROM keyword (case-insensitive)
                if sql[i : i + 4].upper() == "FROM":
                    # Verify it's a word boundary
                    before_ok = i == 0 or not sql[i - 1].isalnum()
                    after_ok = i + 4 >= length or not sql[i + 4].isalnum()
                    if before_ok and after_ok:
                        return i
        i += 1

    return -1


def extract_select_columns(sql: str) -> tuple[list[str], bool]:
    """Extract column names from SELECT clause.

    Args:
        sql: SQL query (will be normalized internally).

    Returns:
        tuple of (columns, is_complex) where:
        - columns: list of normalized field names (aliases preferred, lowercase)
        - is_complex: True if unparseable expressions detected (functions, CASE, subqueries)

    Note:
        - Returns (["*"], False) for SELECT * or table.*
        - Returns ([], True) if SELECT clause cannot be parsed
    """
    # Normalize the SQL first
    normalized = normalize_sql(sql)
    upper_normalized = normalized.upper()

    # Find SELECT keyword
    select_match = re.search(r"\bSELECT\s+", upper_normalized)
    if not select_match:
        return ([], True)

    select_start = select_match.end()

    # Handle DISTINCT keyword
    distinct_match = re.match(r"DISTINCT\s+", upper_normalized[select_start:])
    if distinct_match:
        select_start += distinct_match.end()

    # Find FROM keyword (respecting quotes and parentheses)
    from_pos = _find_from_keyword(normalized, select_start)
    if from_pos == -1:
        # No FROM clause
        return ([], True)

    select_end = from_pos

    # Extract the SELECT clause from the NORMALIZED sql (preserves quotes/content)
    select_clause = normalized[select_start:select_end].strip()

    if not select_clause:
        return ([], True)

    # Split by commas respecting parentheses and quotes
    column_exprs = _split_select_columns(select_clause)

    columns: list[str] = []
    is_complex = False

    for expr in column_exprs:
        expr = expr.strip()
        if not expr:
            continue

        # Check for star selection first
        # Matches: *, table.*, "schema".table.*
        if expr == "*" or re.match(r'^[\w".]+\.\*$', expr):
            return (["*"], False)

        # Remove quoted content to check for complexity indicators
        temp_expr = re.sub(r'"[^"]*"', "", expr)  # Remove double-quoted identifiers
        temp_expr = re.sub(r"'[^']*'", "", temp_expr)  # Remove single-quoted strings

        # Function call (contains parentheses outside quotes)
        if "(" in temp_expr:
            is_complex = True
            continue

        # CASE expression
        if re.match(r"\bCASE\b", temp_expr, re.IGNORECASE):
            is_complex = True
            continue

        # Arithmetic operators: +, -, /
        if re.search(r"[+\-/]", temp_expr):
            is_complex = True
            continue

        # Multiplication operator (not standalone *)
        if re.search(r"\w\s*\*\s*\w", temp_expr):
            is_complex = True
            continue

        # Extract the actual column name
        column_name = _extract_column_name(expr)
        if column_name:
            columns.append(column_name)
        else:
            is_complex = True

    return (columns, is_complex)
