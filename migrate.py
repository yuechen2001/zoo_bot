"""
SQL migration runner.

Usage:
    python migrate.py up          # apply all pending migrations
    python migrate.py down <ver>  # roll back one migration, e.g. down 001_initial_schema
    python migrate.py status      # show applied / pending migrations
"""

import logging
import re
import sys
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
logger = logging.getLogger(__name__)


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_tracking_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    TEXT PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def _applied_versions(conn: sqlite3.Connection) -> set:
    return {r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}


def _parse(path: Path) -> tuple[str, str]:
    """Return (up_sql, down_sql) from a migration file."""
    text = path.read_text()
    up = re.search(r"--\s*up\s*\n(.*?)(?=--\s*down\s*|\Z)", text, re.DOTALL | re.IGNORECASE)
    down = re.search(r"--\s*down\s*\n(.*)", text, re.DOTALL | re.IGNORECASE)
    return (up.group(1).strip() if up else ""), (down.group(1).strip() if down else "")


def _apply(conn: sqlite3.Connection, path: Path) -> None:
    up_sql, _ = _parse(path)
    if not up_sql:
        raise ValueError(f"{path.name} has no '-- up' section — add one before applying")
    for stmt in [s.strip() for s in up_sql.split(";") if s.strip()]:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as e:
            # Idempotent ADD COLUMN: skip if column already exists (repair migrations)
            if "duplicate column name" not in str(e).lower():
                raise
    conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (path.stem,))
    conn.commit()
    logger.info("  ✓ applied   %s", path.stem)


def _rollback(conn: sqlite3.Connection, path: Path) -> None:
    _, down_sql = _parse(path)
    conn.executescript(down_sql)
    conn.execute("DELETE FROM schema_migrations WHERE version = ?", (path.stem,))
    conn.commit()
    logger.info("  ✓ rolled back %s", path.stem)


def run_migrations(db_path: str) -> None:
    """Apply all pending migrations. Called from db.init_db()."""
    conn = _get_conn(db_path)
    _ensure_tracking_table(conn)
    applied = _applied_versions(conn)
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.stem not in applied:
            _apply(conn, path)
    conn.close()


def _cmd_up(db_path: str) -> None:
    conn = _get_conn(db_path)
    _ensure_tracking_table(conn)
    applied = _applied_versions(conn)
    pending = [p for p in sorted(MIGRATIONS_DIR.glob("*.sql")) if p.stem not in applied]
    if not pending:
        logger.info("Nothing to apply — already up to date.")
    for path in pending:
        _apply(conn, path)
    conn.close()


def _cmd_down(db_path: str, version: str) -> None:
    conn = _get_conn(db_path)
    _ensure_tracking_table(conn)
    applied = _applied_versions(conn)
    files = {p.stem: p for p in MIGRATIONS_DIR.glob("*.sql")}
    if version not in applied:
        logger.error("  ✗ %s is not applied.", version)
        sys.exit(1)
    if version not in files:
        logger.error("  ✗ migration file for %s not found.", version)
        sys.exit(1)
    _rollback(conn, files[version])
    conn.close()


def _cmd_status(db_path: str) -> None:
    conn = _get_conn(db_path)
    _ensure_tracking_table(conn)
    applied = _applied_versions(conn)
    all_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not all_files:
        logger.info("No migration files found.")
        return
    for path in all_files:
        mark = "✓" if path.stem in applied else "○"
        logger.info("  %s %s", mark, path.stem)
    conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from config import DATABASE_PATH

    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    cmd = args[0]
    if cmd == "up":
        _cmd_up(DATABASE_PATH)
    elif cmd == "down":
        if len(args) < 2:
            logger.error("Usage: python migrate.py down <version>")
            sys.exit(1)
        _cmd_down(DATABASE_PATH, args[1])
    elif cmd == "status":
        _cmd_status(DATABASE_PATH)
    else:
        logger.error("Unknown command: %s", cmd)
        sys.exit(1)
