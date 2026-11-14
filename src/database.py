"""
database.py - SQLite storage for conversations, messages and tickets.

init_db()                  creates the tables (safe to run many times)
create_conversation()      starts a new conversation, returns its id
add_message(...)           saves one chat message
get_messages(id)           all messages of a conversation (for display)
get_history(id)            role/content pairs (for the LLM prompt)
list_conversations()       recent conversations (for the sidebar)

ticket_manager.py uses get_connection() to work with the tickets table.
Every function accepts an optional db_path so tests can use a temporary file.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from src import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_salt  TEXT NOT NULL,
    password_hash  TEXT NOT NULL,
    iterations     INTEGER NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('user', 'admin')),
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id  INTEGER NOT NULL REFERENCES conversations(id),
    role             TEXT NOT NULL,
    content          TEXT NOT NULL,
    status           TEXT,
    sources_json     TEXT,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER REFERENCES users(id),
    conversation_id  INTEGER REFERENCES conversations(id),
    requester_name   TEXT NOT NULL,
    contact          TEXT NOT NULL,
    category         TEXT NOT NULL,
    description      TEXT NOT NULL,
    context_json     TEXT,
    status           TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS message_feedback (
    message_id  INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resolved    INTEGER NOT NULL CHECK (resolved IN (0, 1)),
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_context_feedback (
    ticket_id   INTEGER PRIMARY KEY REFERENCES tickets(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    helpful     INTEGER NOT NULL CHECK (helpful IN (0, 1)),
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS guided_outcomes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic            TEXT NOT NULL,
    resolved         INTEGER NOT NULL CHECK (resolved IN (0, 1)),
    steps_completed  INTEGER NOT NULL,
    ticket_id        INTEGER REFERENCES tickets(id),
    created_at       TEXT NOT NULL
);
"""


def now():
    """Current local time as text, e.g. 2026-11-13T10:22:31."""
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def get_connection(db_path=None):
    """Open a database connection; commit on success, roll back on error, always close."""
    path = Path(db_path) if db_path is not None else config.DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(db_path=None):
    """Create tables and add new nullable columns without discarding existing data."""
    with get_connection(db_path) as connection:
        connection.executescript(SCHEMA)
        migrations = {
            "conversations": {
                "user_id": "INTEGER REFERENCES users(id)",
            },
            "tickets": {
                "user_id": "INTEGER REFERENCES users(id)",
                "context_json": "TEXT",
            },
        }
        for table, columns in migrations.items():
            existing = {
                row["name"]
                for row in connection.execute(f"PRAGMA table_info({table})")
            }
            for name, declaration in columns.items():
                if name not in existing:
                    connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"
                    )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS conversations_user_idx "
            "ON conversations(user_id, id DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS tickets_user_idx ON tickets(user_id, id DESC)"
        )


def create_conversation(db_path=None, user_id=None):
    """Start a new conversation and return its id."""
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO conversations (user_id, created_at) VALUES (?, ?)",
            (user_id, now()),
        )
        return cursor.lastrowid


def add_message(
    conversation_id,
    role,
    content,
    status=None,
    sources=None,
    db_path=None,
    user_id=None,
):
    """Save one message. Returns the new message id.

    role    : "user" or "assistant"
    status  : the pipeline status for assistant messages (optional)
    sources : the list of source dictionaries for assistant messages (optional)
    """
    sources_json = json.dumps(sources, ensure_ascii=False) if sources else None
    with get_connection(db_path) as connection:
        if user_id is not None:
            owner = connection.execute(
                "SELECT 1 FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            ).fetchone()
            if owner is None:
                raise ValueError("Conversation does not belong to this account.")
        cursor = connection.execute(
            "INSERT INTO messages "
            "(conversation_id, role, content, status, sources_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, role, content, status, sources_json, now()),
        )
        return cursor.lastrowid


def get_messages(conversation_id, db_path=None, user_id=None):
    """Return all messages of a conversation, oldest first."""
    with get_connection(db_path) as connection:
        query = (
            "SELECT m.id, m.role, m.content, m.status, m.sources_json, m.created_at "
            "FROM messages m JOIN conversations c ON c.id = m.conversation_id "
            "WHERE m.conversation_id = ?"
        )
        values = [conversation_id]
        if user_id is not None:
            query += " AND c.user_id = ?"
            values.append(user_id)
        rows = connection.execute(query + " ORDER BY m.id", values).fetchall()

    return [
        {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "status": row["status"],
            "sources": json.loads(row["sources_json"]) if row["sources_json"] else [],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_history(conversation_id, db_path=None, user_id=None):
    """Return [{"role", "content"}, ...] in the format prompt_builder expects."""
    return [
        {"role": message["role"], "content": message["content"]}
        for message in get_messages(conversation_id, db_path, user_id)
    ]


def list_conversations(limit=20, db_path=None, user_id=None):
    """Return recent conversations that have messages, newest first."""
    with get_connection(db_path) as connection:
        query = (
            "SELECT c.id, c.created_at, "
            "  (SELECT m.content FROM messages m "
            "   WHERE m.conversation_id = c.id AND m.role = 'user' "
            "   ORDER BY m.id LIMIT 1) AS first_question "
            "FROM conversations c "
            "WHERE EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = c.id) "
        )
        values = []
        if user_id is not None:
            query += "AND c.user_id = ? "
            values.append(user_id)
        query += "ORDER BY c.id DESC LIMIT ?"
        values.append(limit)
        rows = connection.execute(query, values).fetchall()

    return [
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "title": (row["first_question"] or "Conversation")[:50],
        }
        for row in rows
    ]


def get_conversation_context(conversation_id, user_id, limit=10, db_path=None):
    """Return a recent, ownership-checked transcript snapshot for a ticket."""
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT m.role, m.content, m.status, m.sources_json, m.created_at "
            "FROM messages m JOIN conversations c ON c.id = m.conversation_id "
            "WHERE c.id = ? AND c.user_id = ? "
            "ORDER BY m.id DESC LIMIT ?",
            (conversation_id, user_id, limit),
        ).fetchall()
    return [
        {
            "role": row["role"],
            "content": row["content"],
            "status": row["status"],
            "sources": json.loads(row["sources_json"]) if row["sources_json"] else [],
            "created_at": row["created_at"],
        }
        for row in reversed(rows)
    ]


def get_message_feedback(message_id, user_id, db_path=None):
    """Return this user's resolution vote for an assistant message, if present."""
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT resolved FROM message_feedback "
            "WHERE message_id = ? AND user_id = ?",
            (message_id, user_id),
        ).fetchone()
    return None if row is None else bool(row["resolved"])


def get_ticket_context_feedback(ticket_id, user_id, db_path=None):
    """Return this user's usefulness vote for the attached ticket context."""
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT helpful FROM ticket_context_feedback "
            "WHERE ticket_id = ? AND user_id = ?",
            (ticket_id, user_id),
        ).fetchone()
    return None if row is None else bool(row["helpful"])


def record_ticket_context_feedback(ticket_id, user_id, helpful, db_path=None):
    """Record whether the attached context helped on an owned ticket."""
    if not isinstance(helpful, bool):
        raise ValueError("Context feedback must be true or false.")
    with get_connection(db_path) as connection:
        ticket = connection.execute(
            "SELECT 1 FROM tickets WHERE id = ? AND user_id = ? "
            "AND context_json IS NOT NULL",
            (ticket_id, user_id),
        ).fetchone()
        if ticket is None:
            raise ValueError("Ticket context does not belong to this account.")
        connection.execute(
            "INSERT INTO ticket_context_feedback "
            "(ticket_id, user_id, helpful, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(ticket_id) DO UPDATE SET "
            "helpful = excluded.helpful, created_at = excluded.created_at",
            (ticket_id, user_id, int(helpful), now()),
        )


def record_message_feedback(message_id, user_id, resolved, db_path=None):
    """Record or update an answer-resolution vote for an owned conversation."""
    if not isinstance(resolved, bool):
        raise ValueError("Resolution feedback must be true or false.")
    with get_connection(db_path) as connection:
        message = connection.execute(
            "SELECT 1 FROM messages m "
            "JOIN conversations c ON c.id = m.conversation_id "
            "WHERE m.id = ? AND m.role = 'assistant' AND c.user_id = ?",
            (message_id, user_id),
        ).fetchone()
        if message is None:
            raise ValueError("Assistant message does not belong to this account.")
        connection.execute(
            "INSERT INTO message_feedback (message_id, user_id, resolved, created_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(message_id) DO UPDATE SET "
            "resolved = excluded.resolved, created_at = excluded.created_at",
            (message_id, user_id, int(resolved), now()),
        )


def record_guided_outcome(
    user_id, topic, resolved, steps_completed, ticket_id=None, db_path=None
):
    """Record an explicitly reported guided-troubleshooting outcome."""
    if not isinstance(resolved, bool):
        raise ValueError("Resolution outcome must be true or false.")
    if not isinstance(steps_completed, int) or steps_completed < 0:
        raise ValueError("Completed-step count must be a non-negative integer.")
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO guided_outcomes "
            "(user_id, topic, resolved, steps_completed, ticket_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, topic, int(resolved), steps_completed, ticket_id, now()),
        )
        return cursor.lastrowid


# ---------------------------------------------------------------------------
# Quick self-check: run with  python -m src.database
# (uses a temporary database file, so it never touches the real one)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as temp_folder:
        test_db = Path(temp_folder) / "test.db"

        init_db(test_db)
        init_db(test_db)  # running twice must be harmless

        with get_connection(test_db) as connection:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        print("Tables:", sorted(tables))
        assert {"conversations", "messages", "tickets"} <= tables

        first = create_conversation(test_db)
        empty = create_conversation(test_db)
        assert first != empty

        sources = [{"source": "a.txt", "page": 1, "label": "sample", "score": 0.5}]
        add_message(first, "user", "I can't connect to Wi-Fi caf\u00e9", db_path=test_db)
        add_message(first, "assistant", "Try these steps...", "answered", sources, test_db)

        messages = get_messages(first, test_db)
        assert [m["role"] for m in messages] == ["user", "assistant"]
        assert messages[0]["content"] == "I can't connect to Wi-Fi caf\u00e9"
        assert messages[0]["sources"] == []
        assert messages[1]["status"] == "answered"
        assert messages[1]["sources"] == sources

        history = get_history(first, test_db)
        assert history[1] == {"role": "assistant", "content": "Try these steps..."}

        conversations = list_conversations(db_path=test_db)
        print("Conversations:", conversations)
        assert [c["id"] for c in conversations] == [first]   # the empty one is hidden
        assert conversations[0]["title"].startswith("I can't connect")

        try:
            add_message(999, "user", "orphan", db_path=test_db)
            raise AssertionError("Foreign key should have rejected this")
        except sqlite3.IntegrityError as error:
            print("Foreign key enforced:", error)

    print("Database checks passed.")