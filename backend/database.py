import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from backend.schemas import AIResult, Entry, EntryPage


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection, connection:
            connection.executescript((Path(__file__).with_name("schema.sql")).read_text())

    @staticmethod
    def entry(row: sqlite3.Row) -> Entry:
        return Entry(**{**dict(row), "tags": json.loads(row["tags"])})

    def save(self, text: str, result: AIResult) -> Entry:
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self.connect()) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO entries (text, summary, tags, created_at) VALUES (?, ?, ?, ?)",
                (text, result.summary, json.dumps(result.tags), created_at),
            )
            row = connection.execute(
                "SELECT * FROM entries WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return self.entry(row)

    def list(self, limit: int, offset: int) -> EntryPage:
        with closing(self.connect()) as connection:
            # A read transaction keeps count and page consistent with each other.
            connection.execute("BEGIN")
            total = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM entries ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
            return EntryPage(entries=[self.entry(row) for row in rows], total=total)

    def get(self, entry_id: int) -> Entry | None:
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
            return self.entry(row) if row else None

    def delete(self, entry_id: int) -> bool:
        with closing(self.connect()) as connection, connection:
            cursor = connection.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            return cursor.rowcount == 1
