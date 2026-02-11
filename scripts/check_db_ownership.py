#!/usr/bin/env python3
"""CI twin for runtime assertion B1 -- database ownership verification.

Provisions a temporary SQLite database, runs the db_metadata migration,
inserts an ownership record, and verifies the table exists with the correct
``owner_service``.  This mirrors the runtime assertion that each service
performs at boot time.

Exit codes:
    0 - All checks passed
    1 - Ownership verification failed
    2 - Script error (setup / unexpected exception)

Usage:
    poetry run python scripts/check_db_ownership.py [--verbose]

See: OMN-2150 -- Handshake hardening: CI twin for DB ownership test script
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants -- single-source-of-truth from the model layer
# ---------------------------------------------------------------------------
# We import the SQL strings rather than duplicating them so that any drift
# between the model and the CI twin is impossible.

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from omnibase_core.models.contracts.model_db_ownership_metadata import (  # noqa: E402
    DB_METADATA_CREATE_SQL,
    DB_METADATA_INSERT_SQL,
    DB_METADATA_QUERY_SQL,
    ModelDbOwnershipMetadata,
)

# The canonical owner service for omnibase_core's test database.
EXPECTED_OWNER_SERVICE = "omnibase_core"
EXPECTED_SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(msg: str, *, verbose: bool) -> None:
    if verbose:
        print(f"  {msg}")


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Core checks
# ---------------------------------------------------------------------------


def check_migration_creates_table(
    conn: sqlite3.Connection,
    *,
    verbose: bool,
) -> bool:
    """Run the migration and verify the db_metadata table was created."""
    _log("Running migration: CREATE TABLE db_metadata ...", verbose=verbose)
    conn.executescript(DB_METADATA_CREATE_SQL)
    conn.commit()

    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata'",
    )
    row = cursor.fetchone()
    if row is None:
        print("FAIL: db_metadata table not created by migration SQL")
        return False

    _log("db_metadata table created successfully", verbose=verbose)
    return True


def check_ownership_insert_and_read(
    conn: sqlite3.Connection,
    *,
    verbose: bool,
) -> bool:
    """Insert an ownership record and read it back."""
    now = datetime.now(tz=UTC).isoformat()

    _log(
        f"Inserting ownership: owner_service={EXPECTED_OWNER_SERVICE!r}, "
        f"schema_version={EXPECTED_SCHEMA_VERSION!r}",
        verbose=verbose,
    )
    conn.execute(
        DB_METADATA_INSERT_SQL,
        {
            "owner_service": EXPECTED_OWNER_SERVICE,
            "schema_version": EXPECTED_SCHEMA_VERSION,
            "created_at": now,
        },
    )
    conn.commit()

    cursor = conn.execute(DB_METADATA_QUERY_SQL)
    row = cursor.fetchone()
    if row is None:
        print("FAIL: No ownership record found after INSERT")
        return False

    owner_service, schema_version, created_at = row
    _log(
        f"Read back: owner_service={owner_service!r}, "
        f"schema_version={schema_version!r}, created_at={created_at!r}",
        verbose=verbose,
    )

    if owner_service != EXPECTED_OWNER_SERVICE:
        print(
            f"FAIL: owner_service mismatch: "
            f"expected {EXPECTED_OWNER_SERVICE!r}, got {owner_service!r}",
        )
        return False

    if schema_version != EXPECTED_SCHEMA_VERSION:
        print(
            f"FAIL: schema_version mismatch: "
            f"expected {EXPECTED_SCHEMA_VERSION!r}, got {schema_version!r}",
        )
        return False

    _log("Ownership record verified", verbose=verbose)
    return True


def check_pydantic_model_roundtrip(
    conn: sqlite3.Connection,
    *,
    verbose: bool,
) -> bool:
    """Verify the DB row can be parsed into the Pydantic model."""
    cursor = conn.execute(DB_METADATA_QUERY_SQL)
    row = cursor.fetchone()
    if row is None:
        print("FAIL: No ownership record to validate against model")
        return False

    owner_service, schema_version, created_at_str = row
    try:
        model = ModelDbOwnershipMetadata(
            owner_service=owner_service,
            schema_version=schema_version,
            created_at=datetime.fromisoformat(created_at_str),
        )
    except Exception as exc:
        print(f"FAIL: Pydantic model validation failed: {exc}")
        return False

    _log(f"Pydantic model roundtrip OK: {model}", verbose=verbose)
    return True


def check_wrong_owner_detected(
    conn: sqlite3.Connection,
    *,
    verbose: bool,
) -> bool:
    """Verify that a wrong owner_service is detected (negative test)."""
    _log("Inserting wrong ownership record...", verbose=verbose)

    # Create a second database to avoid polluting the good one
    conn2 = sqlite3.connect(":memory:")
    conn2.executescript(DB_METADATA_CREATE_SQL)
    conn2.execute(
        DB_METADATA_INSERT_SQL,
        {
            "owner_service": "wrong_service",
            "schema_version": EXPECTED_SCHEMA_VERSION,
            "created_at": datetime.now(tz=UTC).isoformat(),
        },
    )
    conn2.commit()

    cursor = conn2.execute(DB_METADATA_QUERY_SQL)
    row = cursor.fetchone()
    conn2.close()

    if row is None:
        print("FAIL: Could not read wrong ownership record")
        return False

    owner_service = row[0]
    if owner_service == EXPECTED_OWNER_SERVICE:
        print("FAIL: Wrong owner was not detected (false negative)")
        return False

    _log(
        f"Wrong owner correctly detected: {owner_service!r} != "
        f"{EXPECTED_OWNER_SERVICE!r}",
        verbose=verbose,
    )
    return True


def check_missing_table_detected(*, verbose: bool) -> bool:
    """Verify that a missing db_metadata table is detected."""
    _log("Checking detection of missing db_metadata table...", verbose=verbose)

    conn = sqlite3.connect(":memory:")
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata'",
    )
    row = cursor.fetchone()
    conn.close()

    if row is not None:
        print("FAIL: db_metadata table exists in fresh database (unexpected)")
        return False

    _log("Missing table correctly detected", verbose=verbose)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CI twin for runtime assertion B1: DB ownership verification",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed progress",
    )
    args = parser.parse_args()

    print("=== DB Ownership CI Twin (B1 mirror) ===")

    checks: list[tuple[str, bool]] = []

    # Use a temp directory so the DB path is safe from TOCTOU races
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "ownership_test.db")
        conn = sqlite3.connect(db_path)
        try:
            # Positive checks
            ok = check_migration_creates_table(conn, verbose=args.verbose)
            checks.append(("Migration creates db_metadata table", ok))

            if ok:
                ok2 = check_ownership_insert_and_read(conn, verbose=args.verbose)
                checks.append(("Ownership INSERT/SELECT roundtrip", ok2))

                ok3 = check_pydantic_model_roundtrip(conn, verbose=args.verbose)
                checks.append(("Pydantic model roundtrip", ok3))

            # Negative checks
            ok4 = check_wrong_owner_detected(conn, verbose=args.verbose)
            checks.append(("Wrong owner detection", ok4))

            ok5 = check_missing_table_detected(verbose=args.verbose)
            checks.append(("Missing table detection", ok5))

        finally:
            conn.close()

    # Summary
    print()
    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    print()
    if passed == total:
        print(f"All {total} checks passed.")
        return 0
    else:
        print(f"{passed}/{total} checks passed. {total - passed} FAILED.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"SCRIPT ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
