import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src import config
from src.auth import create_admin_account, register_user
from src.database import init_db
from src.ticket_manager import get_statistics, list_tickets


class GuidedWorkflowUITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = config.DATABASE_PATH
        config.DATABASE_PATH = Path(self.temp_dir.name) / "apptest.db"
        init_db()
        self.user = register_user(
            "guided.user", "a sufficiently long password"
        )
        self.admin = create_admin_account(
            "guided.admin", "another sufficiently long password"
        )

    def tearDown(self):
        config.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_guided_outcomes_escalation_context_and_admin_queue(self):
        app = AppTest.from_file(
            str(config.PROJECT_ROOT / "app.py"),
            default_timeout=15,
        )
        app.session_state["current_user"] = self.user
        app.run()
        self.assertFalse(app.exception)

        app.switch_page("pages/5_Guided_Troubleshooting.py").run()
        app.button(key="guided-resolved-Wi-Fi connection").click().run()
        app.button(key="guided-start-over").click().run()
        for step in range(4):
            app.button(key=f"guided-next-Wi-Fi connection-{step}").click().run()
        app.button(key="guided-unresolved-Wi-Fi connection").click().run()

        app.text_input(key="guided-ticket-name").set_value("Demo User")
        app.text_input(key="guided-ticket-contact").set_value("demo@example.edu")
        app.button(key="submit-guided-ticket").click().run()
        self.assertFalse(app.exception)

        tickets = list_tickets(user_id=self.user["id"])
        self.assertEqual(len(tickets), 1)
        self.assertEqual(len(tickets[0]["context"]), 6)
        self.assertEqual(
            tickets[0]["context"][0]["sources"][0]["label"],
            config.LABEL_SAMPLE,
        )
        statistics = get_statistics()
        self.assertEqual(statistics["guided_resolution"]["responses"], 2)
        self.assertEqual(statistics["guided_resolution"]["resolved"], 1)
        self.assertEqual(statistics["escalation_context"]["coverage"], 1)

        app.switch_page("pages/1_Admin_Dashboard.py").run()
        self.assertTrue(
            any("administrator accounts" in str(item.value) for item in app.error)
        )
        app.session_state["current_user"] = self.admin
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(
            any("IT ticket queue" in str(item.value) for item in app.title)
        )


if __name__ == "__main__":
    unittest.main()
