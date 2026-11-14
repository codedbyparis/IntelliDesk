import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src import config
from src.auth import authenticate_user
from src.database import init_db


class AuthenticationUITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = config.DATABASE_PATH
        config.DATABASE_PATH = Path(self.temp_dir.name) / "auth-ui.db"
        init_db()

    def tearDown(self):
        config.DATABASE_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_user_can_register_sign_out_and_sign_back_in(self):
        app = AppTest.from_file(
            str(config.PROJECT_ROOT / "app.py"),
            default_timeout=15,
        ).run()
        self.assertFalse(app.exception)

        app.text_input(key="register-username").set_value("demo.user")
        app.text_input(key="register-password").set_value(
            "a sufficiently long password"
        )
        app.text_input(key="register-password-confirm").set_value(
            "a sufficiently long password"
        )
        app.button(key="FormSubmitter:register-form-Create account").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["current_user"]["role"], "user")
        self.assertIsNotNone(
            authenticate_user("demo.user", "a sufficiently long password")
        )

        app.button(key="sidebar-sign-out").click().run()
        self.assertNotIn("current_user", app.session_state)
        app.text_input(key="login-username").set_value("demo.user")
        app.text_input(key="login-password").set_value(
            "a sufficiently long password"
        )
        app.button(key="FormSubmitter:login-form-Sign in").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["current_user"]["username"], "demo.user")


if __name__ == "__main__":
    unittest.main()
