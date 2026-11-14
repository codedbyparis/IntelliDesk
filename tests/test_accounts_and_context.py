import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.auth import authenticate_user, register_user
from src.database import (
    add_message,
    create_conversation,
    get_conversation_context,
    get_messages,
    init_db,
    record_guided_outcome,
    record_message_feedback,
    record_ticket_context_feedback,
)
from src.ticket_manager import create_ticket, get_statistics, list_tickets


class AccountsAndContextTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        init_db(self.db_path)
        self.alice = register_user(
            "alice.user", "a sufficiently long password", self.db_path
        )
        self.bob = register_user(
            "bob.user", "another sufficiently long password", self.db_path
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_authentication_and_username_validation(self):
        self.assertEqual(
            authenticate_user(
                "ALICE.USER", "a sufficiently long password", self.db_path
            ),
            self.alice,
        )
        self.assertIsNone(
            authenticate_user("alice.user", "incorrect password", self.db_path)
        )
        with self.assertRaises(ValueError):
            register_user(None, "a sufficiently long password", self.db_path)

    def test_conversations_and_tickets_are_account_scoped(self):
        conversation_id = create_conversation(
            user_id=self.alice["id"], db_path=self.db_path
        )
        add_message(
            conversation_id,
            "user",
            "Campus Wi-Fi is not working",
            db_path=self.db_path,
            user_id=self.alice["id"],
        )
        message_id = add_message(
            conversation_id,
            "assistant",
            "Try the sample Wi-Fi steps.",
            status="answered",
            db_path=self.db_path,
            user_id=self.alice["id"],
        )

        self.assertEqual(len(get_messages(conversation_id, self.db_path, self.alice["id"])), 2)
        self.assertEqual(get_messages(conversation_id, self.db_path, self.bob["id"]), [])
        self.assertEqual(
            get_conversation_context(
                conversation_id, self.bob["id"], db_path=self.db_path
            ),
            [],
        )
        with self.assertRaises(ValueError):
            add_message(
                conversation_id,
                "user",
                "unauthorized",
                db_path=self.db_path,
                user_id=self.bob["id"],
            )
        with self.assertRaises(ValueError):
            create_ticket(
                "Bob",
                "bob@example.edu",
                "Wi-Fi",
                "A ticket linked to Alice's conversation",
                conversation_id=conversation_id,
                user_id=self.bob["id"],
                db_path=self.db_path,
            )

        context = get_conversation_context(
            conversation_id, self.alice["id"], db_path=self.db_path
        )
        ticket_id = create_ticket(
            "Alice",
            "alice@example.edu",
            "Wi-Fi",
            "Campus Wi-Fi is not working",
            conversation_id=conversation_id,
            user_id=self.alice["id"],
            context=context,
            db_path=self.db_path,
        )
        self.assertEqual(list_tickets(user_id=self.bob["id"], db_path=self.db_path), [])
        self.assertEqual(len(list_tickets(user_id=self.alice["id"], db_path=self.db_path)), 1)

        record_message_feedback(message_id, self.alice["id"], False, self.db_path)
        record_guided_outcome(self.alice["id"], "Wi-Fi connection", True, 2, db_path=self.db_path)
        record_ticket_context_feedback(ticket_id, self.alice["id"], True, self.db_path)
        statistics = get_statistics(self.db_path)
        self.assertEqual(statistics["answer_resolution"]["responses"], 1)
        self.assertEqual(statistics["answer_resolution"]["rate"], 0)
        self.assertEqual(statistics["guided_resolution"]["rate"], 1)
        self.assertEqual(statistics["escalation_context"]["coverage"], 1)
        self.assertEqual(statistics["escalation_context"]["helpful_rate"], 1)

    def test_old_database_migration_preserves_existing_rows(self):
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(
                """
                DROP TABLE guided_outcomes;
                DROP TABLE ticket_context_feedback;
                DROP TABLE message_feedback;
                DROP TABLE tickets;
                DROP TABLE messages;
                DROP TABLE conversations;
                DROP TABLE users;
                CREATE TABLE conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT,
                    sources_json TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER REFERENCES conversations(id),
                    requester_name TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT INTO conversations (id, created_at) VALUES (10, '2026-01-01');
                INSERT INTO messages
                    (conversation_id, role, content, created_at)
                    VALUES (10, 'user', 'Existing message', '2026-01-01');
                INSERT INTO tickets
                    (id, requester_name, contact, category, description, status,
                     created_at, updated_at)
                    VALUES (20, 'Legacy user', 'legacy@example.edu', 'Other',
                            'Existing ticket', 'Open', '2026-01-01', '2026-01-01');
                """
            )
        connection.close()

        init_db(self.db_path)
        init_db(self.db_path)
        self.assertEqual(get_messages(10, self.db_path)[0]["content"], "Existing message")
        legacy_ticket = list_tickets(db_path=self.db_path)[0]
        self.assertEqual(legacy_ticket["id"], 20)
        self.assertEqual(legacy_ticket["context"], [])
        self.assertIsNone(legacy_ticket["user_id"])


if __name__ == "__main__":
    unittest.main()
