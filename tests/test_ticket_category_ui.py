import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src import config
from src.auth import register_user
from src.database import init_db
from src.ticket_manager import list_tickets


class TicketCategoryUITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = config.DATABASE_PATH
        config.DATABASE_PATH = Path(self.temp_dir.name) / "apptest.db"
        init_db()
        self.user = register_user(
            "category.user", "a sufficiently long password"
        )
        self.get_classifier_patch = patch("src.ui.get_classifier", return_value=object())
        self.predict_category_patch = patch(
            "src.classifier.predict_category",
            return_value=("Wi-Fi", 0.9),
        )
        self.get_classifier_patch.start()
        self.predict_category_patch.start()

    def tearDown(self):
        self.predict_category_patch.stop()
        self.get_classifier_patch.stop()
        config.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_suggestion_defaults_category_and_manual_correction_persists(self):
        app = AppTest.from_file(
            str(config.PROJECT_ROOT / "app.py"),
            default_timeout=15,
        )
        app.session_state["current_user"] = self.user
        app.run()
        self.assertFalse(app.exception)

        app.switch_page("pages/2_My_Tickets.py").run()
        app.text_area(key="new-ticket-description").set_value("Wi-Fi cannot connect")
        app.run()
        self.assertEqual(app.selectbox(key="new-ticket-category").value, "Wi-Fi")

        app.selectbox(key="new-ticket-category").select("Other").run()
        self.assertEqual(app.selectbox(key="new-ticket-category").value, "Other")
        app.text_input(key="new-ticket-name").set_value("Demo User")
        app.text_input(key="new-ticket-contact").set_value("demo@example.edu")
        app.button(key="submit-new-ticket").click().run()

        tickets = list_tickets(user_id=self.user["id"])
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]["category"], "Other")
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
