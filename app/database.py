"""SQLite persistence for NOVA translations and feedback."""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "nova.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_language TEXT NOT NULL,
    target_language TEXT NOT NULL,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    phonetic TEXT NOT NULL DEFAULT '',
    context TEXT NOT NULL DEFAULT 'quotidien',
    engine TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    translation_id INTEGER NOT NULL,
    helpful INTEGER NOT NULL CHECK (helpful IN (0, 1)),
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (translation_id) REFERENCES translations(id)
);
"""


def database_path() -> Path:
    configured = os.getenv("NOVA_DB_PATH", "").strip()
    if configured:
        path = Path(configured)
    elif os.getenv("VERCEL"):
        # The deployed filesystem is read-only: /tmp is the only writable area.
        # Data does not survive a cold start; use a hosted DB for persistence.
        path = Path("/tmp/nova.db")
    else:
        path = DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    # Idempotent: recreates the schema if a fresh database file appears while the app runs.
    connection.executescript(SCHEMA)
    # Databases created before phonetics was added need the column as well.
    columns = {row[1] for row in connection.execute("PRAGMA table_info(translations)")}
    if "phonetic" not in columns:
        connection.execute("ALTER TABLE translations ADD COLUMN phonetic TEXT NOT NULL DEFAULT ''")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialise() -> None:
    with connect():
        pass


def save_translation(
    source_language: str,
    target_language: str,
    source_text: str,
    translated_text: str,
    context: str,
    engine: str,
    phonetic: str = "",
) -> dict:
    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO translations (
                source_language, target_language, source_text,
                translated_text, context, engine, phonetic
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_language,
                target_language,
                source_text,
                translated_text,
                context,
                engine,
                phonetic,
            ),
        )
        row = db.execute(
            "SELECT * FROM translations WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


def list_translations(limit: int = 30) -> list[dict]:
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM translations ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def clear_translations() -> None:
    with connect() as db:
        db.execute("DELETE FROM translations")


def save_feedback(translation_id: int, helpful: bool, comment: str | None) -> dict:
    with connect() as db:
        exists = db.execute(
            "SELECT 1 FROM translations WHERE id = ?", (translation_id,)
        ).fetchone()
        if not exists:
            raise ValueError("Traduction introuvable")
        cursor = db.execute(
            "INSERT INTO feedback (translation_id, helpful, comment) VALUES (?, ?, ?)",
            (translation_id, int(helpful), comment),
        )
        row = db.execute("SELECT * FROM feedback WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)
