"""SQLite storage for USCIS WatchBot."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Sequence
import sqlite3

from .config import Settings


CREATE_UPDATES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    source TEXT,
    category TEXT,
    matched_topics TEXT,
    update_type TEXT,
    first_seen_at TEXT,
    sent_daily INTEGER DEFAULT 0,
    sent_weekly INTEGER DEFAULT 0
);
"""


@contextmanager
def get_connection(settings: Settings) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with row access by column name."""

    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db(settings: Settings) -> None:
    """Create required tables if they do not already exist."""

    with get_connection(settings) as connection:
        connection.execute(CREATE_UPDATES_TABLE_SQL)


def insert_update(settings: Settings, update: dict[str, object]) -> int | None:
    """Insert one update. Returns the inserted row id or None for duplicates."""

    with get_connection(settings) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO updates (
                title,
                url,
                source,
                category,
                matched_topics,
                update_type,
                first_seen_at,
                sent_daily,
                sent_weekly
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                update["title"],
                update["url"],
                update["source"],
                update["category"],
                update["matched_topics"],
                update["update_type"],
                update["first_seen_at"],
                update.get("sent_daily", 0),
                update.get("sent_weekly", 0),
            ),
        )

        if cursor.rowcount == 0:
            return None

        return int(cursor.lastrowid)


def get_unsent_weekly_updates(settings: Settings) -> list[dict[str, object]]:
    """Fetch weekly digest updates that have not been sent yet."""

    with get_connection(settings) as connection:
        rows = connection.execute(
            """
            SELECT id, title, url, source, category, matched_topics, update_type, first_seen_at
            FROM updates
            WHERE update_type = 'weekly_general' AND sent_weekly = 0
            ORDER BY first_seen_at ASC, id ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def mark_daily_sent(settings: Settings, update_ids: Sequence[int]) -> None:
    """Mark daily priority alerts as sent."""

    if not update_ids:
        return

    placeholders = ", ".join("?" for _ in update_ids)
    with get_connection(settings) as connection:
        connection.execute(
            f"UPDATE updates SET sent_daily = 1 WHERE id IN ({placeholders})",
            tuple(update_ids),
        )


def mark_weekly_sent(settings: Settings, update_ids: Sequence[int]) -> None:
    """Mark weekly digest updates as sent."""

    if not update_ids:
        return

    placeholders = ", ".join("?" for _ in update_ids)
    with get_connection(settings) as connection:
        connection.execute(
            f"UPDATE updates SET sent_weekly = 1 WHERE id IN ({placeholders})",
            tuple(update_ids),
        )
